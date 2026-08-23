# ==========================================================
# AUCA WORKLOAD MANAGEMENT SYSTEM
# BACKFILL BEFORE DROPPING THE ASSIGNMENT TABLES
# ==========================================================
#
# The next migration deletes LecturerAccountAssignment and
# RepresentativeAccountAssignment. Those tables were one of two
# ways a person could be linked to their record; the other is
# Lecturer.user and Cohort.representative, which the Add
# Lecturer and Add Cohort screens already fill in.
#
# On the database this was written against the two paths agreed
# everywhere -- all 16 lecturers and all 10 cohorts carried the
# link on their own record as well. But this migration will run
# on databases nobody has audited, and a lecturer linked ONLY
# through the assignment screen would otherwise lose their
# account the moment the table is dropped: no dashboard, and no
# notification email when a module is assigned to them.
#
# So the link is copied onto the record first. This runs before
# any table is deleted, and it only ever fills a gap -- an
# existing Lecturer.user is never overwritten, because that is
# the value the Add screen collected and the one a person most
# recently confirmed.
#
# Deliberately not reversible. Recreating the rows would mean
# guessing which links had originally come from the assignment
# table and which had always been on the record, and guessing
# wrong would resurrect links an administrator had removed.
# ==========================================================


from django.db import migrations


def backfill(apps, schema_editor):

    LecturerAccountAssignment = apps.get_model(
        "accounts",
        "LecturerAccountAssignment",
    )

    RepresentativeAccountAssignment = apps.get_model(
        "accounts",
        "RepresentativeAccountAssignment",
    )

    Lecturer = apps.get_model("academics", "Lecturer")

    Cohort = apps.get_model("academics", "Cohort")

    # ---- Lecturers ----

    for assignment in LecturerAccountAssignment.objects.select_related(
        "lecturer"
    ):

        lecturer = assignment.lecturer

        if lecturer.user_id:
            # Already linked on the record. Leave it: this is
            # what the Add / Edit Lecturer screen collected.
            continue

        # Lecturer.user is one-to-one, so refuse to point two
        # lecturers at the same login rather than raising an
        # IntegrityError part-way through the migration.
        taken = Lecturer.objects.filter(
            user_id=assignment.user_id
        ).exclude(
            pk=lecturer.pk
        ).exists()

        if taken:
            continue

        lecturer.user_id = assignment.user_id

        lecturer.save(update_fields=["user"])

    # ---- Cohorts ----

    for assignment in RepresentativeAccountAssignment.objects.select_related(
        "cohort"
    ):

        cohort = assignment.cohort

        if cohort.representative_id:
            continue

        taken = Cohort.objects.filter(
            representative_id=assignment.user_id
        ).exclude(
            pk=cohort.pk
        ).exists()

        if taken:
            continue

        cohort.representative_id = assignment.user_id

        cohort.save(update_fields=["representative"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_backfill_account_assignments"),
        ("academics", "0005_alter_academicperiod_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill,
            migrations.RunPython.noop,
        ),
    ]
