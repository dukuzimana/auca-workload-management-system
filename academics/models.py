from django.db import models
from django.conf import settings



# =========================
# Faculty
# =========================

class Faculty(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )


    class Meta:
        ordering = ['name']


    def __str__(self):
        return self.name





# =========================
# Program
# =========================

class Program(models.Model):

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name="programs"
    )


    name = models.CharField(
        max_length=200
    )


    class Meta:
        ordering = ['name']

        unique_together = [
            ('faculty', 'name')
        ]


    def __str__(self):
        return self.name





# =========================
# Cohort
# =========================

class Cohort(models.Model):

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="cohorts"
    )


    # Class Representative User
    representative = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={
            "role": "representative"
        },
        related_name="representing_cohort"
    )


    name = models.CharField(
        max_length=100
    )


    intake_year = models.IntegerField()



    class Meta:

        ordering = [
            "name"
        ]

        unique_together = [
            ("program", "name")
        ]



    def __str__(self):

        return self.name







# =========================
# Academic Period
# =========================

class AcademicPeriod(models.Model):


    # Cohort is part of the key: two cohorts can run the same
    # semester on different dates. Nullable for existing rows.
    cohort = models.ForeignKey(
        "academics.Cohort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="academic_periods"
    )


    SEMESTER_CHOICES = [

        ("Semester 1", "Semester 1"),

        ("Semester 2", "Semester 2"),

        ("Semester 3", "Semester 3"),

        ("Semester 4", "Semester 4"),

    ]



    academic_year = models.CharField(
        max_length=20
    )



    semester = models.CharField(
        max_length=20,
        choices=SEMESTER_CHOICES
    )



    teaching_period = models.CharField(
        max_length=100
    )


    start_date = models.DateField()


    end_date = models.DateField()



    class Meta:

        ordering = [
            "-academic_year"
        ]


        unique_together = [
            (
                "academic_year",
                "semester",
                "cohort"
            )
        ]



    def __str__(self):

        label = f"{self.academic_year} - {self.semester}"

        if self.cohort_id:
            return f"{self.cohort.name}: {label}"

        return label










# =========================
# Lecturer
# =========================

class Lecturer(models.Model):


    # SET_NULL, not CASCADE: deleting a login must not delete the
    # lecturer record and every Workload row pointing at it.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecturer_profile"
    )


    name = models.CharField(
        max_length=150
    )


    qualification = models.TextField(
        blank=True
    )


    employment_status = models.CharField(
        max_length=50
    )


    class Meta:

        ordering = [
            "name"
        ]



    def __str__(self):

        return self.name










# =========================
# Course
# =========================

class Course(models.Model):


    program = models.ForeignKey(

        Program,

        on_delete=models.CASCADE,

        related_name="courses",

        null=True,

        blank=True

    )


    code = models.CharField(
        max_length=20,
        unique=True
    )


    name = models.CharField(
        max_length=200
    )


    credits = models.IntegerField()


    level = models.CharField(
        max_length=20
    )



    class Meta:

        ordering = [
            "code"
        ]



    def __str__(self):

        return f"{self.code} - {self.name}"









# =========================
# Holiday
# =========================

class Holiday(models.Model):


    date = models.DateField()


    name = models.CharField(
        max_length=100
    )


    class Meta:

        ordering = [
            "date"
        ]


    def __str__(self):

        return f"{self.name} - {self.date}"