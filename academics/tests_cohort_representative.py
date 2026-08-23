import re

# Tests: linking a class to its representative.
# CohortForm is the only path, so the OneToOne rules live there.

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from academics.models import Faculty, Program, Cohort
from academics.forms import CohortForm


User = get_user_model()


class CohortRepresentativeTests(TestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas",
            password="pw",
            role="admin",
        )

        self.client.force_login(self.admin)

        self.faculty = Faculty.objects.create(name="IT")

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="BSc IT",
        )

        self.cohort_a = Cohort.objects.create(
            program=self.program,
            name="Cohort 5",
            intake_year=2023,
        )

        self.cohort_b = Cohort.objects.create(
            program=self.program,
            name="Cohort 6",
            intake_year=2024,
        )

        self.rep_a = User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
            email="jimmy@auca.ac.rw",
        )

        self.rep_b = User.objects.create_user(
            username="arthur",
            password="pw",
            role="representative",
            email="arthur@auca.ac.rw",
        )

    # ------------------------------------------------------
    # The dedicated screen is gone
    # ------------------------------------------------------

    def test_no_representative_screen_exists(self):
        """
        Removed on purpose. Representatives are reached through
        Users; the link is set on the cohort.
        """

        for path in [
            "/academics/representatives/",
            "/academics/representatives/create/",
        ]:
            self.assertEqual(
                self.client.get(path).status_code,
                404,
                msg=f"{path} should no longer resolve",
            )

    def test_sidebar_does_not_offer_one(self):

        response = self.client.get(
            reverse("academics:cohort_list")
        )

        self.assertNotContains(response, "Class Representatives")

    # ------------------------------------------------------
    # The cohort form is the link
    # ------------------------------------------------------

    def test_editing_a_cohort_sets_the_representative(self):

        response = self.client.post(
            reverse(
                "academics:cohort_update",
                args=[self.cohort_a.pk],
            ),
            {
                "program": self.program.pk,
                "name": "Cohort 5",
                "intake_year": 2023,
                "representative": self.rep_a.pk,
            },
        )

        self.assertEqual(response.status_code, 302)

        self.cohort_a.refresh_from_db()
        self.assertEqual(self.cohort_a.representative, self.rep_a)

    def test_representative_can_be_cleared(self):
        """The field is optional, so blank means nobody."""

        self.cohort_a.representative = self.rep_a
        self.cohort_a.save()

        self.client.post(
            reverse(
                "academics:cohort_update",
                args=[self.cohort_a.pk],
            ),
            {
                "program": self.program.pk,
                "name": "Cohort 5",
                "intake_year": 2023,
                "representative": "",
            },
        )

        self.cohort_a.refresh_from_db()
        self.assertIsNone(self.cohort_a.representative)

    # ------------------------------------------------------
    # The OneToOne constraint
    # ------------------------------------------------------

    def test_only_representative_accounts_are_offered(self):

        lecturer_account = User.objects.create_user(
            username="kumar",
            password="pw",
            role="lecturer",
        )

        offered = CohortForm().fields["representative"].queryset

        self.assertIn(self.rep_a, offered)
        self.assertNotIn(lecturer_account, offered)

    def test_an_account_held_by_another_cohort_is_not_offered(self):
        """
        Cohort.representative is OneToOne, so a second cohort
        pointing at the same account is a UNIQUE constraint
        error, not a choice to put in front of an administrator.
        """

        self.cohort_b.representative = self.rep_b
        self.cohort_b.save()

        offered = CohortForm(
            instance=self.cohort_a
        ).fields["representative"].queryset

        self.assertNotIn(self.rep_b, offered)
        self.assertIn(self.rep_a, offered)

    def test_the_current_holder_stays_selectable(self):
        """
        Or re-showing the form would blank a valid value and the
        dropdown could not render its own current choice.
        """

        self.cohort_a.representative = self.rep_a
        self.cohort_a.save()

        offered = CohortForm(
            instance=self.cohort_a
        ).fields["representative"].queryset

        self.assertIn(self.rep_a, offered)

    def test_a_taken_account_is_rejected_not_a_500(self):
        """
        Hiding a choice is not validation: a stale page could
        still post it. The form has to refuse it.
        """

        self.cohort_b.representative = self.rep_b
        self.cohort_b.save()

        form = CohortForm(
            data={
                "program": self.program.pk,
                "name": "Cohort 5",
                "intake_year": 2023,
                "representative": self.rep_b.pk,
            },
            instance=self.cohort_a,
        )

        self.assertFalse(form.is_valid())

        self.cohort_b.refresh_from_db()
        self.assertEqual(self.cohort_b.representative, self.rep_b)

    # ------------------------------------------------------
    # Visibility of gaps
    # ------------------------------------------------------

    def test_cohort_list_flags_a_class_with_nobody(self):
        """
        The one thing the removed screen was good for: seeing at
        a glance which classes nobody is notified for.
        """

        response = self.client.get(
            reverse("academics:cohort_list")
        )

        self.assertContains(response, "Not assigned")

    def test_cohort_list_flags_an_account_with_no_email(self):

        silent = User.objects.create_user(
            username="silent",
            password="pw",
            role="representative",
        )

        self.cohort_a.representative = silent
        self.cohort_a.save()

        response = self.client.get(
            reverse("academics:cohort_list")
        )

        self.assertContains(response, "No email")

    def test_cohort_search_matches_representative(self):

        self.cohort_a.representative = self.rep_a
        self.cohort_a.save()

        response = self.client.get(
            reverse("academics:cohort_list"),
            {"q": "jimmy"},
        )

        self.assertEqual(len(response.context["cohorts"]), 1)


class UserRoleFilterTests(TestCase):
    """
    The Users screen is the way in to representatives now, so it
    has to be able to show just them.
    """

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas",
            password="pw",
            role="admin",
        )

        self.client.force_login(self.admin)

        User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
        )

        User.objects.create_user(
            username="kumar",
            password="pw",
            role="lecturer",
        )

    def test_role_filter_narrows_the_list(self):

        response = self.client.get(
            reverse("accounts:user_list"),
            {"role": "representative"},
        )

        usernames = [u.username for u in response.context["users"]]

        self.assertEqual(usernames, ["jimmy"])

    def test_no_filter_shows_everyone(self):

        response = self.client.get(
            reverse("accounts:user_list")
        )

        self.assertEqual(
            len(response.context["users"]),
            User.objects.count(),
        )

    def test_an_unknown_role_is_ignored_not_obeyed(self):
        """A tampered value must not empty the screen."""

        response = self.client.get(
            reverse("accounts:user_list"),
            {"role": "wizard"},
        )

        self.assertEqual(
            len(response.context["users"]),
            User.objects.count(),
        )

    def test_search_stays_within_the_filtered_role(self):

        response = self.client.get(
            reverse("accounts:user_list"),
            {"role": "representative", "q": "kumar"},
        )

        self.assertEqual(len(response.context["users"]), 0)


class AddCohortDropdownTests(TestCase):
    """
    The representative dropdown on Add Cohort. It lists user
    accounts with role="representative", and has to explain
    itself when it has nothing to list.
    """

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas",
            password="pw",
            role="admin",
        )

        self.client.force_login(self.admin)

        self.faculty = Faculty.objects.create(name="IT")

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="BSc IT",
        )

    def test_free_accounts_are_offered(self):

        rep = User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
            email="jimmy@auca.ac.rw",
        )

        offered = CohortForm().fields["representative"].queryset

        self.assertIn(rep, offered)

    def test_option_label_shows_the_email(self):
        """
        The address is what receives the workload notification,
        so it belongs in the option, not one screen away.
        """

        rep = User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
            email="jimmy@auca.ac.rw",
        )

        field = CohortForm().fields["representative"]

        self.assertEqual(
            field.label_from_instance(rep),
            "jimmy (jimmy@auca.ac.rw)",
        )

    def test_option_label_flags_a_missing_email(self):

        silent = User.objects.create_user(
            username="silent",
            password="pw",
            role="representative",
        )

        field = CohortForm().fields["representative"]

        self.assertIn(
            "no email address",
            field.label_from_instance(silent),
        )

    def test_a_new_cohort_can_be_added_with_a_representative(self):

        rep = User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
        )

        response = self.client.post(
            reverse("academics:cohort_create"),
            {
                "program": self.program.pk,
                "name": "Cohort 15",
                "intake_year": 2026,
                "representative": rep.pk,
            },
        )

        self.assertEqual(response.status_code, 302)

        cohort = Cohort.objects.get(name="Cohort 15")
        self.assertEqual(cohort.representative, rep)

    def test_representative_stays_optional(self):
        """
        A cohort is usually created before anyone knows who will
        represent it, so a blank must still save.
        """

        response = self.client.post(
            reverse("academics:cohort_create"),
            {
                "program": self.program.pk,
                "name": "Cohort 16",
                "intake_year": 2026,
                "representative": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Cohort.objects.filter(name="Cohort 16").exists()
        )

    # ------------------------------------------------------
    # Empty states
    # ------------------------------------------------------

    def test_help_says_when_no_accounts_exist_at_all(self):

        response = self.client.get(
            reverse("academics:cohort_create")
        )

        self.assertContains(
            response,
            "No class representative accounts exist yet",
        )

    def test_help_says_when_every_account_is_taken(self):
        """
        The state the live database is in: accounts exist, but
        each already holds a cohort. Without this the dropdown
        just looks broken.
        """

        rep = User.objects.create_user(
            username="jimmy",
            password="pw",
            role="representative",
        )

        Cohort.objects.create(
            program=self.program,
            name="Cohort 5",
            intake_year=2023,
            representative=rep,
        )

        response = self.client.get(
            reverse("academics:cohort_create")
        )

        self.assertContains(response, "already assigned to a cohort")

    def test_empty_state_links_to_create_user(self):

        response = self.client.get(
            reverse("academics:cohort_create")
        )

        self.assertContains(
            response,
            reverse("accounts:create_user"),
        )


class ActionButtonTests(TestCase):
    """
    Every list screen renders its Edit/Delete pair the same way:
    the compact table tier, each with an icon, inside a
    .table-actions row that never wraps, inside a table that can
    scroll sideways instead.
    """

    LIST_URLS = [
        "academics:faculty_list",
        "academics:program_list",
        "academics:cohort_list",
        "academics:course_list",
        "academics:lecturer_list",
        "academics:holiday_list",
        "academics:academic_period_list",
        "accounts:user_list",
        "workload:workload_list",
        "workload:assignment",
    ]

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas",
            password="pw",
            role="admin",
        )

        self.client.force_login(self.admin)

        self.faculty = Faculty.objects.create(name="IT")

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="BSc IT",
        )

        self.cohort = Cohort.objects.create(
            program=self.program,
            name="Cohort 5",
            intake_year=2023,
        )

        # A row is required, or the action cells never render and
        # the assertions below pass against an empty table.
        from academics.models import AcademicPeriod, Course, Lecturer
        from workload.models import Workload
        from datetime import date

        period = AcademicPeriod.objects.create(
            academic_year="2025/2026",
            semester="Semester 1",
            teaching_period="Jan - Jun 2026",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 6, 30),
        )

        course = Course.objects.create(
            program=self.program,
            code="IT101",
            name="Big Data Analytics",
            credits=3,
            level="Masters",
        )

        lecturer = Lecturer.objects.create(
            name="Dr. Eric Nizeyimana",
            employment_status="Full Time",
        )

        Workload.objects.create(
            cohort=self.cohort,
            academic_period=period,
            lecturer=lecturer,
            course=course,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 2, 6),
            hours=45,
            course_days="Monday,Tuesday",
        )

    def test_every_list_scrolls_sideways(self):
        """
        A wide table must scroll rather than squeeze its columns,
        which is what pushed the action buttons under each other.
        """

        for name in self.LIST_URLS:

            response = self.client.get(reverse(name))

            self.assertContains(
                response,
                'class="table-scroll"',
                msg_prefix=f"{name} has no horizontal scroll",
            )

    def test_action_buttons_use_the_compact_tier(self):

        response = self.client.get(
            reverse("workload:workload_list")
        )

        for cls in ["view-btn", "edit-btn", "delete-link"]:

            self.assertContains(
                response,
                cls,
                msg_prefix="workload list",
            )

    def test_workload_action_buttons_have_icons(self):
        """
        The workload page used the full-size classes with no
        icons, so its actions did not match any other screen.
        """

        response = self.client.get(
            reverse("workload:workload_list")
        )

        for icon in ["fa-eye", "fa-pen", "fa-trash"]:

            self.assertContains(response, icon)

    def test_no_list_uses_the_full_size_tier_in_a_row(self):
        """
        .btn-primary / .btn-danger are page actions, 42px tall.
        Using them inside a table row is what made the workload
        buttons taller than everywhere else.
        """

        for name in ["workload:workload_list", "workload:assignment"]:

            html = self.client.get(reverse(name)).content.decode()

            for cell in re.findall(
                r'<div class="table-actions">.*?</div>', html, re.S
            ):
                self.assertNotIn("btn-primary", cell)
                self.assertNotIn("btn-danger", cell)


class FeedbackMessageTests(TestCase):
    """
    Every action that changes something has to say so, and every
    action that changes nothing has to say that too. A form that
    silently re-renders looks like it was ignored.
    """

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas",
            password="pw",
            role="admin",
        )

        self.client.force_login(self.admin)

    def _messages(self, response):

        return [str(m) for m in response.context["messages"]]

    def test_adding_says_what_was_added(self):

        response = self.client.post(
            reverse("academics:faculty_create"),
            {"name": "Information Technology", "description": ""},
            follow=True,
        )

        text = " ".join(self._messages(response))

        self.assertIn("Faculty", text)
        self.assertIn("added successfully", text)

    def test_updating_says_updated_not_added(self):

        faculty = Faculty.objects.create(name="IT")

        response = self.client.post(
            reverse("academics:faculty_update", args=[faculty.pk]),
            {"name": "Info Tech", "description": ""},
            follow=True,
        )

        text = " ".join(self._messages(response))

        self.assertIn("updated successfully", text)
        self.assertNotIn("added successfully", text)

    def test_deleting_names_the_record(self):

        faculty = Faculty.objects.create(name="IT")

        response = self.client.post(
            reverse("academics:faculty_delete", args=[faculty.pk]),
            {},
            follow=True,
        )

        text = " ".join(self._messages(response))

        self.assertIn("IT", text)
        self.assertIn("deleted successfully", text)

    def test_an_invalid_form_is_not_silent(self):
        """
        The failing case. Field errors can scroll out of sight on
        a long form, leaving the page looking like it ignored the
        click.
        """

        response = self.client.post(
            reverse("academics:faculty_create"),
            {"name": "", "description": ""},
        )

        text = " ".join(self._messages(response))

        self.assertIn("Nothing was saved", text)

    def test_a_failed_workload_assignment_is_not_silent(self):

        response = self.client.post(
            reverse("workload:assignment"),
            {},
        )

        text = " ".join(self._messages(response))

        self.assertIn("Nothing was assigned", text)

    def test_a_failed_workload_edit_is_not_silent(self):

        from workload.models import Workload
        from academics.models import AcademicPeriod, Course, Lecturer
        from datetime import date

        faculty = Faculty.objects.create(name="IT")
        program = Program.objects.create(faculty=faculty, name="BSc IT")
        cohort = Cohort.objects.create(
            program=program, name="Cohort 5", intake_year=2023
        )
        period = AcademicPeriod.objects.create(
            academic_year="2025/2026",
            semester="Semester 1",
            teaching_period="Jan - Jun 2026",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 6, 30),
        )
        course = Course.objects.create(
            program=program, code="IT101", name="Data",
            credits=3, level="Masters",
        )
        lecturer = Lecturer.objects.create(
            name="Kumar", employment_status="Full Time"
        )
        workload = Workload.objects.create(
            cohort=cohort, academic_period=period, lecturer=lecturer,
            course=course, start_date=date(2026, 1, 5),
            end_date=date(2026, 2, 6), hours=45,
            course_days="Monday",
        )

        response = self.client.post(
            reverse("workload:workload_update", args=[workload.pk]),
            {},
        )

        text = " ".join(self._messages(response))

        self.assertIn("Nothing was changed", text)

    def test_bad_login_is_reported(self):

        client = Client()

        response = client.post(
            reverse("accounts:login"),
            {"username": "nobody", "password": "wrong"},
            follow=True,
        )

        text = " ".join(self._messages(response))

        self.assertIn("Invalid username or password", text)


class LoginPageTests(TestCase):

    def test_password_field_has_a_show_toggle(self):

        response = Client().get(reverse("accounts:login"))

        self.assertContains(response, 'id="togglePassword"')
        self.assertContains(response, "fa-eye")

    def test_the_toggle_is_a_button_not_a_submit(self):
        """
        Inside the login <form>, a button without type="button"
        defaults to submit -- clicking the eye would post the
        form instead of revealing the password.
        """

        html = Client().get(reverse("accounts:login")).content.decode()

        i = html.find('id="togglePassword"')
        start = html.rfind("<button", 0, i)

        self.assertIn('type="button"', html[start:i])


class LecturerColumnTests(TestCase):

    def test_qualification_cell_is_marked_wrappable(self):
        """
        Free text of no fixed length. Held on one line it pushed
        the Actions column off the screen.
        """

        admin = User.objects.create_user(
            username="dismas", password="pw", role="admin"
        )
        self.client.force_login(admin)

        from academics.models import Lecturer

        Lecturer.objects.create(
            name="Kumar Kundan",
            employment_status="Full Time",
            qualification=(
                "Ph.D in Computer Science, "
                "Ph. D candidate in Data science"
            ),
        )

        response = self.client.get(
            reverse("academics:lecturer_list")
        )

        self.assertContains(response, 'class="col-qualification"')
