# Set account passwords. Hashes are one-way, so an existing
# password cannot be read back -- only replaced.


import secrets
import string

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


# Ambiguous characters left out: someone reads these off a
# screen and types them into a login form.
ALPHABET = (
    "".join(c for c in string.ascii_letters if c not in "lIO")
    + "".join(c for c in string.digits if c not in "01")
)


def make_password(length=12):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


class Command(BaseCommand):

    help = (
        "Set passwords for user accounts. Existing passwords "
        "cannot be read back, only replaced."
    )

    def add_arguments(self, parser):

        target = parser.add_mutually_exclusive_group(required=True)

        target.add_argument(
            "--user",
            action="append",
            dest="users",
            help="Username. Repeat for several."
        )

        target.add_argument(
            "--blank-only",
            action="store_true",
            help=(
                "Every account that has no usable password, "
                "i.e. cannot currently be signed into."
            )
        )

        target.add_argument(
            "--all",
            action="store_true",
            help="Every account. Replaces working passwords too."
        )

        parser.add_argument(
            "--password",
            help=(
                "Use this password for every account listed. "
                "Omit it to generate a different random one "
                "for each, which is safer."
            )
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Required with --all when DEBUG is off. Setting "
                "every password at once on a live system locks "
                "out everyone who is using it."
            )
        )

    # ------------------------------------------------------

    def handle(self, *args, **options):

        password = options.get("password")

        if password:

            try:
                validate_password(password)

            except ValidationError as error:

                raise CommandError(
                    "That password was rejected:\n  "
                    + "\n  ".join(error.messages)
                )

        # ---- Choose the accounts ----

        if options["users"]:

            accounts = list(
                User.objects.filter(username__in=options["users"])
            )

            found = {user.username for user in accounts}

            missing = set(options["users"]) - found

            if missing:
                raise CommandError(
                    "No such account: " + ", ".join(sorted(missing))
                )

        elif options["blank_only"]:

            accounts = [
                user for user in User.objects.order_by("username")
                if not user.has_usable_password()
            ]

            if not accounts:

                self.stdout.write(self.style.SUCCESS(
                    "Every account already has a usable password."
                ))

                return

        else:

            if not settings.DEBUG and not options["force"]:

                raise CommandError(
                    "Refusing to reset every password on a system "
                    "with DEBUG off, because it signs out everyone "
                    "currently using it. Pass --force if that is "
                    "really what you want."
                )

            accounts = list(User.objects.order_by("username"))

        # ---- Set them ----

        results = []

        for user in accounts:

            issued = password or make_password()

            user.set_password(issued)

            user.save(update_fields=["password"])

            results.append((user, issued))

        # ---- Report ----

        self.stdout.write("")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Passwords set ({len(results)})"
        ))

        self.stdout.write("")

        self.stdout.write(
            f"  {'USERNAME':<22}{'ROLE':<16}"
            f"{'PASSWORD':<16}{'EMAIL'}"
        )

        self.stdout.write("  " + "-" * 84)

        for user, issued in results:

            self.stdout.write(
                f"  {user.username:<22}{user.role:<16}"
                f"{issued:<16}{user.email or '(none)'}"
            )

        self.stdout.write("")

        self.stdout.write(self.style.WARNING(
            "This list is the only copy. Passwords are stored as\n"
            "one-way hashes, so nothing can print them again."
        ))

        blank = [u for u, _ in results if not u.email]

        if blank:

            self.stdout.write("")

            self.stdout.write(self.style.WARNING(
                f"{len(blank)} of these accounts have no email "
                f"address, so they cannot be sent workload\n"
                f"notifications. Set one on the Users screen:"
            ))

            for user in blank:
                self.stdout.write(f"  - {user.username}")

        self.stdout.write("")
