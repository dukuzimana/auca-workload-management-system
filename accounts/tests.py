# Tests: account linking and search.
import datetime

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from accounts.forms import UserUpdateForm

from academics.models import (
    Faculty,
    Program,
    Cohort,
    AcademicPeriod,
    Lecturer,
    Course,
)

from workload.models import Workload
from workload.selectors import resolve_lecturer

from common.search import search


class AccountData(TestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username="Dismas",
            password="pw",
            role="admin",
        )

        self.faculty = Faculty.objects.create(name="Information Technology")

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="MSc Big Data Analytics",
        )

        self.cohort = Cohort.objects.create(
            program=self.program,
            name="Cohort 5",
            intake_year=2025,
        )

        self.period = AcademicPeriod.objects.create(
            academic_year="2026/2027",
            semester="Semester 1",
            teaching_period="May 2026 - September 2026",
            start_date=datetime.date(2026, 5, 4),
            end_date=datetime.date(2026, 9, 25),
        )

        self.course = Course.objects.create(
            program=self.program,
            code="BDA701",
            name="Advanced Databases",
            credits=3,
            level="Masters",
        )

        # Two lecturer logins and two lecturer records.
        self.kumar_user = User.objects.create_user(
            username="Kumar",
            password="pw",
            role="lecturer",
        )

        self.claire_user = User.objects.create_user(
            username="Claire",
            password="pw",
            role="lecturer",
        )

        self.kumar = Lecturer.objects.create(
            name="Kumar Kundan",
            employment_status="Contractual",
            user=self.kumar_user,
        )

        self.claire = Lecturer.objects.create(
            name="Marie Claire",
            employment_status="Visitor",
            user=self.claire_user,
        )

    def sign_in_admin(self):
        self.client.force_login(self.admin)


class AccountDeletionTests(AccountData):

    def test_deleting_a_login_keeps_the_lecturer_and_workload(self):
        """
        Lecturer.user was CASCADE, so removing a login destroyed the
        academic record and every Workload row attached to it.
        """
        Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.kumar,
            course=self.course,
            start_date=self.period.start_date,
            course_days="Monday",
        )

        self.kumar_user.delete()

        self.kumar.refresh_from_db()

        self.assertIsNone(self.kumar.user)
        self.assertEqual(Lecturer.objects.filter(pk=self.kumar.pk).count(), 1)
        self.assertEqual(Workload.objects.filter(lecturer=self.kumar).count(), 1)

    def test_clearing_the_link_keeps_the_lecturer_and_workload(self):
        """
        Unlinking is now done by clearing User Account on the
        lecturer's own record. It must remove only the login
        connection -- the lecturer and their teaching history
        stay.
        """
        Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.kumar,
            course=self.course,
            start_date=self.period.start_date,
            course_days="Monday",
        )

        self.kumar.user = None
        self.kumar.save()

        self.kumar.refresh_from_db()

        self.assertIsNone(self.kumar.user)
        self.assertEqual(Lecturer.objects.filter(pk=self.kumar.pk).count(), 1)
        self.assertEqual(Workload.objects.filter(lecturer=self.kumar).count(), 1)
        self.assertTrue(User.objects.filter(pk=self.kumar_user.pk).exists())

    def test_last_administrator_cannot_be_deleted(self):
        self.sign_in_admin()

        other_admin = User.objects.create_user(
            username="Temp",
            password="pw",
            role="admin",
        )

        # Signed in as Dismas, deleting the only other admin is fine.
        self.client.post(
            reverse("accounts:delete_user", args=[other_admin.pk])
        )
        self.assertFalse(User.objects.filter(pk=other_admin.pk).exists())

        # Deleting yourself is refused.
        self.client.post(
            reverse("accounts:delete_user", args=[self.admin.pk])
        )
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_role_change_blocked_while_linked(self):
        """
        Kumar's login is set on his lecturer record by the
        fixture. Turning him into a representative would leave
        that record pointing at an account that no longer passes
        the lecturer role check, and his workload would vanish
        from every screen with nothing to explain why.
        """
        form = UserUpdateForm(
            data={
                "username": "Kumar",
                "email": "kumar@auca.ac.rw",
                "role": "representative",
                "is_active": True,
            },
            instance=self.kumar_user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)


# ==========================================================
# SEARCH
# ==========================================================

class SearchHelperTests(AccountData):

    def test_blank_query_returns_everything(self):
        self.assertEqual(
            search(Lecturer.objects.all(), "", ("name",)).count(),
            Lecturer.objects.count(),
        )

    def test_search_is_case_insensitive_and_partial(self):
        found = search(Lecturer.objects.all(), "kum", ("name",))
        self.assertEqual([l.name for l in found], ["Kumar Kundan"])

    def test_every_term_must_match(self):
        """
        "marie claire" finds Marie Claire; "marie kumar" finds
        nobody, rather than everyone matching either word.
        """
        self.assertEqual(
            search(Lecturer.objects.all(), "marie claire", ("name",)).count(),
            1,
        )
        self.assertEqual(
            search(Lecturer.objects.all(), "marie kumar", ("name",)).count(),
            0,
        )

    def test_search_spans_related_fields(self):
        found = search(
            Lecturer.objects.all(),
            "Claire",
            ("name", "user__username"),
        )
        self.assertEqual(found.count(), 1)


class SearchViewTests(AccountData):

    def test_user_list_filters_and_reports_counts(self):
        self.sign_in_admin()

        response = self.client.get(
            reverse("accounts:user_list"),
            {"q": "kumar"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 1)
        self.assertTrue(response.context["is_searching"])
        self.assertEqual(
            response.context["total_count"],
            User.objects.count(),
        )

    def test_whitespace_query_is_not_a_search(self):
        self.sign_in_admin()

        response = self.client.get(
            reverse("accounts:user_list"),
            {"q": "   "},
        )

        self.assertFalse(response.context["is_searching"])
        self.assertEqual(
            response.context["result_count"],
            User.objects.count(),
        )

    def test_lecturer_search_does_not_widen_scope(self):
        """
        A lecturer searching their own dashboard can only ever match
        their own modules, whatever they type.
        """
        Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.claire,
            course=self.course,
            start_date=self.period.start_date,
            course_days="Monday",
        )

        self.client.force_login(self.kumar_user)

        response = self.client.get(
            reverse("workload:lecturer_dashboard"),
            {"q": "Advanced Databases"},
        )

        # The module belongs to Claire, so Kumar sees nothing.
        self.assertEqual(response.context["result_count"], 0)

    def test_admin_workload_search_matches_across_relations(self):
        Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.kumar,
            course=self.course,
            start_date=self.period.start_date,
            course_days="Monday",
        )

        self.sign_in_admin()

        response = self.client.get(
            reverse("workload:workload_list"),
            {"q": "Kumar"},
        )

        self.assertEqual(response.context["result_count"], 1)

    def test_search_box_renders_on_list_screens(self):
        self.sign_in_admin()

        for name in [
            "accounts:user_list",
            "academics:lecturer_list",
            "academics:course_list",
            "academics:cohort_list",
            "academics:faculty_list",
            "academics:program_list",
            "academics:academic_period_list",
            "academics:holiday_list",
            "workload:workload_list",
        ]:
            with self.subTest(screen=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="search-box"')


# The assignment screens are gone: Add Lecturer and Add Cohort
# already collect the link.

class AssignmentScreensRemovedTests(AccountData):

    def test_the_assignment_models_are_gone(self):

        import accounts.models as accounts_models

        self.assertFalse(
            hasattr(accounts_models, "LecturerAccountAssignment")
        )

        self.assertFalse(
            hasattr(accounts_models, "RepresentativeAccountAssignment")
        )

    def test_the_routes_no_longer_resolve(self):

        from django.urls import NoReverseMatch

        for name in [
            "accounts:lecturer_assignment_list",
            "accounts:create_lecturer_assignment",
            "accounts:representative_assignment_list",
            "accounts:create_representative_assignment",
        ]:
            with self.subTest(route=name):
                with self.assertRaises(NoReverseMatch):
                    reverse(name)

    def test_the_sidebar_does_not_link_to_them(self):
        """
        A dead {% url %} in base.html is not a broken link, it
        is a NoReverseMatch on every page that extends it.
        """
        self.sign_in_admin()

        response = self.client.get(reverse("accounts:user_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Lecturer Accounts")
        self.assertNotContains(response, "Representative Accounts")

    def test_every_admin_screen_still_loads(self):
        """
        The removal touched base.html and users.html, which every
        screen inherits from.
        """
        self.sign_in_admin()

        for name in [
            "accounts:user_list",
            "accounts:create_user",
            "academics:lecturer_list",
            "academics:cohort_list",
            "workload:workload_list",
            "workload:assignment",
        ]:
            with self.subTest(screen=name):
                self.assertEqual(
                    self.client.get(reverse(name)).status_code,
                    200,
                )


class LinkingStillReachesTheInboxTests(AccountData):
    """
    The removal must not cost anyone their notification email.
    """

    def test_lecturer_set_on_the_record_is_emailed(self):

        from workload.selectors import account_for_lecturer

        self.kumar_user.email = "kumar@auca.ac.rw"
        self.kumar_user.save()

        self.assertEqual(
            account_for_lecturer(self.kumar),
            self.kumar_user,
        )

    def test_representative_set_on_the_cohort_is_emailed(self):

        from workload.selectors import account_for_cohort

        rep = User.objects.create_user(
            username="Cohort5Rep",
            password="pw",
            role="representative",
            email="cohort5@auca.ac.rw",
        )

        self.cohort.representative = rep
        self.cohort.save()

        self.assertEqual(
            account_for_cohort(self.cohort),
            rep,
        )

    def test_an_unlinked_lecturer_resolves_to_nobody(self):
        """
        Not an error -- but it must be None, so the notification
        code reports it rather than emailing the wrong person.
        """

        from workload.selectors import account_for_lecturer

        self.kumar.user = None
        self.kumar.save()

        self.assertIsNone(account_for_lecturer(self.kumar))

    def test_adding_a_lecturer_with_an_account_links_in_one_step(self):
        """
        The premise of the removal: the Add Lecturer screen
        collects the account itself, so no second screen is
        needed to finish the job.
        """

        from academics.forms import LecturerForm

        new_user = User.objects.create_user(
            username="Fabrice",
            password="pw",
            role="lecturer",
            email="fabrice@auca.ac.rw",
        )

        form = LecturerForm(data={
            "user": new_user.pk,
            "name": "Dr. Fabrice Sibomana",
            "qualification": "PhD",
            "employment_status": "Regular",
        })

        self.assertTrue(form.is_valid(), form.errors)

        lecturer = form.save()

        from workload.selectors import account_for_lecturer, resolve_lecturer

        self.assertEqual(account_for_lecturer(lecturer), new_user)
        self.assertEqual(resolve_lecturer(new_user), lecturer)

    def test_add_lecturer_form_offers_only_lecturer_accounts(self):

        from academics.forms import LecturerForm

        usernames = set(
            LecturerForm().fields["user"].queryset.values_list(
                "username", flat=True
            )
        )

        self.assertIn("Kumar", usernames)
        self.assertNotIn("Dismas", usernames)
