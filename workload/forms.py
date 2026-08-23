from django import forms

from .models import Workload

from academics.models import (
    Lecturer,
    Course,
    Cohort,
    AcademicPeriod
)



# ==================================================
# WORKLOAD FORM
# ==================================================

class WorkloadForm(forms.ModelForm):


    class Meta:

        model = Workload


        fields = [

            "cohort",

            "academic_period",

            "lecturer",

            "co_lecturers",

            "course",

            "start_date",

            "course_days",

            "duration_weeks",

        ]



        widgets = {


            "cohort": forms.Select(

                attrs={

                    "class": "form-control"

                }

            ),



            "academic_period": forms.Select(

                attrs={

                    "class": "form-control"

                }

            ),



            "lecturer": forms.Select(

                attrs={

                    "class": "form-control"

                }

            ),



            "course": forms.Select(

                attrs={

                    "class": "form-control"

                }

            ),



            "start_date": forms.DateInput(

                attrs={

                    "class": "form-control",

                    "type": "date"

                }

            ),



            "course_days": forms.TextInput(

                attrs={

                    "class": "form-control",

                    "placeholder":
                    "Example: Monday,Thursday"

                }

            ),



            "co_lecturers": forms.SelectMultiple(

                attrs={

                    "class": "form-control",

                    "size": 4

                }

            ),



            "duration_weeks": forms.NumberInput(

                attrs={

                    "class": "form-control",

                    "min": 1,

                    "placeholder":
                    "Leave blank for the standard block"

                }

            ),

        }



    # =============================================
    # INITIAL DATA
    # =============================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)



        self.fields["lecturer"].queryset = (
            Lecturer.objects.all()
        )


        self.fields["course"].queryset = (
            Course.objects.all()
        )


        self.fields["cohort"].queryset = (
            Cohort.objects.all()
        )


        self.fields["academic_period"].queryset = (
            AcademicPeriod.objects.all()
        )


        # Co-teaching is the exception, not the rule, and a
        # module with no duration override runs its standard
        # block. Neither should stop the form saving.
        self.fields["co_lecturers"].queryset = (
            Lecturer.objects.all()
        )

        self.fields["co_lecturers"].required = False

        self.fields["co_lecturers"].label = (
            "Co-lecturers (optional)"
        )

        self.fields["co_lecturers"].help_text = (
            "Hold Ctrl (Cmd on a Mac) to select more than one. "
            "They see the module on their own dashboard and are "
            "emailed with the lead lecturer."
        )

        self.fields["duration_weeks"].required = False


    # =============================================
    # VALIDATE CO-LECTURERS
    # =============================================

    def clean_co_lecturers(self):
        """
        The lead lecturer is not their own co-lecturer.

        Selecting the same person in both fields would email
        them twice and show the module twice on their
        dashboard, so it is dropped rather than rejected --
        the intent is clear and there is nothing to correct.
        """

        co_lecturers = self.cleaned_data.get("co_lecturers")

        if not co_lecturers:
            return co_lecturers

        lead = self.data.get("lecturer") or None

        if lead:
            return co_lecturers.exclude(pk=lead)

        return co_lecturers



    # =============================================
    # VALIDATE COURSE DAYS
    # =============================================

    def clean_course_days(self):

        data = self.cleaned_data.get(
            "course_days"
        )


        if not data:

            raise forms.ValidationError(
                "Please enter teaching days."
            )


        days = [

            day.strip()

            for day in data.split(",")

        ]



        valid_days = [

            "Monday",

            "Tuesday",

            "Wednesday",

            "Thursday",

            "Friday",

            "Saturday",

            "Sunday",

        ]



        for day in days:


            if day not in valid_days:


                raise forms.ValidationError(

                    f"{day} is not a valid day. "
                    "Use full day names."

                )



        return ",".join(days)



    # =============================================
    # VALIDATE DUPLICATE ASSIGNMENT
    # =============================================

    def clean(self):

        cleaned_data = super().clean()



        cohort = cleaned_data.get(
            "cohort"
        )


        academic_period = cleaned_data.get(
            "academic_period"
        )


        lecturer = cleaned_data.get(
            "lecturer"
        )


        course = cleaned_data.get(
            "course"
        )



        if all([

            cohort,

            academic_period,

            lecturer,

            course

        ]):



            queryset = Workload.objects.filter(

                cohort=cohort,

                academic_period=academic_period,

                lecturer=lecturer,

                course=course,

            )



            # Exclude current object during UPDATE

            if self.instance.pk:

                queryset = queryset.exclude(

                    pk=self.instance.pk

                )



            if queryset.exists():


                raise forms.ValidationError(

                    "This workload assignment already exists."

                )



        return cleaned_data