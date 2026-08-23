from django import forms

from django.contrib.auth.forms import UserCreationForm

from .models import User

from academics.models import (
    Lecturer,
    Cohort
)


# ==================================================
# CREATE USER FORM
# ==================================================

class UserCreateForm(UserCreationForm):

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "role",
        ]

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username"
            }
        )
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Email"
            }
        )
    )

    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )


# ==================================================
# UPDATE USER FORM
# ==================================================

class UserUpdateForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            "username",
            "email",
            "role",
            "is_active",
        ]

    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control"
            }
        )
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control"
            }
        )
    )

    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    is_active = forms.BooleanField(
        required=False
    )

    def clean_role(self):
        """
        Refuse a role change that would strand an existing link.

        A user linked to a lecturer record cannot quietly become a
        representative: the link row would survive, the lecturer
        would keep pointing at an account that no longer passes the
        lecturer role check, and that lecturer's workload would
        disappear from every screen with nothing to explain why.
        Removing the link first is an explicit, reversible step.
        """
        role = self.cleaned_data.get("role")

        if not self.instance.pk or role == self.instance.role:
            return role

        if self.instance.role == "lecturer" and role != "lecturer":

            linked = Lecturer.objects.filter(
                user=self.instance
            ).first()

            if linked:
                raise forms.ValidationError(
                    f"This account is set as the login for the "
                    f"lecturer record '{linked.name}'. Open "
                    f"Academics > Lecturers, clear the User Account "
                    f"field on that record, then change the role."
                )

        if self.instance.role == "representative" and role != "representative":

            linked = Cohort.objects.filter(
                representative=self.instance
            ).first()

            if linked:
                raise forms.ValidationError(
                    f"This account is set as the class "
                    f"representative for '{linked.name}'. Open "
                    f"Academics > Cohorts, clear the Representative "
                    f"field on that cohort, then change the role."
                )

        return role
