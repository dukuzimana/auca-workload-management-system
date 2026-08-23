# Check the email set-up.
#   python manage.py check_email --to you@example.com


from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand

from academics.models import Cohort, Lecturer

from accounts.models import User

from workload.selectors import account_for_cohort, account_for_lecturer


CONSOLE = "django.core.mail.backends.console.EmailBackend"


class Command(BaseCommand):

    help = (
        "Report whether workload notification emails can "
        "actually be delivered, and optionally send a test."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--to",
            help=(
                "Send a test message to this address. Without "
                "it, the set-up is only reported on."
            )
        )

    # ------------------------------------------------------

    def handle(self, *args, **options):

        write = self.stdout.write

        backend = settings.EMAIL_BACKEND

        write("")
        write(self.style.MIGRATE_HEADING("1. Where mail is going"))
        write("")

        write(f"  EMAIL_BACKEND       {backend}")
        write(f"  EMAIL_HOST          {settings.EMAIL_HOST or '(not set)'}")
        write(f"  EMAIL_PORT          {settings.EMAIL_PORT}")
        write(f"  EMAIL_HOST_USER     {settings.EMAIL_HOST_USER or '(not set)'}")
        write(
            f"  EMAIL_HOST_PASSWORD "
            f"{'(set)' if settings.EMAIL_HOST_PASSWORD else '(not set)'}"
        )
        write(f"  EMAIL_USE_TLS       {settings.EMAIL_USE_TLS}")
        write(f"  DEFAULT_FROM_EMAIL  {settings.DEFAULT_FROM_EMAIL}")
        write(f"  SITE_URL            {settings.SITE_URL}")

        write("")

        deliverable = backend != CONSOLE

        if not deliverable:

            write(self.style.ERROR(
                "  Nothing is being delivered."
            ))

            write("")
            write(
                "  No EMAIL_HOST is set, so Django is printing\n"
                "  notifications to the terminal running the\n"
                "  server instead of sending them. The system\n"
                "  reports them as sent because, as far as it is\n"
                "  concerned, they were handed over successfully.\n"
            )
            write("  To send real mail, set these and restart:\n")
            write("      EMAIL_HOST=smtp.gmail.com")
            write("      EMAIL_PORT=587")
            write("      EMAIL_HOST_USER=workload@auca.ac.rw")
            write("      EMAIL_HOST_PASSWORD=your-app-password")
            write("      SITE_URL=https://workload.auca.ac.rw")
            write("")
            write(
                "  For Gmail the password must be an App Password\n"
                "  from https://myaccount.google.com/apppasswords --\n"
                "  the account's normal password is rejected.\n"
            )

        else:

            write(self.style.SUCCESS(
                "  A mail server is configured."
            ))

            write("")

            try:
                connection = get_connection()
                connection.open()
                connection.close()

                write(self.style.SUCCESS(
                    "  The server accepted the connection."
                ))

            except Exception as error:

                write(self.style.ERROR(
                    f"  The server refused the connection: {error}"
                ))

                write("")
                write(
                    "  Nothing will be delivered until this is\n"
                    "  resolved. Assignments will still save, and\n"
                    "  the failure is reported on screen each time."
                )

        # --------------------------------------------------

        write("")
        write(self.style.MIGRATE_HEADING(
            "2. Who can actually be reached"
        ))
        write("")

        unreachable_lecturers = []

        for lecturer in Lecturer.objects.all():

            account = account_for_lecturer(lecturer)

            if account is None:
                unreachable_lecturers.append(
                    (lecturer.name, "no account linked")
                )

            elif not account.email:
                unreachable_lecturers.append(
                    (lecturer.name, f"{account.username} has no email")
                )

        unreachable_cohorts = []

        for cohort in Cohort.objects.all():

            account = account_for_cohort(cohort)

            if account is None:
                unreachable_cohorts.append(
                    (cohort.name, "no representative linked")
                )

            elif not account.email:
                unreachable_cohorts.append(
                    (cohort.name, f"{account.username} has no email")
                )

        total_lecturers = Lecturer.objects.count()

        total_cohorts = Cohort.objects.count()

        write(
            f"  Lecturers reachable        "
            f"{total_lecturers - len(unreachable_lecturers)}"
            f" of {total_lecturers}"
        )

        write(
            f"  Class reps reachable       "
            f"{total_cohorts - len(unreachable_cohorts)}"
            f" of {total_cohorts}"
        )

        for label, rows in (
            ("Lecturers who cannot be emailed", unreachable_lecturers),
            ("Cohorts whose rep cannot be emailed", unreachable_cohorts),
        ):

            if not rows:
                continue

            write("")
            write(self.style.WARNING(f"  {label} ({len(rows)})"))

            for name, reason in rows:
                write(f"    - {name}: {reason}")

        if unreachable_lecturers or unreachable_cohorts:

            write("")
            write(
                "  Set the missing addresses on the Users screen,\n"
                "  or in bulk:\n"
                "      python manage.py set_emails --domain auca.ac.rw"
            )

        # --------------------------------------------------

        if options["to"]:

            write("")
            write(self.style.MIGRATE_HEADING("3. Test message"))
            write("")

            try:
                sent = send_mail(
                    subject="AUCA Workload System: test message",
                    message=(
                        "This is a test from the AUCA Workload "
                        "Management System.\n\n"
                        "If you are reading this in your inbox, "
                        "notification emails will be delivered.\n"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[options["to"]],
                    fail_silently=False,
                )

                if not deliverable:
                    write(self.style.WARNING(
                        "  Printed to the console above -- not "
                        "delivered, because no mail server is set."
                    ))

                elif sent:
                    write(self.style.SUCCESS(
                        f"  Accepted for delivery to {options['to']}."
                    ))

                else:
                    write(self.style.ERROR(
                        "  The server accepted nothing."
                    ))

            except Exception as error:

                write(self.style.ERROR(
                    f"  Failed: {error.__class__.__name__}: {error}"
                ))

        write("")
