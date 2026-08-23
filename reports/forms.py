from django import forms

from academics.models import (
    AcademicPeriod,
    Faculty,
    Program,
    Lecturer,
    Cohort
)

from workload.models import Workload



class WorkloadReportFilterForm(forms.Form):


    academic_period = forms.ModelChoiceField(
        queryset=AcademicPeriod.objects.all(),
        required=False,
        empty_label="All Academic Periods",
        label="Academic Period"
    )


    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        required=False,
        empty_label="All Faculties",
        label="Faculty"
    )


    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        required=False,
        empty_label="All Programs",
        label="Program"
    )


    lecturer = forms.ModelChoiceField(
        queryset=Lecturer.objects.all(),
        required=False,
        empty_label="All Lecturers",
        label="Lecturer"
    )


    cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.all(),
        required=False,
        empty_label="All Cohorts",
        label="Cohort"
    )


    status = forms.ChoiceField(

        choices=[
            ("", "All Status"),

            ("Upcoming", "Upcoming"),

            ("Ongoing", "Ongoing"),

            ("Pending", "Pending"),

            ("Done", "Done"),

        ],

        required=False,

        label="Workload Status"

    )