# ==========================================================
# AUCA WORKLOAD MANAGEMENT SYSTEM
# WORKLOAD TESTS
# ==========================================================

import datetime

from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    User,
)

from academics.models import (
    Faculty, Program, Cohort, AcademicPeriod,
    Lecturer, Course, Holiday,
)

from workload.models import Workload
from workload.utils import generate_course_schedule, notional_hours_for


class BaseData(TestCase):

    def setUp(self):

        self.faculty = Faculty.objects.create(name="Information Technology")

        self.program = Program.objects.create(
            faculty=self.faculty,
            name="MSc Big Data Analytics",
        )

        self.period = AcademicPeriod.objects.create(
            academic_year="2026/2027",
            semester="Semester 1",
            teaching_period="May 2026 - September 2026",
            start_date=datetime.date(2026, 5, 10),
            end_date=datetime.date(2026, 9, 26),
        )

        self.course3 = Course.objects.create(
            program=self.program, code="MSDA 9114",
            name="Python for Data Science", credits=3, level="MSC",
        )

        self.course4 = Course.objects.create(
            program=self.program, code="MSDA 9115",
            name="Machine Learning", credits=4, level="MSC",
        )

        self.lecturer_user = User.objects.create_user(
            username="kumar", password="pw", role="lecturer",
        )
        self.lecturer = Lecturer.objects.create(
            user=self.lecturer_user, name="Kumar Kundan",
            qualification="PhD", employment_status="Contractual",
        )

        self.other_lecturer = Lecturer.objects.create(
            name="Jason Sebagenzi", qualification="PhD",
            employment_status="Regular",
        )

        self.rep_user = User.objects.create_user(
            username="jimmy", password="pw", role="representative",
        )
        self.cohort = Cohort.objects.create(
            program=self.program, name="Cohort 5",
            intake_year=2024, representative=self.rep_user,
        )

        self.other_cohort = Cohort.objects.create(
            program=self.program, name="Cohort 6", intake_year=2025,
        )

        # Administrator with role="admin" but NOT a superuser,
        # which is how the user management screens create them.
        self.admin_user = User.objects.create_user(
            username="dismas", password="pw", role="admin",
        )

    def make_workload(self, **kw):
        defaults = dict(
            cohort=self.cohort, academic_period=self.period,
            lecturer=self.lecturer, course=self.course3,
            start_date=datetime.date(2026, 5, 10),
            course_days="Sunday,Thursday",
        )
        defaults.update(kw)
        return Workload.objects.create(**defaults)


# ==========================================================
# SCHEDULE GENERATION
# ==========================================================

class ScheduleTests(BaseData):

    def test_three_credit_course_runs_four_weeks_of_two_days(self):
        schedule = generate_course_schedule(
            datetime.date(2026, 5, 10), 3, "Sunday,Thursday")
        self.assertEqual(len(schedule), 8)

    def test_four_credit_course_runs_five_weeks(self):
        schedule = generate_course_schedule(
            datetime.date(2026, 5, 10), 4, "Sunday,Thursday")
        self.assertEqual(len(schedule), 10)

    def test_public_holiday_is_skipped_and_block_extends(self):
        # Easter Monday 2026 falls on 6 April.
        schedule = generate_course_schedule(
            datetime.date(2026, 3, 29), 3, "Sunday,Monday")

        self.assertNotIn(datetime.date(2026, 4, 6), schedule)
        self.assertEqual(len(schedule), 8)

    def test_administrator_entered_holiday_is_skipped(self):
        Holiday.objects.create(
            date=datetime.date(2026, 5, 17), name="Founders Day")

        schedule = generate_course_schedule(
            datetime.date(2026, 5, 10), 3, "Sunday,Thursday")

        self.assertNotIn(datetime.date(2026, 5, 17), schedule)
        self.assertEqual(len(schedule), 8)

    def test_day_names_are_case_insensitive(self):
        # The source spreadsheet contains "SUNDAY".
        self.assertEqual(
            generate_course_schedule(datetime.date(2026, 5, 10), 3, "SUNDAY, thursday"),
            generate_course_schedule(datetime.date(2026, 5, 10), 3, "Sunday,Thursday"),
        )

    def test_unknown_credit_value_does_not_raise(self):
        # Previously raised ValueError and returned a 500.
        schedule = generate_course_schedule(
            datetime.date(2026, 5, 10), 2, "Sunday")
        self.assertEqual(len(schedule), 4)

    def test_invalid_day_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            generate_course_schedule(
                datetime.date(2026, 5, 10), 3, "Thusday")


# ==========================================================
# MODEL
# ==========================================================

class WorkloadModelTests(BaseData):

    def test_hours_are_credit_hours_not_session_count(self):
        w3 = self.make_workload(course=self.course3)
        w4 = self.make_workload(course=self.course4, cohort=self.other_cohort)

        self.assertEqual(w3.hours, 45)
        self.assertEqual(w4.hours, 60)
        self.assertEqual(w3.total_classes(), 8)

    def test_notional_hours_helper(self):
        self.assertEqual(notional_hours_for(3), 45)
        self.assertEqual(notional_hours_for(4), 60)

    def test_end_date_is_last_teaching_day(self):
        w = self.make_workload()
        self.assertEqual(str(w.end_date), w.generated_schedule[-1])

    def test_status_reflects_dates(self):
        today = datetime.date.today()

        past = self.make_workload(start_date=today - datetime.timedelta(days=120))
        future = self.make_workload(
            start_date=today + datetime.timedelta(days=60),
            cohort=self.other_cohort)

        self.assertEqual(past.status, "Done")
        self.assertEqual(future.status, "Upcoming")

    def test_refresh_statuses_corrects_stale_rows(self):
        w = self.make_workload(
            start_date=datetime.date.today() - datetime.timedelta(days=120))

        # Force a stale value the way the passage of time would.
        Workload.objects.filter(pk=w.pk).update(status="Upcoming")

        corrected = Workload.objects.all().refresh_statuses()
        w.refresh_from_db()

        self.assertEqual(corrected, 1)
        self.assertEqual(w.status, "Done")


# ==========================================================
# LECTURER ACCESS
# ==========================================================

class LecturerAccessTests(BaseData):

    def setUp(self):
        super().setUp()
        self.mine = self.make_workload()
        self.theirs = self.make_workload(
            lecturer=self.other_lecturer, course=self.course4)

    def test_dashboard_shows_only_own_workload(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:lecturer_dashboard"))

        self.assertEqual(r.status_code, 200)
        ids = {w.pk for w in r.context["workloads"]}
        self.assertEqual(ids, {self.mine.pk})
        self.assertEqual(r.context["total_workloads"], 1)

    def test_calendar_shows_only_own_workload(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:lecturer_calendar"))

        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["is_admin"])
        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.mine.pk})

    def test_lecturer_linked_on_their_record_sees_their_workload(self):
        """
        Lecturer.user is now the only linkage path. It is set by
        the Add / Edit Lecturer screen, and the dashboard must
        resolve from it alone.
        """
        user = User.objects.create_user(
            username="jason", password="pw", role="lecturer")
        self.other_lecturer.user = user
        self.other_lecturer.save()

        self.client.force_login(user)
        r = self.client.get(reverse("workload:lecturer_dashboard"))

        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.theirs.pk})

    def test_unlinked_lecturer_gets_empty_dashboard_not_an_error(self):
        user = User.objects.create_user(
            username="ghost", password="pw", role="lecturer")

        self.client.force_login(user)
        r = self.client.get(reverse("workload:lecturer_dashboard"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total_workloads"], 0)

    def test_representative_cannot_open_lecturer_dashboard(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:lecturer_dashboard"))
        self.assertEqual(r.status_code, 302)


# ==========================================================
# REPRESENTATIVE ACCESS
# ==========================================================

class RepresentativeAccessTests(BaseData):

    def setUp(self):
        super().setUp()
        self.ours = self.make_workload()
        self.theirs = self.make_workload(
            cohort=self.other_cohort, course=self.course4)

    def test_dashboard_shows_only_own_cohort(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:representative_dashboard"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["cohort"], self.cohort)
        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.ours.pk})

    def test_calendar_shows_only_own_cohort(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:representative_calendar"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.ours.pk})
        self.assertEqual(r.context["schedule_count"], 1)

    def test_representative_linked_on_the_cohort_sees_its_calendar(self):
        """
        Cohort.representative is now the only linkage path, set
        by the Add / Edit Cohort screen.
        """
        user = User.objects.create_user(
            username="ericb", password="pw", role="representative")
        self.other_cohort.representative = user
        self.other_cohort.save()

        self.client.force_login(user)
        r = self.client.get(reverse("workload:representative_calendar"))

        self.assertEqual(r.context["cohort"], self.other_cohort)
        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.theirs.pk})

    def test_lecturer_cannot_open_representative_calendar(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:representative_calendar"))
        self.assertEqual(r.status_code, 302)


# ==========================================================
# ADMINISTRATOR ACCESS
# ==========================================================

class AdminAccessTests(BaseData):

    def setUp(self):
        super().setUp()
        self.a = self.make_workload()
        self.b = self.make_workload(
            cohort=self.other_cohort, lecturer=self.other_lecturer,
            course=self.course4)

    def test_non_superuser_admin_sees_every_workload(self):
        # Regression: the calendar used to branch on is_superuser
        # alone, so a role="admin" user saw an empty calendar.
        self.assertFalse(self.admin_user.is_superuser)

        self.client.force_login(self.admin_user)
        r = self.client.get(reverse("workload:master_calendar"))

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_admin"])
        self.assertEqual({w.pk for w in r.context["workloads"]},
                         {self.a.pk, self.b.pk})

    def test_shared_calendar_link_routes_admin_to_master_view(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(reverse("workload:lecturer_calendar"))

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_admin"])

    def test_lecturer_cannot_open_master_calendar(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:master_calendar"))
        self.assertEqual(r.status_code, 302)

    def test_crud_pages_render(self):
        # Regression: these templates used un-namespaced {% url %}
        # tags and raised NoReverseMatch.
        self.client.force_login(self.admin_user)

        for name, args in [
            ("workload:assignment", []),
            ("workload:workload_list", []),
            ("workload:workload_detail", [self.a.pk]),
            ("workload:workload_update", [self.a.pk]),
            ("workload:workload_delete", [self.a.pk]),
        ]:
            with self.subTest(url=name):
                r = self.client.get(reverse(name, args=args))
                self.assertEqual(r.status_code, 200)


# ==========================================================
# PRINTING AND EXPORT
# ==========================================================

class PrintTests(BaseData):

    def setUp(self):
        super().setUp()

        self.period2 = AcademicPeriod.objects.create(
            academic_year="2026/2027",
            semester="Semester 2",
            teaching_period="September 2026 - February 2027",
            start_date=datetime.date(2026, 9, 27),
            end_date=datetime.date(2027, 2, 13),
        )

        # Mine, in two different periods.
        self.mine_p1 = self.make_workload()
        self.mine_p2 = self.make_workload(
            academic_period=self.period2, course=self.course4,
            start_date=datetime.date(2026, 9, 27))

        # Somebody else's, same periods.
        self.theirs = self.make_workload(
            lecturer=self.other_lecturer, cohort=self.other_cohort,
            course=self.course4)

    # ---------- lecturer ----------

    def test_lecturer_print_shows_only_own_workload(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:lecturer_workload_print"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual({w.pk for w in r.context["workloads"]},
                         {self.mine_p1.pk, self.mine_p2.pk})

    def test_lecturer_print_filters_by_period(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(
            reverse("workload:lecturer_workload_print"),
            {"period": self.period2.pk})

        self.assertEqual(r.context["selected_period"], self.period2)
        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.mine_p2.pk})

    def test_lecturer_print_totals_are_credit_hours(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(
            reverse("workload:lecturer_workload_print"),
            {"period": self.period.pk})

        # One 3-credit module = 45 hours over 8 sittings.
        self.assertEqual(r.context["total_hours"], 45)
        self.assertEqual(r.context["total_sessions"], 8)

    def test_period_dropdown_only_offers_own_periods(self):
        lonely = AcademicPeriod.objects.create(
            academic_year="2030/2031", semester="Semester 1",
            teaching_period="unused", start_date=datetime.date(2030, 1, 1),
            end_date=datetime.date(2030, 6, 1))

        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:lecturer_workload_print"))

        self.assertNotIn(lonely, list(r.context["periods"]))

    def test_bogus_period_cannot_widen_scope(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(
            reverse("workload:lecturer_workload_print"), {"period": "999999"})

        self.assertIsNone(r.context["selected_period"])
        self.assertNotIn(self.theirs.pk, {w.pk for w in r.context["workloads"]})

    def test_representative_cannot_print_lecturer_workload(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:lecturer_workload_print"))
        self.assertEqual(r.status_code, 302)

    # ---------- representative ----------

    def test_representative_print_shows_only_own_cohort(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:representative_calendar_print"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["cohort"], self.cohort)
        self.assertEqual({w.pk for w in r.context["workloads"]},
                         {self.mine_p1.pk, self.mine_p2.pk})

    def test_representative_print_filters_by_period(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(
            reverse("workload:representative_calendar_print"),
            {"period": self.period.pk})

        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.mine_p1.pk})

    def test_cohort_calendar_lists_holidays_in_span(self):
        self.client.force_login(self.rep_user)
        r = self.client.get(reverse("workload:representative_calendar_print"))

        dates = {h["date"] for h in r.context["holidays"]}
        # Umuganura 2026 falls on 7 August, inside the May-Feb span.
        self.assertIn(datetime.date(2026, 8, 7), dates)

    def test_lecturer_cannot_print_cohort_calendar(self):
        self.client.force_login(self.lecturer_user)
        r = self.client.get(reverse("workload:representative_calendar_print"))
        self.assertEqual(r.status_code, 302)


# ==========================================================
# ADMIN REPORTING
# ==========================================================

class AdminReportTests(BaseData):

    def setUp(self):
        super().setUp()
        self.a = self.make_workload()
        self.b = self.make_workload(
            lecturer=self.other_lecturer, cohort=self.other_cohort,
            course=self.course4)

    def test_report_page_renders_for_non_superuser_admin(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(reverse("reports:workload_report"))

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["workload_count"], 2)
        self.assertEqual(r.context["total_hours"], 105)   # 45 + 60

    def test_report_filters_by_lecturer(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(
            reverse("reports:workload_report"),
            {"lecturer": self.lecturer.pk})

        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.a.pk})
        self.assertIn(("Lecturer", str(self.lecturer)), r.context["applied"])

    def test_report_filters_by_cohort_and_status(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(
            reverse("reports:workload_report"),
            {"cohort": self.other_cohort.pk, "status": self.b.status})

        self.assertEqual({w.pk for w in r.context["workloads"]}, {self.b.pk})

    def test_printable_report_renders_and_states_criteria(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(
            reverse("reports:workload_report_print"),
            {"cohort": self.cohort.pk})

        self.assertEqual(r.status_code, 200)
        self.assertIn(("Cohort", str(self.cohort)), r.context["applied"])
        self.assertEqual(r.context["total_hours"], 45)

    def test_csv_export_respects_filters(self):
        self.client.force_login(self.admin_user)
        r = self.client.get(
            reverse("reports:workload_report_csv"),
            {"lecturer": self.other_lecturer.pk})

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", r["Content-Disposition"])

        rows = r.content.decode().strip().splitlines()
        self.assertEqual(len(rows), 2)               # header + one row
        self.assertIn("Machine Learning", rows[1])
        self.assertNotIn("Python for Data Science", rows[1])

    def test_lecturer_cannot_reach_admin_report(self):
        self.client.force_login(self.lecturer_user)

        for name in ["reports:workload_report",
                     "reports:workload_report_print",
                     "reports:workload_report_csv"]:
            with self.subTest(url=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 302)
