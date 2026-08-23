from django.contrib import admin

from .models import (
    Faculty,
    Program,
    Cohort,
    AcademicPeriod,
    Lecturer,
    Course,
    Holiday
)



# ==================================================
# FACULTY ADMIN
# ==================================================

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "description",
    )


    search_fields = (
        "name",
    )





# ==================================================
# PROGRAM ADMIN
# ==================================================

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "faculty",
    )


    list_filter = (
        "faculty",
    )


    search_fields = (
        "name",
        "faculty__name",
    )







# ==================================================
# COHORT ADMIN
# ==================================================

@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "program",
        "representative",
        "intake_year",
    )


    list_filter = (
        "program",
        "intake_year",
    )


    search_fields = (
        "name",
        "program__name",
    )









# ==================================================
# ACADEMIC PERIOD ADMIN
# ==================================================

@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):

    list_display = (

        "academic_year",

        "semester",

        "teaching_period",

        "start_date",

        "end_date",

    )


    list_filter = (

        "academic_year",

        "semester",

    )


    search_fields = (

        "academic_year",

        "teaching_period",

        "semester",

    )









# ==================================================
# LECTURER ADMIN
# ==================================================

@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):

    list_display = (

        "name",

        "qualification",

        "employment_status",

        "user",

    )


    list_filter = (

        "employment_status",

    )


    search_fields = (

        "name",

        "user__username",

        "user__first_name",

        "user__last_name",

    )











# ==================================================
# COURSE ADMIN
# ==================================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (

        "code",

        "name",

        "program",

        "credits",

        "level",

    )


    list_filter = (

        "program",

        "level",

    )


    search_fields = (

        "code",

        "name",

        "program__name",

    )











# ==================================================
# HOLIDAY ADMIN
# ==================================================

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):

    list_display = (

        "name",

        "date",

    )


    list_filter = (

        "date",

    )


    search_fields = (

        "name",

    )