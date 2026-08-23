# ==========================================================
# BACKFILL ACCOUNT ASSIGNMENTS
# ==========================================================
#
# The system links people to their records two ways:
#
#   academics.Lecturer.user            <-> accounts.LecturerAccountAssignment
#   academics.Cohort.representative    <-> accounts.RepresentativeAccountAssignment
#
# Lecturers linked before the Lecturer Accounts screen existed
# only ever had the first of these written. The screen reads the
# second, so it showed "No lecturer assignments available" even
# though every lecturer had a working login -- and an
# administrator trying to fix that by adding the assignment by
# hand hit a UNIQUE constraint error, because the record's user
# column was already taken.
#
# This creates the missing rows from the links that already
# exist. It writes nothing where an assignment is already
# present, so it is safe on a database that has both.
# ==========================================================
from django.db import migrations


def backfill(apps, schema_editor):

    Lecturer = apps.get_model("academics", "Lecturer")
    Cohort = apps.get_model("academics", "Cohort")

    LecturerAccountAssignment = apps.get_model(
        "accounts",
        "LecturerAccountAssignment"
    )

    RepresentativeAccountAssignment = apps.get_model(
        "accounts",
        "RepresentativeAccountAssignment"
    )

    linked_users = set(
        LecturerAccountAssignment.objects.values_list(
            "user_id",
            flat=True
        )
    )

    linked_lecturers = set(
        LecturerAccountAssignment.objects.values_list(
            "lecturer_id",
            flat=True
        )
    )

    for lecturer in Lecturer.objects.exclude(user__isnull=True):

        if lecturer.pk in linked_lecturers:
            continue

        if lecturer.user_id in linked_users:
            continue

        LecturerAccountAssignment.objects.create(
            user_id=lecturer.user_id,
            lecturer_id=lecturer.pk
        )

        linked_users.add(lecturer.user_id)
        linked_lecturers.add(lecturer.pk)

    linked_reps = set(
        RepresentativeAccountAssignment.objects.values_list(
            "user_id",
            flat=True
        )
    )

    linked_cohorts = set(
        RepresentativeAccountAssignment.objects.values_list(
            "cohort_id",
            flat=True
        )
    )

    for cohort in Cohort.objects.exclude(representative__isnull=True):

        if cohort.pk in linked_cohorts:
            continue

        if cohort.representative_id in linked_reps:
            continue

        RepresentativeAccountAssignment.objects.create(
            user_id=cohort.representative_id,
            cohort_id=cohort.pk
        )

        linked_reps.add(cohort.representative_id)
        linked_cohorts.add(cohort.pk)


def unbackfill(apps, schema_editor):
    """
    Deliberately a no-op.

    Reversing would have to guess which assignment rows this
    migration created and which an administrator added through the
    screens, and deleting the wrong ones would unlink working
    accounts. Leaving the rows in place is harmless: they mirror
    links that already exist.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_lectureraccountassignment_and_more"),
        ("academics", "0004_alter_lecturer_user"),
    ]

    operations = [
        migrations.RunPython(
            backfill,
            unbackfill
        ),
    ]
