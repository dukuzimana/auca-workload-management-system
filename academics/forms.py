from django import forms

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Faculty,
    Program,
    Cohort,
    AcademicPeriod,
    Lecturer,
    Course,
    Holiday
)


User = get_user_model()



# ==================================================
# FACULTY FORM
# ==================================================

class FacultyForm(forms.ModelForm):

    class Meta:

        model = Faculty

        fields = [
            "name",
            "description"
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter faculty name"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Faculty description"
                }
            )

        }





# ==================================================
# PROGRAM FORM
# ==================================================

class ProgramForm(forms.ModelForm):

    class Meta:

        model = Program

        fields = [
            "faculty",
            "name"
        ]

        widgets = {

            "faculty": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter program name"
                }
            )

        }





# ==================================================
# COHORT FORM
# ==================================================

class CohortForm(forms.ModelForm):

    class Meta:

        model = Cohort

        fields = [
            "program",
            "representative",
            "name",
            "intake_year"
        ]

        widgets = {

            "program": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "representative": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter cohort name"
                }
            ),

            "intake_year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2025"
                }
            )

        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        field = self.fields["representative"]


        # Cohort.representative is OneToOne, so offering an account
        # that already holds another class is a UNIQUE error on save,
        # not a choice. The current holder stays in the queryset, or
        # re-showing the form would blank a valid value.
        available = Q(representing_cohort__isnull=True)

        if self.instance.pk and self.instance.representative_id:

            available |= Q(pk=self.instance.representative_id)


        field.queryset = User.objects.filter(
            available,
            role="representative"
        ).order_by("username")


        field.required = False

        field.label = "Class representative"

        field.empty_label = "-- No representative --"


        # Flag accounts with no email: they cannot be notified.
        def label(user):

            if not user.email:
                return f"{user.username} (no email address)"

            return f"{user.username} ({user.email})"


        field.label_from_instance = label


        # An empty dropdown looks broken unless it says why it is
        # empty. Two different causes, two different fixes, and
        # neither is obvious from a list showing nothing.
        if not field.queryset.exists():

            total = User.objects.filter(
                role="representative"
            ).count()

            create = reverse("accounts:create_user")

            if total == 0:

                field.help_text = mark_safe(
                    "No class representative accounts exist yet. "
                    f"<a href=\"{create}\">Create one</a> with the role "
                    "set to Class Representative, then set it here."
                )

            else:

                # Every account is spoken for. A cohort can only
                # have one and an account can only hold one, so the
                # way forward is another account, not another pick.
                field.help_text = mark_safe(
                    f"All {total} representative accounts are already "
                    "assigned to a cohort. "
                    f"<a href=\"{create}\">Create another</a> to assign "
                    "one here, or leave this blank and set it later."
                )

        else:

            field.help_text = (
                "Optional. Can be set later by editing the cohort."
            )







# ==================================================
# ACADEMIC PERIOD FORM
# ==================================================

class AcademicPeriodForm(forms.ModelForm):

    class Meta:

        model = AcademicPeriod

        fields = [

            "academic_year",

            "semester",

            "teaching_period",

            "start_date",

            "end_date"

        ]


        widgets = {

            "academic_year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2025/2026"
                }
            ),

            "semester": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "teaching_period": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: January - June 2026"
                }
            ),

            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "end_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

        }







# ==================================================
# LECTURER FORM
# ==================================================

class LecturerForm(forms.ModelForm):

    class Meta:

        model = Lecturer

        fields = [

            "user",

            "name",

            "qualification",

            "employment_status"

        ]


        widgets = {


            "user": forms.Select(

                attrs={

                    "class": "form-control"

                }

            ),



            "name": forms.TextInput(

                attrs={

                    "class": "form-control",

                    "placeholder":
                    "Enter lecturer full name"

                }

            ),



            "qualification": forms.Textarea(

                attrs={

                    "class": "form-control",

                    "rows": 3,

                    "placeholder":
                    "Academic qualification"

                }

            ),



            "employment_status": forms.TextInput(

                attrs={

                    "class": "form-control",

                    "placeholder":
                    "Example: Full Time"

                }

            )

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


        self.fields["user"].queryset = User.objects.filter(

            role="lecturer"

        )





# ==================================================
# COURSE FORM
# ==================================================

class CourseForm(forms.ModelForm):

    class Meta:

        model = Course

        fields = [

            "program",

            "code",

            "name",

            "credits",

            "level"

        ]


        widgets = {

            "program": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Course code"
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Course name"
                }
            ),

            "credits": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "level": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Masters"
                }
            )

        }







# ==================================================
# HOLIDAY FORM
# ==================================================

class HolidayForm(forms.ModelForm):

    class Meta:

        model = Holiday

        fields = [

            "date",

            "name"

        ]


        widgets = {

            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Holiday name"
                }
            )

        }
