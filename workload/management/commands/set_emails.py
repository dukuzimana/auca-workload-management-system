# Fill in missing email addresses.
#   python manage.py set_emails --domain auca.ac.rw --dry-run


import re

from django.core.management.base import BaseCommand, CommandError

from academics.models import Cohort, Lecturer

from accounts.models import User


def local_part(name):
    """
    Turn a person's name into the part before the @.

    Digits are kept. Dropping them collapsed every class
    representative to the same address -- "Cohort 9 rep" and
    "Cohort 14 rep" both became "cohort.rep" -- and the first
    one written would have received all ten cohorts' mail.
    """

    # Titles are not part of an address.
    words = [
        word for word in re.split(r"[^A-Za-z0-9]+", name.lower())
        if word and word not in {
            "dr", "prof", "mr", "mrs", "ms", "miss", "rev",
        }
    ]

    return ".".join(words) if words else ""


class Command(BaseCommand):

    help = (
        "Fill in email addresses for accounts that have none, "
        "so they can receive workload notifications."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--domain",
            help=(
                "Generate addresses for every account missing "
                "one, e.g. auca.ac.rw"
            )
        )

        parser.add_argument(
            "--user",
            help="Set one account's address. Use with --email."
        )

        parser.add_argument(
            "--email",
            help="The address to set. Use with --user."
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "Also replace addresses that are already set. "
                "Off by default, so a real address entered by "
                "hand is never overwritten by a guess."
            )
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change, write nothing."
        )

    # ------------------------------------------------------

    def handle(self, *args, **options):

        write = self.stdout.write

        # ---- One account ----

        if options["user"] or options["email"]:

            if not (options["user"] and options["email"]):
                raise CommandError(
                    "--user and --email must be given together."
                )

            try:
                user = User.objects.get(username=options["user"])

            except User.DoesNotExist:
                raise CommandError(
                    f"No account called '{options['user']}'."
                )

            before = user.email or "(blank)"

            if not options["dry_run"]:
                user.email = options["email"]
                user.save(update_fields=["email"])

            write("")
            write(self.style.SUCCESS(
                f"  {user.username}: {before} -> {options['email']}"
            ))
            write("")

            return

        # ---- In bulk ----

        domain = (options["domain"] or "").strip().lstrip("@")

        if not domain:
            raise CommandError(
                "Give --domain to generate addresses, or --user "
                "with --email to set a single one."
            )

        # Who each account belongs to, so the generated address
        # uses the person's name rather than the username.
        owner = {}

        for lecturer in Lecturer.objects.select_related("user"):
            if lecturer.user_id:
                owner[lecturer.user_id] = lecturer.name

        for cohort in Cohort.objects.select_related("representative"):
            if cohort.representative_id:
                owner[cohort.representative_id] = f"{cohort.name} rep"

        changes = []

        clashes = []

        taken = {
            email.lower()
            for email in User.objects.exclude(email="")
            .values_list("email", flat=True)
        }

        for user in User.objects.order_by("username"):

            if user.email and not options["overwrite"]:
                continue

            source = owner.get(user.pk, user.username)

            local = local_part(source) or local_part(user.username)

            if not local:
                continue

            address = f"{local}@{domain}"

            if address.lower() in taken and address.lower() != (user.email or "").lower():

                clashes.append((user.username, address))

                continue

            taken.add(address.lower())

            changes.append((user, user.email or "(blank)", address))

        # ---- Report ----

        write("")

        if not changes and not clashes:

            write(self.style.SUCCESS(
                "  Every account already has an email address."
            ))
            write("")

            return

        write(self.style.MIGRATE_HEADING(
            f"Addresses to set ({len(changes)})"
        ))
        write("")

        for user, before, after in changes:

            write(
                f"  {user.username:<22}{user.role:<16}"
                f"{before:<24} ->  {after}"
            )

        if clashes:

            write("")
            write(self.style.WARNING(
                f"Skipped -- the address is already in use ({len(clashes)})"
            ))

            for username, address in clashes:
                write(f"  {username:<22}{address}")

            write("")
            write(
                "  Set these by hand:\n"
                "      python manage.py set_emails --user NAME "
                "--email someone@example.com"
            )

        write("")

        if options["dry_run"]:

            write(self.style.WARNING(
                "  DRY RUN -- nothing was written."
            ))
            write("")

            return

        for user, _, address in changes:
            user.email = address
            user.save(update_fields=["email"])

        write(self.style.SUCCESS(
            f"  {len(changes)} addresses set."
        ))

        write("")
        write(self.style.WARNING(
            "  These are generated from names, not confirmed.\n"
            "  Check them against your real mail directory --\n"
            "  an address that does not exist will bounce, and\n"
            "  the person will never know they were assigned."
        ))
        write("")
