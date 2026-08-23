from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    fieldsets = UserAdmin.fieldsets + (
        ("Role Information", {
            "fields": ("role",)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role Information", {
            "fields": ("role",)
        }),
    )