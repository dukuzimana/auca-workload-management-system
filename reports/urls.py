from django.urls import path

from . import views


app_name = "reports"


urlpatterns = [

    path(
        "workload-report/",
        views.workload_report,
        name="workload_report"
    ),

    path(
        "workload-report/print/",
        views.workload_report_print,
        name="workload_report_print"
    ),

    path(
        "workload-report/csv/",
        views.workload_report_csv,
        name="workload_report_csv"
    ),

]
