# ==========================================================
# AUCA WORKLOAD MANAGEMENT SYSTEM
# TESTS: NOTIFICATIONS, CO-TEACHING, SPREADSHEET IMPORT
# ==========================================================


import logging

from datetime import date

from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from academics.models import (
    Faculty,
    Program,
    Cohort,
    AcademicPeriod,
    Lecturer,
    Course,
)

from accounts.models import (
    User,
)

from workload.models import Workload

from workload.notifications import (
    notify_assignment,
    resolve_recipients,
)

from workload.selectors import (
    account_for_cohort,
    account_for_lecturer,
    workloads_for_lecturer,
)

from workload.management.commands.import_workload_excel import (
    name_key,
    normalise_days,
    parse_period_cell,
    split_people,
)

from workload.utils import generate_course_schedule


# ==========================================================
# SHARED SETUP
# ==========================================================

class WorkloadFixture(TestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username="admin",
            password="pw",
            role="admin",
            email="admin@auca.ac.rw",
        )

        self.faculty = Faculty.objects.create(
            name="Faculty of Information Technology"
        )

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="MSc Big Data Analytics",
        )

        self.rep_user = User.objects.create_user(
            username="rep",
            password="pw",
            role="representative",
            email="rep@auca.ac.rw",
        )

        self.cohort = Cohort.objects.create(
            program=self.program,
            name="Cohort 9",
            intake_year=2026,
            representative=self.rep_user,
        )

        self.period = AcademicPeriod.objects.create(
            cohort=self.cohort,
            academic_year="2026-2028",
            semester="Semester 1",
            teaching_period="Sep - Oct",
            start_date=date(2026, 9, 13),
            end_date=date(2026, 10, 11),
        )

        self.lecturer_user = User.objects.create_user(
            username="pacifique",
            password="pw",
            role="lecturer",
            email="pacifique@auca.ac.rw",
        )

        self.lecturer = Lecturer.objects.create(
            user=self.lecturer_user,
            name="Nizeyimana Pacifique",
            qualification="Ph.D in Statistics",
            employment_status="Regular",
        )

        self.course = Course.objects.create(
            program=self.program,
            code="BDA91103",
            name="R for Data science",
            credits=3,
            level="MSC",
        )

    def make_workload(self, **overrides):

        values = {
            "cohort": self.cohort,
            "academic_period": self.period,
            "lecturer": self.lecturer,
            "course": self.course,
            "start_date": date(2026, 9, 13),
            "course_days": "Sunday,Thursday",
        }

        values.update(overrides)

        return Workload.objects.create(**values)


# ==========================================================
# RECIPIENTS
# ==========================================================

class RecipientTests(WorkloadFixture):

    def test_lecturer_and_representative_are_both_found(self):

        workload = self.make_workload()

        found, skipped = resolve_recipients(workload)

        self.assertEqual(skipped, [])

        self.assertEqual(
            sorted(r.email for r in found),
            ["pacifique@auca.ac.rw", "rep@auca.ac.rw"],
        )

    def test_co_lecturer_is_notified_too(self):
        """A co-teacher should not hear it from someone else."""

        david_user = User.objects.create_user(
            username="david",
            password="pw",
            role="lecturer",
            email="david@auca.ac.rw",
        )

        david = Lecturer.objects.create(
            user=david_user,
            name="Mr. David Hagumuwumva",
            employment_status="Regular",
        )

        workload = self.make_workload()

        workload.co_lecturers.add(david)

        found, _ = resolve_recipients(workload)

        self.assertIn("david@auca.ac.rw", [r.email for r in found])

    def test_a_lecturer_with_no_account_is_reported_not_skipped_silently(self):
        """
        Lecturer.user is now the only linkage path, so an empty
        one means nobody can be emailed. That has to be said out
        loud: an administrator who is not told assumes the
        lecturer knows about the module.
        """

        self.lecturer.user = None

        self.lecturer.save()

        self.assertIsNone(account_for_lecturer(self.lecturer))

        workload = self.make_workload()

        found, skipped = resolve_recipients(workload)

        self.assertNotIn(
            "pacifique@auca.ac.rw",
            [r.email for r in found],
        )

        reasons = " ".join(r.reason for r in skipped)

        self.assertIn("no user account", reasons)

    def test_a_cohort_with_no_representative_is_reported(self):
        """
        Same rule the other way round: a cohort whose
        representative field is empty has nobody to email, and
        the administrator is told which cohort.
        """

        self.cohort.representative = None

        self.cohort.save()

        self.assertIsNone(account_for_cohort(self.cohort))

        workload = self.make_workload()

        _, skipped = resolve_recipients(workload)

        reasons = " ".join(r.reason for r in skipped)

        self.assertIn("no class representative", reasons)

    def test_the_record_is_the_single_source_of_the_address(self):
        """
        The address emailed is the one on the linked account, so
        changing it on the Users screen changes where mail goes
        with nothing else to update.
        """

        self.lecturer_user.email = "new.address@auca.ac.rw"

        self.lecturer_user.save()

        workload = self.make_workload()

        found, _ = resolve_recipients(workload)

        self.assertIn(
            "new.address@auca.ac.rw",
            [r.email for r in found],
        )

    def test_missing_email_is_reported_not_swallowed(self):
        """
        The whole point of the skipped list: an administrator
        must not be told someone was notified when they were
        not.
        """

        self.lecturer_user.email = ""

        self.lecturer_user.save()

        workload = self.make_workload()

        found, skipped = resolve_recipients(workload)

        self.assertEqual([r.email for r in found], ["rep@auca.ac.rw"])

        self.assertEqual(len(skipped), 1)

        self.assertIn("no email address", skipped[0].reason)

    def test_cohort_without_representative_is_reported(self):

        self.cohort.representative = None

        self.cohort.save()

        workload = self.make_workload()

        _, skipped = resolve_recipients(workload)

        self.assertTrue(
            any(
                "no class representative" in r.reason
                for r in skipped
            )
        )

    def test_one_person_in_two_roles_is_emailed_once(self):

        self.rep_user.email = "pacifique@auca.ac.rw"

        self.rep_user.save()

        workload = self.make_workload()

        found, _ = resolve_recipients(workload)

        self.assertEqual(len(found), 1)


# ==========================================================
# SENDING
# ==========================================================

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="https://workload.auca.ac.rw",
)
class SendingTests(WorkloadFixture):

    def test_two_emails_go_out(self):

        workload = self.make_workload()

        result = notify_assignment(workload)

        self.assertEqual(len(mail.outbox), 2)

        self.assertTrue(result.all_delivered)

    def test_email_carries_the_assignment_detail(self):

        workload = self.make_workload()

        notify_assignment(workload)

        body = mail.outbox[0].body

        self.assertIn("BDA91103", body)

        self.assertIn("R for Data science", body)

        self.assertIn("Cohort 9", body)

        self.assertIn("Nizeyimana Pacifique", body)

        self.assertIn("Sunday,Thursday", body)

        self.assertIn("2026-2028", body)

        # Every class date, not just the span.
        self.assertIn("13 September 2026", body)

    def test_email_links_to_the_right_account(self):
        """
        The lecturer is sent to their workload and the
        representative to their calendar. Sending both to the
        same page would give one of them a permission error.
        """

        workload = self.make_workload()

        notify_assignment(workload)

        by_recipient = {
            message.to[0]: message.body
            for message in mail.outbox
        }

        lecturer_body = by_recipient["pacifique@auca.ac.rw"]

        rep_body = by_recipient["rep@auca.ac.rw"]

        self.assertIn(
            "https://workload.auca.ac.rw"
            + reverse("workload:lecturer_dashboard"),
            lecturer_body,
        )

        self.assertIn(
            "https://workload.auca.ac.rw"
            + reverse("workload:representative_dashboard"),
            rep_body,
        )

    def test_login_link_returns_to_the_same_page(self):

        workload = self.make_workload()

        notify_assignment(workload)

        body = mail.outbox[0].body

        self.assertIn(
            reverse("accounts:login")
            + "?next="
            + reverse("workload:lecturer_dashboard"),
            body,
        )

    def test_html_alternative_is_attached(self):

        workload = self.make_workload()

        notify_assignment(workload)

        message = mail.outbox[0]

        self.assertEqual(len(message.alternatives), 1)

        html, mimetype = message.alternatives[0]

        self.assertEqual(mimetype, "text/html")

        self.assertIn("R for Data science", html)

    def test_subject_has_no_newline(self):
        """A newline in a subject is a header-injection vector."""

        workload = self.make_workload()

        notify_assignment(workload)

        for message in mail.outbox:

            self.assertNotIn("\n", message.subject)

            self.assertNotIn("\r", message.subject)

    def test_update_says_updated_not_assigned(self):

        workload = self.make_workload()

        notify_assignment(workload, created=False)

        self.assertIn("Updated", mail.outbox[0].subject)

    def test_holidays_are_explained(self):

        from academics.models import Holiday

        Holiday.objects.create(
            date=date(2026, 9, 17),
            name="Test Holiday",
        )

        workload = self.make_workload()

        notify_assignment(workload)

        self.assertIn("Test Holiday", mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND="workload.tests_notifications.BrokenBackend",
)
class DeliveryFailureTests(WorkloadFixture):

    def setUp(self):

        super().setUp()

        # The failure below is deliberate and is logged with a
        # traceback by design. Silencing it here keeps the test
        # output readable, so a real error still stands out.
        logging.disable(logging.CRITICAL)

        self.addCleanup(logging.disable, logging.NOTSET)

    def test_a_dead_mail_server_does_not_lose_the_assignment(self):
        """
        The workload is saved before the email is attempted.
        Turning a successful save into a 500 because SMTP was
        unreachable would be the worse failure.
        """

        workload = self.make_workload()

        result = notify_assignment(workload)

        self.assertEqual(result.sent, [])

        self.assertTrue(result.failed)

        self.assertFalse(result.all_delivered)

        # And the row is still there.
        self.assertTrue(
            Workload.objects.filter(pk=workload.pk).exists()
        )


class BrokenBackend:
    """A mail backend that refuses to connect."""

    def __init__(self, *args, **kwargs):
        pass

    def open(self):
        raise OSError("Connection refused")

    def close(self):
        pass


# ==========================================================
# THE ASSIGN SCREEN
# ==========================================================

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
)
class AssignViewTests(WorkloadFixture):

    def setUp(self):

        super().setUp()

        self.client.force_login(self.admin)

    def post_assignment(self, **overrides):

        data = {
            "cohort": self.cohort.pk,
            "academic_period": self.period.pk,
            "lecturer": self.lecturer.pk,
            "course": self.course.pk,
            "start_date": "2026-09-13",
            "course_days": "Sunday,Thursday",
        }

        data.update(overrides)

        return self.client.post(
            reverse("workload:assignment"),
            data,
            follow=True,
        )

    def test_assigning_sends_the_emails(self):

        response = self.post_assignment()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Workload.objects.count(), 1)

        self.assertEqual(len(mail.outbox), 2)

    def test_administrator_is_told_who_was_notified(self):

        response = self.post_assignment()

        text = " ".join(
            str(m) for m in get_messages(response.wsgi_request)
        )

        self.assertIn("pacifique@auca.ac.rw", text)

        self.assertIn("rep@auca.ac.rw", text)

    def test_administrator_is_told_who_was_not_notified(self):

        self.cohort.representative = None

        self.cohort.save()

        response = self.post_assignment()

        text = " ".join(
            str(m) for m in get_messages(response.wsgi_request)
        )

        self.assertIn("no class representative", text)

        # The assignment still succeeded.
        self.assertEqual(Workload.objects.count(), 1)

    def test_co_lecturers_can_be_set_from_the_form(self):

        david = Lecturer.objects.create(
            name="Mr. David Hagumuwumva",
            employment_status="Regular",
        )

        self.post_assignment(co_lecturers=[david.pk])

        workload = Workload.objects.get()

        self.assertEqual(
            list(workload.co_lecturers.all()),
            [david],
        )

    def test_lead_lecturer_is_not_also_a_co_lecturer(self):

        self.post_assignment(co_lecturers=[self.lecturer.pk])

        workload = Workload.objects.get()

        self.assertEqual(workload.co_lecturers.count(), 0)


# ==========================================================
# CO-TEACHING VISIBILITY
# ==========================================================

class CoTeachingTests(WorkloadFixture):

    def test_co_lecturer_sees_the_module_on_their_dashboard(self):

        david_user = User.objects.create_user(
            username="david",
            password="pw",
            role="lecturer",
            email="david@auca.ac.rw",
        )

        david = Lecturer.objects.create(
            user=david_user,
            name="Mr. David Hagumuwumva",
            employment_status="Regular",
        )

        workload = self.make_workload()

        workload.co_lecturers.add(david)

        self.assertEqual(
            list(workloads_for_lecturer(david)),
            [workload],
        )

        self.client.force_login(david_user)

        response = self.client.get(
            reverse("workload:lecturer_dashboard")
        )

        self.assertContains(response, "R for Data science")

    def test_a_module_is_not_listed_twice(self):

        workload = self.make_workload()

        workload.co_lecturers.add(self.lecturer)

        self.assertEqual(
            workloads_for_lecturer(self.lecturer).count(),
            1,
        )

    def test_teaching_team_lists_the_lead_first(self):

        david = Lecturer.objects.create(
            name="Mr. David Hagumuwumva",
            employment_status="Regular",
        )

        workload = self.make_workload()

        workload.co_lecturers.add(david)

        self.assertEqual(
            workload.teaching_team(),
            [self.lecturer, david],
        )

    def test_scope_is_not_widened(self):
        """A lecturer must not see another lecturer's module."""

        other = Lecturer.objects.create(
            name="Someone Else",
            employment_status="Regular",
        )

        self.make_workload()

        self.assertEqual(
            workloads_for_lecturer(other).count(),
            0,
        )


# ==========================================================
# DURATION OVERRIDE
# ==========================================================

class DurationTests(WorkloadFixture):

    def test_blank_override_keeps_the_standard_block(self):

        workload = self.make_workload()

        # 3 credits = 4 weeks, two days a week.
        self.assertEqual(workload.total_classes(), 8)

    def test_override_lengthens_the_block(self):

        workload = self.make_workload(duration_weeks=13)

        self.assertEqual(workload.total_classes(), 26)

    def test_zero_falls_back_to_the_credit_length(self):

        schedule = generate_course_schedule(
            date(2026, 9, 13),
            3,
            "Sunday,Thursday",
            weeks=0,
        )

        self.assertEqual(len(schedule), 8)


# ==========================================================
# SPREADSHEET PARSING
# ==========================================================

class ParsingTests(TestCase):

    def test_dates_are_read_day_first(self):

        start, end, _ = parse_period_cell("12/7/2026 - 16/8/2026")

        self.assertEqual(start, date(2026, 7, 12))

        self.assertEqual(end, date(2026, 8, 16))

    def test_a_truncated_year_is_rebuilt_from_the_other_half(self):

        start, end, notes = parse_period_cell("8/9/2030 -13/10/203")

        self.assertEqual(start, date(2030, 9, 8))

        self.assertEqual(end, date(2030, 10, 13))

        self.assertTrue(notes)

    def test_an_impossible_year_is_rebuilt(self):

        start, end, _ = parse_period_cell("13/1/2031 - 15/4/3031")

        self.assertEqual(start, date(2031, 1, 13))

        self.assertEqual(end, date(2031, 4, 15))

    def test_a_backwards_range_moves_the_end_year(self):
        """
        "13/12/2026 - 13/3/2026" is a three-month term ending in
        March 2027, not a fifteen-month one starting in December
        2027.
        """

        start, end, notes = parse_period_cell("13/12/2026 - 13/3/2026")

        self.assertEqual(start, date(2026, 12, 13))

        self.assertEqual(end, date(2027, 3, 13))

        self.assertTrue(notes)

    def test_an_unreadable_half_is_reported_not_guessed(self):

        start, end, notes = parse_period_cell("../7/2026 - 2/8/2026")

        self.assertEqual(end, date(2026, 8, 2))

        self.assertTrue(notes)

    def test_an_empty_cell_yields_nothing(self):

        start, end, notes = parse_period_cell(None)

        self.assertIsNone(start)

        self.assertIsNone(end)

        self.assertTrue(notes)

    def test_the_recurring_thursday_misspelling(self):

        days, note = normalise_days("Sunday, Thusday")

        self.assertEqual(days, "Sunday,Thursday")

        self.assertIn("Thursday", note)

    def test_days_separated_by_a_space(self):

        days, _ = normalise_days("Sunday Thusday")

        self.assertEqual(days, "Sunday,Thursday")

    def test_upper_case_days(self):

        days, _ = normalise_days("SUNDAY, Thusday")

        self.assertEqual(days, "Sunday,Thursday")

    def test_all_days_means_the_working_week(self):
        """
        Internship and Thesis say "All days". Read literally
        that scheduled Saturday and Sunday sittings on every
        placement, and gave a thirteen-week internship 91 class
        dates. Nobody supervises at the weekend.
        """

        days, note = normalise_days("All days")

        self.assertEqual(
            days,
            "Monday,Tuesday,Wednesday,Thursday,Friday",
        )

        self.assertNotIn("Saturday", days)

        self.assertNotIn("Sunday", days)

        self.assertTrue(note)

    def test_the_same_person_written_two_ways(self):

        self.assertEqual(
            name_key("Dr. Pacifique Nizeyimana"),
            name_key("Nizeyimana Pacifique"),
        )

        self.assertEqual(
            name_key("Dr. Eric Nizeyimana"),
            name_key("Eric Nizeyimana"),
        )

    def test_different_people_do_not_collide(self):

        self.assertNotEqual(
            name_key("Eric Nizeyimana"),
            name_key("Pacifique Nizeyimana"),
        )

    def test_co_teachers_split_on_comma_and_slash(self):

        self.assertEqual(
            split_people("Dr. Eric Nizeyimana, Mr. david Hagumuwumva"),
            ["Dr. Eric Nizeyimana", "Mr. david Hagumuwumva"],
        )

        self.assertEqual(
            split_people("Dr.Eric Nizeyimana/ Dr. Kumar Kundan"),
            ["Dr.Eric Nizeyimana", "Dr. Kumar Kundan"],
        )


# ==========================================================
# PER-COHORT ACADEMIC PERIODS
# ==========================================================

class PeriodScopingTests(WorkloadFixture):

    def test_two_cohorts_can_share_a_year_and_semester(self):
        """
        The spreadsheet has Cohort 12 and Cohort 13 both running
        "2028 - 2030" Semester 1 ten months apart. Before the
        cohort field this could not be recorded at all.
        """

        other = Cohort.objects.create(
            program=self.program,
            name="Cohort 10",
            intake_year=2027,
        )

        AcademicPeriod.objects.create(
            cohort=other,
            academic_year="2026-2028",
            semester="Semester 1",
            teaching_period="Apr - May",
            start_date=date(2027, 4, 18),
            end_date=date(2027, 5, 16),
        )

        self.assertEqual(
            AcademicPeriod.objects.filter(
                academic_year="2026-2028",
                semester="Semester 1",
            ).count(),
            2,
        )

    def test_the_cohort_is_named_in_the_label(self):

        self.assertIn("Cohort 9", str(self.period))
