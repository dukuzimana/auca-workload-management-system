# Tests: teaching days column and visible action buttons.


import re

from datetime import date

from django.test import TestCase
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

from workload.models import Workload


class DaysColumnFixture(TestCase):

    def setUp(self):

        self.admin = User.objects.create_superuser(
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
            teaching_period="Sep - Dec",
            start_date=date(2026, 9, 7),
            end_date=date(2026, 12, 18),
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

        # The two modules that caused this.
        self.thesis = Course.objects.create(
            program=self.program,
            code="MSDA9222",
            name="Thesis",
            credits=6,
            level="MSC",
        )

        self.thesis_workload = Workload.objects.create(
            cohort=self.cohort,
            academic_period=self.period,
            lecturer=self.lecturer,
            course=self.thesis,
            start_date=date(2026, 9, 7),
            course_days="Monday,Tuesday,Wednesday,Thursday,Friday",
            duration_weeks=12,
        )


# ==========================================================
# THE MODEL HELPER
# ==========================================================

class TeachingDaysTests(DaysColumnFixture):

    def test_a_five_day_module_becomes_five_separate_days(self):
        """
        One 40-character word becomes five short ones, each of
        which the browser can place on its own line.
        """

        self.assertEqual(
            self.thesis_workload.teaching_days(),
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        )

    def test_days_come_back_in_calendar_order(self):
        """
        "Thursday,Sunday" and "Sunday,Thursday" are the same
        teaching pattern and must read identically on screen.
        """

        self.thesis_workload.course_days = "Sunday,Thursday"

        self.assertEqual(
            self.thesis_workload.teaching_days(),
            ["Thursday", "Sunday"],
        )

    def test_a_duplicate_day_is_not_shown_twice(self):

        self.thesis_workload.course_days = "Monday,Monday"

        self.assertEqual(
            self.thesis_workload.teaching_days(),
            ["Monday"],
        )

    def test_spacing_and_casing_are_tolerated(self):

        self.thesis_workload.course_days = " monday ,  FRIDAY "

        self.assertEqual(
            self.thesis_workload.teaching_days(),
            ["Monday", "Friday"],
        )

    def test_no_days_gives_an_empty_list_not_a_crash(self):

        self.thesis_workload.course_days = ""

        self.assertEqual(self.thesis_workload.teaching_days(), [])

    def test_an_unrecognised_day_does_not_break_the_page(self):
        """
        A bad day name is a data problem. The row still has to
        render, showing what was typed, so whoever can fix it
        can see it.
        """

        self.thesis_workload.course_days = "Monday,Funday"

        self.assertEqual(
            self.thesis_workload.teaching_days(),
            ["Monday", "Funday"],
        )


# ==========================================================
# THE RENDERED PAGE
# ==========================================================

class WorkloadPageRenderingTests(DaysColumnFixture):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.html = self.client.get(
            reverse("workload:assignment")
        ).content.decode()

    def test_the_unbreakable_string_is_no_longer_on_the_page(self):
        """
        The actual regression guard. If anyone puts
        {{ workload.course_days }} back in the table, this
        fails.
        """

        self.assertNotIn(
            "Monday,Tuesday,Wednesday,Thursday,Friday",
            self.html,
        )

    def test_each_day_is_its_own_element(self):
        """
        Separate elements are what give the browser somewhere
        to wrap. One string in one cell has no break point.
        """

        cells = re.findall(
            r'<td class="col-days">.*?</td>',
            self.html,
            re.S,
        )

        self.assertTrue(cells)

        thesis_cell = next(
            cell for cell in cells if "Fri" in cell
        )

        self.assertEqual(
            thesis_cell.count('class="day-chip"'),
            5,
        )

    def test_the_full_day_name_is_kept_as_a_tooltip(self):
        """
        The column shows "Mon"; hovering must still say
        "Monday", so shortening costs no information.
        """

        self.assertIn('title="Wednesday"', self.html)

    def test_no_remaining_run_is_long_enough_to_widen_the_column(self):
        """
        The point of the whole change, measured rather than
        assumed: nothing in a days cell is an unbreakable run
        longer than a three-letter abbreviation.
        """

        cells = re.findall(
            r'<td class="col-days">(.*?)</td>',
            self.html,
            re.S,
        )

        for cell in cells:

            for text in re.findall(r'>([^<>]+)<', cell):

                for token in text.split():

                    self.assertLessEqual(
                        len(token),
                        3,
                        f"{token!r} is long enough to widen the column",
                    )

    def test_the_action_buttons_are_present_on_every_row(self):

        self.assertIn(
            reverse(
                "workload:workload_detail",
                args=[self.thesis_workload.id],
            ),
            self.html,
        )

        self.assertIn(
            reverse(
                "workload:workload_update",
                args=[self.thesis_workload.id],
            ),
            self.html,
        )

        self.assertIn(
            reverse(
                "workload:workload_delete",
                args=[self.thesis_workload.id],
            ),
            self.html,
        )

    def test_the_actions_column_is_pinned(self):
        """
        Wrapping the days is enough on a normal laptop, but the
        table has ten columns and some screen will always be
        narrow enough. The pinned column is what makes the
        buttons reachable at any width.
        """

        self.assertIn("table-sticky-actions", self.html)

    def test_a_row_with_no_days_shows_a_dash(self):
        """
        An empty cell looks like the page failed to load.
        """

        self.thesis_workload.course_days = ""

        self.thesis_workload.save()

        html = self.client.get(
            reverse("workload:assignment")
        ).content.decode()

        self.assertIn("day-chip-missing", html)


# ==========================================================
# THE SAME COLUMN ELSEWHERE
# ==========================================================

class CalendarPagesTests(DaysColumnFixture):
    """
    The lecturer's and representative's own schedule screens
    print the same field and had the same unbreakable string
    setting their table width.
    """

    def test_lecturer_calendar_uses_day_chips(self):

        self.client.force_login(self.lecturer_user)

        html = self.client.get(
            reverse("workload:lecturer_calendar")
        ).content.decode()

        self.assertNotIn(
            "Monday,Tuesday,Wednesday,Thursday,Friday",
            html,
        )

        self.assertIn("day-chip", html)

    def test_representative_calendar_uses_day_chips(self):

        self.client.force_login(self.rep_user)

        html = self.client.get(
            reverse("workload:representative_calendar")
        ).content.decode()

        self.assertNotIn(
            "Monday,Tuesday,Wednesday,Thursday,Friday",
            html,
        )

        self.assertIn("day-chip", html)


# ==========================================================
# THE STYLESHEET
# ==========================================================

class StylesheetTests(TestCase):
    """
    The markup change only works with the rules that cap the
    column and pin the last one. Losing them silently restores
    the original fault.
    """

    def setUp(self):

        from django.conf import settings
        from pathlib import Path

        self.css = (
            Path(settings.BASE_DIR) / "static" / "css" / "style.css"
        ).read_text(encoding="utf-8")

    def test_the_days_column_is_capped_and_allowed_to_wrap(self):

        self.assertIn(".col-days", self.css)

        self.assertIn("max-width:130px", self.css)

    def test_the_chips_wrap_onto_the_next_line(self):

        self.assertIn(".day-chips", self.css)

        self.assertIn("flex-wrap:wrap", self.css)

    def test_the_pinned_column_is_opaque(self):
        """
        A transparent sticky cell lets the columns scrolling
        underneath show through the buttons.
        """

        block = self.css[self.css.index(".table-sticky-actions"):]

        self.assertIn("position:sticky", block)

        self.assertIn("background:#ffffff", block)
