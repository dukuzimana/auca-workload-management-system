# ==========================================================
# AUCA WORKLOAD MANAGEMENT SYSTEM
# WORKLOAD URL CONFIGURATION
# ==========================================================


from django.urls import path

from . import views


app_name = "workload"


urlpatterns = [

    # ======================================================
    # CREATE WORKLOAD
    # ======================================================

    path(
        "assignment/",
        views.assignment,
        name="assignment"
    ),


    # ======================================================
    # WORKLOAD CRUD
    # ======================================================

    path(
        "workloads/",
        views.workload_list,
        name="workload_list"
    ),

    path(
        "workloads/<int:pk>/",
        views.workload_detail,
        name="workload_detail"
    ),

    path(
        "workloads/<int:pk>/edit/",
        views.workload_update,
        name="workload_update"
    ),

    path(
        "workloads/<int:pk>/delete/",
        views.workload_delete,
        name="workload_delete"
    ),


    # ======================================================
    # LECTURER
    # ======================================================

    path(
        "lecturer-dashboard/",
        views.lecturer_dashboard,
        name="lecturer_dashboard"
    ),

    path(
        "lecturer-workload/print/",
        views.lecturer_workload_print,
        name="lecturer_workload_print"
    ),


    # Two names, one role-routing view: the sidebar offers the same
    # link to administrators and lecturers.

    path(
        "lecturer-calendar/",
        views.calendar,
        name="lecturer_calendar"
    ),

    path(
        "calendar/",
        views.calendar,
        name="calendar"
    ),

    path(
        "master-calendar/",
        views.master_calendar,
        name="master_calendar"
    ),


    # ======================================================
    # CLASS REPRESENTATIVE
    # ======================================================

    path(
        "representative-dashboard/",
        views.representative_dashboard,
        name="representative_dashboard"
    ),

    path(
        "representative-calendar/",
        views.representative_calendar,
        name="representative_calendar"
    ),

    path(
        "representative-calendar/print/",
        views.representative_calendar_print,
        name="representative_calendar_print"
    ),

]
