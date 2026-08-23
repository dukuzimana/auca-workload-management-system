# Tests: notification from the Django admin, and .env loading.


import os

from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path

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

from accounts.models import User

from config.settings import _load_env_file

from workload.models import Workload


SMTP_LIKE = "django.core.mail.backends.locmem.EmailBackend"


# ==========================================================
# SHARED SETUP
# ==========================================================

class AdminFixture(TestCase):
    """A workload that has somebody reachable at both ends."""

    def setUp(self):

        self.superuser = User.objects.create_superuser(
            username="root",
            password="pw",
            email="root@auca.ac.rw",
            role="admin",
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
            employment_status="Regular",
        )

        self.course = Course.objects.create(
            program=self.program,
            code="BDA91103",
            name="R for Data science",
            credits=3,
            level="MSC",
        )

        self.client.force_login(self.superuser)

    def post_data(self, **overrides):

        data = {
            "cohort": self.cohort.pk,
            "academic_period": self.period.pk,
            "lecturer": self.lecturer.pk,
            "course": self.course.pk,
            "start_date": "2026-09-13",
            "course_days": "Sunday,Thursday",
            "co_lecturers": [],
            "duration_weeks": "",
        }

        data.update(overrides)

        return data

    def recipients_of_sent_mail(self):

        addresses = []

        for message in mail.outbox:
            addresses.extend(message.to)

        return sorted(addresses)


# ==========================================================
# ASSIGNING FROM THE DJANGO ADMIN
# ==========================================================

@override_settings(EMAIL_BACKEND=SMTP_LIKE)
class AdminAssignmentNotificationTests(AdminFixture):

    def test_adding_a_workload_emails_lecturer_and_representative(self):
        """The gap this exists to close."""

        mail.outbox = []

        response = self.client.post(
            reverse("admin:workload_workload_add"),
            self.post_data(),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Workload.objects.count(), 1)

        self.assertEqual(
            self.recipients_of_sent_mail(),
            ["pacifique@auca.ac.rw", "rep@auca.ac.rw"],
        )

    def test_added_workload_is_worded_as_an_assignment(self):

        mail.outbox = []

        self.client.post(
            reverse("admin:workload_workload_add"),
            self.post_data(),
            follow=True,
        )

        body = mail.outbox[0].body.lower()

        self.assertNotIn("updated", body)

    def test_editing_a_workload_emails_both_again(self):
        """An edit moves real class dates, so both are told."""

        workload = Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.lecturer,
            course=self.course,
            start_date=date(2026, 9, 13),
            course_days="Sunday,Thursday",
        )

        mail.outbox = []

        self.client.post(
            reverse(
                "admin:workload_workload_change",
                args=[workload.pk],
            ),
            self.post_data(start_date="2026-09-20"),
            follow=True,
        )

        workload.refresh_from_db()

        self.assertEqual(workload.start_date, date(2026, 9, 20))

        self.assertEqual(
            self.recipients_of_sent_mail(),
            ["pacifique@auca.ac.rw", "rep@auca.ac.rw"],
        )

    def test_edit_is_worded_as_an_update_not_a_new_assignment(self):

        workload = Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.lecturer,
            course=self.course,
            start_date=date(2026, 9, 13),
            course_days="Sunday,Thursday",
        )

        mail.outbox = []

        self.client.post(
            reverse(
                "admin:workload_workload_change",
                args=[workload.pk],
            ),
            self.post_data(start_date="2026-09-20"),
            follow=True,
        )

        self.assertIn(
            "updated",
            (mail.outbox[0].subject + mail.outbox[0].body).lower(),
        )

    def test_co_lecturer_added_in_the_same_save_is_emailed(self):
        """
        The reason this hangs off save_related, not save_model.

        At save_model time the co_lecturers rows are not written
        yet, so the teaching team would read as the lead alone
        and a co-teacher added in that same edit would never
        hear about the module they are teaching.
        """

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

        mail.outbox = []

        self.client.post(
            reverse("admin:workload_workload_add"),
            self.post_data(co_lecturers=[david.pk]),
            follow=True,
        )

        self.assertIn(
            "david@auca.ac.rw",
            self.recipients_of_sent_mail(),
        )

    def test_the_administrator_is_told_who_was_not_reached(self):
        """
        A cohort with no representative must be reported, not
        passed over in silence.
        """

        self.cohort.representative = None

        self.cohort.save()

        response = self.client.post(
            reverse("admin:workload_workload_add"),
            self.post_data(),
            follow=True,
        )

        text = " ".join(
            str(m) for m in get_messages(response.wsgi_request)
        )

        self.assertIn("not notified", text.lower())

    def test_a_dead_mail_server_does_not_lose_the_assignment(self):
        """
        Delivery never breaks the save. Losing the assignment
        because SMTP refused would be the worse failure.
        """

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
            EMAIL_HOST="127.0.0.1",
            EMAIL_PORT=1,
            EMAIL_TIMEOUT=1,
        ):

            response = self.client.post(
                reverse("admin:workload_workload_add"),
                self.post_data(),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Workload.objects.count(), 1)

    def test_console_backend_is_reported_as_not_delivered(self):
        """
        "Sent" while Django only printed to the terminal is the
        single most misleading thing this screen can say.
        """

        with override_settings(
            EMAIL_BACKEND=(
                "django.core.mail.backends.console.EmailBackend"
            )
        ):

            response = self.client.post(
                reverse("admin:workload_workload_add"),
                self.post_data(),
                follow=True,
            )

        text = " ".join(
            str(m) for m in get_messages(response.wsgi_request)
        )

        self.assertIn("NOT delivered", text)


# ==========================================================
# .env LOADING
# ==========================================================

class EnvFileTests(TestCase):
    """
    A filled-in `.env` has to actually reach os.environ, or the
    system reports itself configured and still delivers nothing.
    """

    # Deliberately not the real setting names: settings.py loads
    # the project .env at import time.

    HOST = "AUCA_TEST_EMAIL_HOST"
    PORT = "AUCA_TEST_EMAIL_PORT"
    USER = "AUCA_TEST_EMAIL_USER"
    SECRET = "AUCA_TEST_EMAIL_PASSWORD"
    SENDER = "AUCA_TEST_DEFAULT_FROM_EMAIL"

    def setUp(self):

        self.directory = TemporaryDirectory()

        self.path = Path(self.directory.name) / ".env"

        self.addCleanup(self.directory.cleanup)

        self.touched = []

        # Start from a known state even if a previous run leaked.
        for key in (
            self.HOST, self.PORT, self.USER, self.SECRET, self.SENDER
        ):
            os.environ.pop(key, None)

    def tearDown(self):

        for key in self.touched:
            os.environ.pop(key, None)

    def write(self, text):

        self.path.write_text(text, encoding="utf-8")

    def load(self, *keys):

        self.touched.extend(keys)

        _load_env_file(self.path)

    def test_a_plain_setting_is_read(self):

        self.write(f"{self.HOST}=smtp.gmail.com\n")

        self.load(self.HOST)

        self.assertEqual(os.environ[self.HOST], "smtp.gmail.com")

    def test_comments_and_blank_lines_are_ignored(self):

        self.write(
            f"# {self.HOST}=commented.example.com\n"
            "\n"
            "   \n"
            f"{self.PORT}=587\n"
        )

        self.load(self.HOST, self.PORT)

        self.assertNotIn(self.HOST, os.environ)

        self.assertEqual(os.environ[self.PORT], "587")

    def test_surrounding_quotes_are_stripped(self):
        """
        DEFAULT_FROM_EMAIL is the one people quote, because it
        contains a space and angle brackets.
        """

        self.write(
            f'{self.SENDER}="AUCA Workload <no-reply@auca.ac.rw>"\n'
        )

        self.load(self.SENDER)

        self.assertEqual(
            os.environ[self.SENDER],
            "AUCA Workload <no-reply@auca.ac.rw>",
        )

    def test_a_pasted_export_prefix_is_tolerated(self):
        """The setup notes are written as shell `export` lines."""

        self.write(f"export {self.USER}=workload@auca.ac.rw\n")

        self.load(self.USER)

        self.assertEqual(
            os.environ[self.USER],
            "workload@auca.ac.rw",
        )

    def test_a_real_environment_variable_wins(self):
        """
        The server's own configuration must not be overridden by
        a stray .env left in the checkout.
        """

        os.environ[self.HOST] = "real.example.com"

        self.touched.append(self.HOST)

        self.write(f"{self.HOST}=file.example.com\n")

        _load_env_file(self.path)

        self.assertEqual(
            os.environ[self.HOST],
            "real.example.com",
        )

    def test_a_password_containing_equals_survives(self):
        """App passwords are generated, and may contain '='."""

        self.write(f"{self.SECRET}=ab=cd=ef\n")

        self.load(self.SECRET)

        self.assertEqual(
            os.environ[self.SECRET],
            "ab=cd=ef",
        )

    def test_a_missing_file_is_not_an_error(self):
        """No .env is the normal case for a fresh checkout."""

        missing = Path(self.directory.name) / "nothing-here"

        _load_env_file(missing)

    def test_a_line_without_an_equals_is_skipped(self):

        self.write(f"this is not a setting\n{self.PORT}=25\n")

        self.load(self.PORT)

        self.assertEqual(os.environ[self.PORT], "25")
