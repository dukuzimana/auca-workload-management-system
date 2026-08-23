# Tests: the spreadsheet import, end to end.


import tempfile

from datetime import date, datetime
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from academics.models import (
    AcademicPeriod,
    Cohort,
    Course,
    Faculty,
    Lecturer,
    Program,
)

from accounts.models import User

from workload.models import Workload


HEADER = [
    None,
    "Period (2026-2028)",
    "Lecturer's Name",
    "Degree/specialisation(Qualification)",
    "Employment Status",
    "Course Code",
    "Course Name",
    "Credicts",
    "Level",
    "Course Day",
    "Number of hours",
    "Status",
]


def build_workbook(path):
    """A miniature version of the faculty spreadsheet."""

    from openpyxl import Workbook

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Cohort9"

    rows = [
        [None, "Faculty of Information Technology"],
        ["Masters of science in Big  Data Analytics third semester  "],
        [None, "Teaching Load 2026-2028"],
        [],
        [],
        [],
        [],
        [],
        HEADER,

        # An ordinary row, with the recurring misspelling.
        [
            1, "13/9/2026 - 11/10/2026", "Dr. Eric Nizeyimana",
            "Ph.D in Computer science", "Regular", "BDA91101",
            "Advanced Research methodology", 3, "MSC",
            "Sunday, Thusday", 45, "Upcoming",
        ],

        # A date Excel stored as a real date, not text.
        [
            2, datetime(2026, 10, 11), "Nizeyimana Pacifique",
            "Ph.D in Statistics", "Regular", "BDA91103",
            "R for Data science", 3, "MSC", "SUNDAY, Thusday",
            45, "Upcoming",
        ],

        # The same code as row 1, a different course.
        [
            3, "8/11/2026 - 13/12/2026", "Prof. Jason Sebagenzi",
            "Ph.D in Computer Science", "Regular", "BDA91101",
            "Advanced algorithm analysis", 3, "MSC",
            "Sunday,Thursday", 45, "Upcoming",
        ],

        # No code and no teaching days.
        [
            None, "14/2/2027 - 21/2/2027", "Mr. David Hagumuwumva",
            None, "Regular", None, "Mathematical Computing",
            None, None, None, None, None,
        ],

        [],

        HEADER,

        # Co-taught, and a term-long block stated explicitly.
        [
            "SEM IV", "5/3/2028 - 5/6/2028",
            "Dr. Eric Nizeyimana, Mr. david Hagumuwumva",
            "Ph.D in Computer science", "Regular", "BDA92214",
            "Internship", 60, None, "All days", None, "Upcoming",
        ],

        # A period that runs backwards.
        [
            None, "13/12/2026 - 13/3/2026", "Dr. Kumar Kundan",
            "Ph.D in Information Technology", "Contractual",
            "BDA92112", "Big data essentials", 3, "MSC",
            "Sunday", 45, "Upcoming",
        ],

        # No usable start date at all.
        [
            None, "../7/2026", "Prof. Goga Nicu",
            "Ph.D in Computer Science", "Visitor", "BDA91206",
            "Distributed Systems", 3, "MSC", "Sunday", 45,
            "Upcoming",
        ],
    ]

    for row in rows:
        sheet.append(row)

    lecturers = workbook.create_sheet("Lecturers ")

    lecturers.append(["BIG DATA ANALYTICS WORKLOAD"])

    lecturers.append(["SN", "Instructor", None, "Course"])

    lecturers.append([1, "Dr. Eric Nizeyimana", "Regular"])

    lecturers.append([2, "Dr. Pacifique Nizeyimana", "Regular"])

    workbook.save(path)


class ImportCommandTests(TestCase):

    @classmethod
    def setUpClass(cls):

        super().setUpClass()

        cls._directory = tempfile.TemporaryDirectory()

        cls.path = str(Path(cls._directory.name) / "load.xlsx")

        build_workbook(cls.path)

    @classmethod
    def tearDownClass(cls):

        cls._directory.cleanup()

        super().tearDownClass()

    def run_import(self, *args):

        out = StringIO()

        call_command(
            "import_workload_excel",
            self.path,
            *args,
            stdout=out,
            stderr=out,
        )

        return out.getvalue()

    # ------------------------------------------------------

    def test_the_structure_is_created(self):

        self.run_import()

        self.assertEqual(Faculty.objects.count(), 1)

        self.assertEqual(Program.objects.count(), 1)

        self.assertEqual(
            Cohort.objects.get().name,
            "Cohort 9",
        )

    def test_the_stray_semester_suffix_is_dropped(self):
        """
        The programme cell reads "...Analytics third semester".
        Keeping that would make a second programme that every
        one of those cohorts hangs off.
        """

        self.run_import()

        self.assertNotIn(
            "semester",
            Program.objects.get().name.lower(),
        )

    def test_both_date_formats_are_read(self):

        self.run_import()

        methodology = Workload.objects.get(
            course__name="Advanced Research methodology"
        )

        self.assertEqual(methodology.start_date, date(2026, 9, 13))

        r_course = Workload.objects.get(
            course__name="R for Data science"
        )

        self.assertEqual(r_course.start_date, date(2026, 10, 11))

    def test_the_misspelling_is_corrected(self):

        self.run_import()

        workload = Workload.objects.get(
            course__name="Advanced Research methodology"
        )

        self.assertEqual(workload.course_days, "Sunday,Thursday")

    def test_a_reused_code_does_not_merge_two_courses(self):
        """
        Two different courses share the code BDA91101. Course
        code is unique, so trusting it would silently collapse
        them into one.
        """

        self.run_import()

        names = set(
            Course.objects.values_list("name", flat=True)
        )

        self.assertIn("Advanced Research methodology", names)

        self.assertIn("Advanced algorithm analysis", names)

        self.assertEqual(
            Course.objects.filter(code="BDA91101").count(),
            1,
        )

    def test_the_clash_is_reported(self):

        output = self.run_import()

        self.assertIn("already used by a different course", output)

    def test_a_co_taught_module_names_both_people(self):

        self.run_import()

        internship = Workload.objects.get(course__name="Internship")

        self.assertEqual(
            internship.lecturer.name,
            "Dr. Eric Nizeyimana",
        )

        # The spreadsheet writes him "Mr. david Hagumuwumva"
        # here and "Mr. David Hagumuwumva" earlier. One record,
        # under the capitalisation seen first.
        self.assertEqual(
            [l.name for l in internship.co_lecturers.all()],
            ["Mr. David Hagumuwumva"],
        )

        self.assertEqual(
            Lecturer.objects.filter(
                name__icontains="hagumuwumva"
            ).count(),
            1,
        )

    def test_a_term_long_block_keeps_its_stated_span(self):

        self.run_import()

        internship = Workload.objects.get(course__name="Internship")

        self.assertEqual(internship.duration_weeks, 13)

        # Thirteen weeks of the working week, Monday to Friday.
        self.assertEqual(
            internship.course_days,
            "Monday,Tuesday,Wednesday,Thursday,Friday",
        )

        self.assertEqual(internship.total_classes(), 65)

    def test_hours_in_the_credits_column_are_converted(self):
        """
        Internship shows 60 with the hours column blank. Stored
        as 60 credits it would record 900 teaching hours.
        """

        self.run_import()

        internship = Workload.objects.get(course__name="Internship")

        self.assertEqual(internship.course.credits, 4)

        self.assertEqual(internship.hours, 60)

    def test_that_conversion_is_reported(self):

        output = self.run_import()

        self.assertIn("Please confirm", output)

    def test_a_backwards_period_is_repaired(self):

        self.run_import()

        essentials = Workload.objects.get(
            course__name="Big data essentials"
        )

        self.assertEqual(essentials.start_date, date(2026, 12, 13))

    def test_a_row_with_no_start_date_is_skipped_and_reported(self):

        output = self.run_import()

        self.assertFalse(
            Workload.objects.filter(
                course__name="Distributed Systems"
            ).exists()
        )

        self.assertIn("not imported", output)

    def test_a_row_with_no_days_is_imported_as_pending(self):
        """
        Losing the row would hide an assignment that exists.
        Importing it without a schedule shows it as Pending,
        which is what it is.
        """

        self.run_import()

        maths = Workload.objects.get(
            course__name="Mathematical Computing"
        )

        self.assertEqual(maths.course_days, "")

        self.assertEqual(maths.status, "Pending")

    def test_periods_are_scoped_to_the_cohort(self):

        self.run_import()

        for period in AcademicPeriod.objects.all():

            self.assertIsNotNone(period.cohort_id)

    def test_running_twice_does_not_duplicate(self):

        self.run_import()

        first = {
            "workloads": Workload.objects.count(),
            "courses": Course.objects.count(),
            "lecturers": Lecturer.objects.count(),
            "cohorts": Cohort.objects.count(),
            "periods": AcademicPeriod.objects.count(),
        }

        self.run_import()

        second = {
            "workloads": Workload.objects.count(),
            "courses": Course.objects.count(),
            "lecturers": Lecturer.objects.count(),
            "cohorts": Cohort.objects.count(),
            "periods": AcademicPeriod.objects.count(),
        }

        self.assertEqual(first, second)

    def test_dry_run_writes_nothing(self):

        output = self.run_import("--dry-run")

        self.assertIn("DRY RUN", output)

        self.assertEqual(Workload.objects.count(), 0)

        self.assertEqual(Cohort.objects.count(), 0)

    def test_the_same_person_written_two_ways_is_one_record(self):
        """
        The lecturer sheet says "Dr. Pacifique Nizeyimana" and
        the cohort sheet says "Nizeyimana Pacifique".
        """

        self.run_import()

        matches = Lecturer.objects.filter(
            name__icontains="pacifique"
        )

        self.assertEqual(matches.count(), 1)

    def test_create_accounts_leaves_the_email_blank(self):
        """
        Inventing an address would let the system report a
        notification as sent while it goes nowhere.
        """

        output = self.run_import("--create-accounts")

        created = User.objects.filter(role="lecturer")

        self.assertTrue(created.exists())

        for user in created:

            self.assertEqual(user.email, "")

            self.assertFalse(user.has_usable_password())

        self.assertIn("without an email address", output)

    def test_every_cohort_gets_a_representative_account(self):

        self.run_import("--create-accounts")

        cohort = Cohort.objects.get()

        self.assertIsNotNone(cohort.representative)

        self.assertEqual(
            cohort.representative.role,
            "representative",
        )

    def test_accounts_are_not_created_without_the_flag(self):

        self.run_import()

        self.assertEqual(User.objects.count(), 0)
