from django.contrib import admin

from django.urls import path, include



urlpatterns = [

    # ============================
    # Django Administration Panel
    # ============================

    path(
        "admin/",
        admin.site.urls
    ),



    # ============================
    # Authentication
    # Login / Logout
    # User Management
    # ============================

    path(
        "",
        include(
            "accounts.urls",
            namespace="accounts"
        )
    ),



    # ============================
    # Administrator Dashboard
    # Analytics and Reports
    # ============================

    path(
        "admin-dashboard/",
        include(
            "analytics.urls"
        )
    ),



    # ============================
    # Academic Management
    # Faculty
    # Programs
    # Courses
    # Cohorts
    # ============================

    path(
        "academics/",
        include(
            "academics.urls"
        )
    ),



    # ============================
    # Workload Management
    # Schedule
    # Lecturer Workload
    # ============================

    path(
        "workload/",
        include(
            "workload.urls"
        )
    ),


    # ============================
    # Printable Workload Reports
    # ============================

    path(
        "reports/",
        include(
            "reports.urls",
            namespace="reports"
        )
    ),

]