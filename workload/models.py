from django.db import models
from django.utils import timezone

from academics.models import Cohort, Lecturer, Course, AcademicPeriod

from .utils import (
    generate_course_schedule,
    notional_hours_for,
    excluded_holidays,
    parse_course_days,
    DAY_NAMES,
)


# ==================================================
# QUERYSET
# ==================================================

class WorkloadQuerySet(models.QuerySet):

    def refresh_statuses(self):
        """
        Bring the stored status column back in line with today's
        date.

        Status is derived from the start and end dates, but it is
        stored rather than computed so that the admin dashboard
        and reports can filter and aggregate on it. Stored values
        therefore go stale as time passes: a module that finished
        last month still reads "Upcoming" until something saves it
        again. Call this before any view that counts by status.

        Returns the number of rows corrected.
        """

        today = timezone.localdate()

        changed = []

        for workload in self:

            new_status = workload.compute_status(today)

            if workload.status != new_status:

                workload.status = new_status

                changed.append(workload)

        if changed:

            Workload.objects.bulk_update(
                changed,
                ["status"]
            )

        return len(changed)


# ==================================================
# WORKLOAD
# ==================================================

class Workload(models.Model):

    STATUS_CHOICES = [
        ("Upcoming", "Upcoming"),
        ("Ongoing", "Ongoing"),
        ("Pending", "Pending"),
        ("Done", "Done"),
    ]

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="workloads"
    )

    academic_period = models.ForeignKey(
        AcademicPeriod,
        on_delete=models.CASCADE,
        related_name="workloads"
    )

    # The lecturer who leads the module.
    lecturer = models.ForeignKey(
        Lecturer,
        on_delete=models.CASCADE,
        related_name="workloads"
    )

    # Co-teachers. The spreadsheet records them in one cell.
    co_lecturers = models.ManyToManyField(
        Lecturer,
        blank=True,
        related_name="co_workloads"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="workloads"
    )

    start_date = models.DateField()

    end_date = models.DateField(
        blank=True,
        null=True
    )

    hours = models.IntegerField(
        blank=True,
        null=True,
        editable=False,
        help_text="Notional teaching hours (credits x 15)."
    )

    course_days = models.CharField(
        max_length=100,
        help_text="Example: Monday,Thursday"
    )

    # Overrides the block length implied by the credits. Blank
    # keeps the default; Internship and Thesis run a whole term.
    duration_weeks = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=(
            "Leave blank to use the standard block length for "
            "the course's credit value."
        )
    )

    generated_schedule = models.JSONField(
        blank=True,
        null=True,
        editable=False
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        blank=True,
        editable=False
    )

    objects = WorkloadQuerySet.as_manager()

    class Meta:
        ordering = ["-id"]
        verbose_name = "Teaching Workload"
        verbose_name_plural = "Teaching Workloads"

    # ----------------------------------------------
    # STATUS
    # ----------------------------------------------

    def compute_status(self, today=None):
        """Status implied by the dates, without saving."""

        today = today or timezone.localdate()

        if not self.start_date:
            return "Pending"

        # Assigned, but no teaching days could be worked out.
        if not self.generated_schedule:
            return "Pending"

        if self.start_date > today:
            return "Upcoming"

        if self.end_date and today > self.end_date:
            return "Done"

        return "Ongoing"

    # ----------------------------------------------
    # SAVE
    # ----------------------------------------------

    def save(self, *args, **kwargs):

        # 1. Build the teaching schedule, skipping holidays.
        if self.course_id and self.start_date and self.course_days:

            schedule = generate_course_schedule(
                self.start_date,
                self.course.credits,
                self.course_days,
                weeks=self.duration_weeks
            )

            if schedule:
                self.end_date = schedule[-1]
                self.generated_schedule = [str(day) for day in schedule]
            else:
                self.end_date = None
                self.generated_schedule = []

            # Recorded hours are the official credit hours, not
            # the number of sittings. See utils.notional_hours_for.
            self.hours = notional_hours_for(self.course.credits)

        # 2. Derive the status from those dates.
        self.status = self.compute_status()

        super().save(*args, **kwargs)

    # ----------------------------------------------
    # HELPERS
    # ----------------------------------------------

    def total_classes(self):
        """Number of sittings actually scheduled."""

        return len(self.generated_schedule or [])

    def teaching_team(self):
        """
        Every lecturer on this module, lead first.

        Used by the notification emails and the printed sheets,
        which should name a co-teacher rather than silently
        showing only the lead.
        """

        team = [self.lecturer] if self.lecturer_id else []

        if self.pk:
            team += [
                lecturer
                for lecturer in self.co_lecturers.all()
                if lecturer.pk != self.lecturer_id
            ]

        return team

    def teaching_team_names(self):
        """The teaching team as one readable string."""

        return ", ".join(
            lecturer.name for lecturer in self.teaching_team()
        )

    def teaching_days(self):
        """
        The teaching days as a list, shortest useful form.

        course_days is stored as the spreadsheet writes it --
        "Monday,Tuesday,Wednesday,Thursday,Friday" -- with no
        space after the commas. That is a single 40-character
        word as far as a browser is concerned, and there is no
        legal place to break it, so the Days column grew wider
        than the screen and pushed the Actions buttons out of
        sight beyond a horizontal scroll. Internship and Thesis
        run five days a week and were the only rows long enough
        to do it.

        Returning a list lets the template render one element
        per day, which gives the browser somewhere to wrap.
        Order follows the calendar week, not the order typed,
        so "Thursday,Sunday" and "Sunday,Thursday" read the
        same on screen.
        """

        try:
            indexes = parse_course_days(self.course_days)

        except ValueError:
            # An unrecognised day name is a data problem, not a reason for
            # the page to fail. Show what was typed.
            return [
                part.strip()
                for part in (self.course_days or "").split(",")
                if part.strip()
            ]

        return [DAY_NAMES[index] for index in indexes]

    def missed_holidays(self):
        """Holidays that displaced a sitting in this block."""

        return excluded_holidays(
            self.start_date,
            self.end_date,
            self.course_days
        )

    def __str__(self):
        if self.course_id and self.lecturer_id:
            return f"{self.course.name} - {self.lecturer}"
        return "Workload Assignment"
