from django.urls import path

from . import views



urlpatterns = [


    # ============================
    # Administrator Dashboard
    # URL:
    # /admin-dashboard/
    # ============================

    path(
        '',
        views.dashboard,
        name='admin_dashboard'
    ),




    # ============================
    # Analytics Reports
    # URL:
    # /admin-dashboard/reports/
    # ============================

    path(
        'reports/',
        views.reports,
        name='reports'
    ),


]