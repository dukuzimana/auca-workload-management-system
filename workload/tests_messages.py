# Tests: feedback after an action.
#
# base.html rendered no messages block at all, so all 28
# messages.success/error/warning calls in the project were
# invisible -- a click looked like it had done nothing.

import re
from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from academics.models import (
    Faculty, Program, Cohort, AcademicPeriod, Course, Lecturer,
)
from workload.models import Workload


User = get_user_model()


def alert_tags(response):
    """The kind of every alert on the page, in order."""

    return re.findall(
        r'<div class="alert alert-(\w+)">',
        response.content.decode(),
    )


def alert_text(response):
    """All alert copy as one normalised string."""

    html = response.content.decode()
    body = "".join(
        re.findall(
            r'<span class="alert-text">(.*?)</span>',
            html,
            re.S,
        )
    )
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", body)).strip()


class Fixtures(TestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username="dismas", password="pw", role="admin",
        )

        self.client.force_login(self.admin)

        self.faculty = Faculty.objects.create(name="IT")

        self.program = Program.objects.create(
            faculty=self.faculty, name="BSc IT",
        )


class AcademicsMessageTests(Fixtures):
    """
    Every academics screen saves through one helper, so
    confirming it once confirms Faculty, Program, Cohort,
    Course, Lecturer, Academic Period and Holiday.
    """

    def test_adding_a_lecturer_is_confirmed(self):

        response = self.client.post(
            reverse("academics:lecturer_create"),
            {
                "name": "Dr. Test",
                "qualification": "PhD in Testing",
                "employment_status": "Full Time",
                "user": "",
            },
            follow=True,
        )

        self.assertIn("success", alert_tags(response))
        self.assertIn("Lecturer", alert_text(response))
        self.assertIn("added successfully", alert_text(response))

    def test_updating_says_updated_not_added(self):

        lecturer = Lecturer.objects.create(
            name="Dr. Test", employment_status="Full Time",
        )

        response = self.client.post(
            reverse("academics:lecturer_update", args=[lecturer.pk]),
            {
                "name": "Dr. Tested",
                "qualification": "PhD",
                "employment_status": "Full Time",
                "user": "",
            },
            follow=True,
        )

        self.assertIn("updated successfully", alert_text(response))
        self.assertNotIn("added successfully", alert_text(response))

    def test_deleting_is_confirmed_by_name(self):
        """
        The name has to be read before the delete, or there is
        no instance left to read it from.
        """

        lecturer = Lecturer.objects.create(
            name="Dr. Gone", employment_status="Full Time",
        )

        response = self.client.post(
            reverse("academics:lecturer_delete", args=[lecturer.pk]),
            follow=True,
        )

        self.assertIn("Dr. Gone", alert_text(response))
        self.assertIn("deleted successfully", alert_text(response))

    def test_a_rejected_form_says_nothing_was_saved(self):

        response = self.client.post(
            reverse("academics:faculty_create"),
            {"name": "", "description": ""},
            follow=True,
        )

        self.assertIn("error", alert_tags(response))
        self.assertIn("Nothing was saved", alert_text(response))
        self.assertEqual(Faculty.objects.count(), 1)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="smtp.example.com",
)
class WorkloadMessageTests(Fixtures):

    def setUp(self):

        super().setUp()

        lecturer_user = User.objects.create_user(
            username="kumar", password="pw",
            role="lecturer", email="kumar@auca.ac.rw",
        )

        representative = User.objects.create_user(
            username="jimmy", password="pw",
            role="representative", email="jimmy@auca.ac.rw",
        )

        self.cohort = Cohort.objects.create(
            program=self.program, name="Cohort 5",
            intake_year=2023, representative=representative,
        )

        self.period = AcademicPeriod.objects.create(
            academic_year="2025/2026", semester="Semester 1",
            teaching_period="Jan - Jun 2026",
            start_date=date(2026, 1, 5), end_date=date(2026, 6, 30),
        )

        self.course = Course.objects.create(
            program=self.program, code="IT101",
            name="Big Data Analytics", credits=3, level="Masters",
        )

        self.lecturer = Lecturer.objects.create(
            name="Kumar Kundan", employment_status="Full Time",
            user=lecturer_user,
        )

    def assign(self, **overrides):

        data = {
            "cohort": self.cohort.pk,
            "academic_period": self.period.pk,
            "lecturer": self.lecturer.pk,
            "course": self.course.pk,
            "start_date": "2026-01-05",
            "hours": 45,
            "course_days": "Monday,Tuesday",
        }
        data.update(overrides)

        return self.client.post(
            reverse("workload:assignment"), data, follow=True,
        )

    def test_assignment_names_what_was_assigned(self):

        text = alert_text(self.assign())

        self.assertIn("assigned successfully", text)
        self.assertIn("Kumar Kundan", text)
        self.assertIn("Cohort 5", text)

    def test_the_email_outcome_is_reported_separately(self):
        """
        Kept apart from the save confirmation on purpose:
        "assigned successfully" is true even when nobody could
        be reached, and merging the two would let a silent
        non-delivery hide behind a green tick.
        """

        response = self.assign()

        self.assertIn("assigned successfully", alert_text(response))
        self.assertIn("Notification sent to", alert_text(response))
        self.assertIn("kumar@auca.ac.rw", alert_text(response))
        self.assertIn("jimmy@auca.ac.rw", alert_text(response))

    def test_a_class_with_no_representative_is_flagged(self):
        """
        The assignment still stands, but somebody has to be told
        that half the intended audience heard nothing.
        """

        self.cohort.representative = None
        self.cohort.save()

        response = self.assign()

        self.assertIn("assigned successfully", alert_text(response))
        self.assertIn("warning", alert_tags(response))

    def test_a_rejected_assignment_lists_the_fields(self):

        response = self.client.post(
            reverse("workload:assignment"),
            {"cohort": "", "course": ""},
            follow=True,
        )

        html = response.content.decode()

        self.assertIn("The workload was not assigned", html)
        self.assertIn("Course:", html)
        self.assertEqual(Workload.objects.count(), 0)

    def test_the_error_is_not_reported_twice(self):
        """
        The view used to add its own summary on top of the
        template's list, so one mistake produced two alerts.
        """

        response = self.client.post(
            reverse("workload:assignment"),
            {"cohort": "", "course": ""},
            follow=True,
        )

        self.assertEqual(len(alert_tags(response)), 1)


class LoginPageTests(TestCase):

    def test_password_field_has_a_visibility_toggle(self):

        html = self.client.get(reverse("accounts:login")).content.decode()

        self.assertIn('id="togglePassword"', html)
        self.assertIn("fa-eye", html)

    def test_the_toggle_reports_its_state(self):
        """
        A button whose meaning is only its icon needs a label,
        or a screen reader announces nothing useful.
        """

        html = self.client.get(reverse("accounts:login")).content.decode()

        self.assertIn('aria-pressed="false"', html)
        self.assertIn('aria-label="Show password"', html)

    def test_the_password_still_starts_hidden(self):

        html = self.client.get(reverse("accounts:login")).content.decode()

        self.assertIn('type="password"', html)
