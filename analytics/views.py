from django.shortcuts import render

from django.contrib.auth.decorators import login_required

from django.db.models import Sum

from accounts.decorators import admin_required

from accounts.models import User


from academics.models import (
    Faculty,
    Program,
    Lecturer,
    Course,
)


from workload.models import Workload







# ==================================
# Administrator Dashboard
# ==================================

@login_required
@admin_required
def dashboard(request):


    # ===============================
    # ACADEMIC STATISTICS
    # ===============================


    total_faculties = Faculty.objects.count()


    total_programs = Program.objects.count()


    total_lecturers = Lecturer.objects.count()


    total_courses = Course.objects.count()





    # ===============================
    # USER STATISTICS
    # ===============================


    total_users = User.objects.count()


    total_admins = User.objects.filter(
        role="admin"
    ).count()



    total_lecturer_accounts = User.objects.filter(
        role="lecturer"
    ).count()



    total_representatives = User.objects.filter(
        role="representative"
    ).count()







    # ===============================
    # WORKLOAD DISTRIBUTION
    # ===============================


    workload_distribution = []



    for faculty in Faculty.objects.all():


        total_hours = Workload.objects.filter(

            cohort__program__faculty=faculty

        ).aggregate(

            total=Sum("hours")

        )["total"] or 0



        workload_distribution.append(

            {

                "faculty": faculty.name,

                "hours": total_hours

            }

        )









    # ===============================
    # WORKLOAD STATUS
    # ===============================


    status_data = [

        Workload.objects.filter(
            status="Upcoming"
        ).count(),


        Workload.objects.filter(
            status="Ongoing"
        ).count(),


        Workload.objects.filter(
            status="Done"
        ).count(),


        Workload.objects.filter(
            status="Pending"
        ).count(),

    ]










    # ===============================
    # RECENT ACTIVITIES
    # ===============================


    recent_workloads = Workload.objects.select_related(

        "course",

        "lecturer",

        "cohort",

        "academic_period",

        "cohort__program",

        "cohort__program__faculty"

    ).order_by(

        "-id"

    )[:5]







    context = {


        # Academic cards

        "total_faculties":
            total_faculties,


        "total_programs":
            total_programs,


        "total_lecturers":
            total_lecturers,


        "total_courses":
            total_courses,




        # User cards

        "total_users":
            total_users,


        "total_admins":
            total_admins,


        "total_lecturer_accounts":
            total_lecturer_accounts,


        "total_representatives":
            total_representatives,




        # Charts

        "workload_distribution":
            workload_distribution,


        "status_data":
            status_data,




        # Activities

        "recent_workloads":
            recent_workloads,

    }





    return render(

        request,

        "analytics/dashboard.html",

        context

    )








# ==================================
# Reports
# ==================================

@login_required
@admin_required
def reports(request):


    workloads = Workload.objects.select_related(

        "course",

        "lecturer",

        "cohort",

        "academic_period"

    ).order_by(

        "-id"

    )



    context = {


        "workloads": workloads,


        "total_workloads":
            workloads.count(),


        "completed":
            workloads.filter(
                status="Done"
            ).count(),


        "ongoing":
            workloads.filter(
                status="Ongoing"
            ).count(),


        "upcoming":
            workloads.filter(
                status="Upcoming"
            ).count(),


        "pending":
            workloads.filter(
                status="Pending"
            ).count(),


    }




    return render(

        request,

        "analytics/reports.html",

        context

    )