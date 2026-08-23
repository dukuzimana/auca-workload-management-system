from unfold.admin import ModelAdmin
from django.contrib import admin

from academics.models import (
    Faculty,
    Program,
    Lecturer,
    Course
)

from workload.models import Workload



class DashboardAdminSite(admin.AdminSite):


    site_header = (
        "AUCA Workload Management System"
    )


    site_title = (
        "AUCA Admin"
    )


admin.site.site_header = (
    "AUCA Workload Management System"
)


admin.site.site_title = (
    "AUCA Administration"
)


admin.site.index_title = (
    "System Dashboard"
)