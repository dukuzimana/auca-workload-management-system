from django.urls import path

from . import views



app_name = "academics"



urlpatterns = [


    # =========================
    # FACULTY CRUD
    # =========================

    path(
        'faculties/',
        views.faculty_list,
        name='faculty_list'
    ),


    path(
        'faculties/create/',
        views.faculty_create,
        name='faculty_create'
    ),


    path(
        'faculties/<int:pk>/update/',
        views.faculty_update,
        name='faculty_update'
    ),


    path(
        'faculties/<int:pk>/delete/',
        views.faculty_delete,
        name='faculty_delete'
    ),






    # =========================
    # PROGRAM CRUD
    # =========================

    path(
        'programs/',
        views.program_list,
        name='program_list'
    ),


    path(
        'programs/create/',
        views.program_create,
        name='program_create'
    ),


    path(
        'programs/<int:pk>/update/',
        views.program_update,
        name='program_update'
    ),


    path(
        'programs/<int:pk>/delete/',
        views.program_delete,
        name='program_delete'
    ),






    # =========================
    # COHORT CRUD
    # =========================

    path(
        'cohorts/',
        views.cohort_list,
        name='cohort_list'
    ),


    path(
        'cohorts/create/',
        views.cohort_create,
        name='cohort_create'
    ),


    path(
        'cohorts/<int:pk>/update/',
        views.cohort_update,
        name='cohort_update'
    ),


    path(
        'cohorts/<int:pk>/delete/',
        views.cohort_delete,
        name='cohort_delete'
    ),






    # =========================
    # COURSE CRUD
    # =========================

    path(
        'courses/',
        views.course_list,
        name='course_list'
    ),


    path(
        'courses/create/',
        views.course_create,
        name='course_create'
    ),


    path(
        'courses/<int:pk>/update/',
        views.course_update,
        name='course_update'
    ),


    path(
        'courses/<int:pk>/delete/',
        views.course_delete,
        name='course_delete'
    ),






    # =========================
    # LECTURER CRUD
    # =========================

    path(
        'lecturers/',
        views.lecturer_list,
        name='lecturer_list'
    ),


    path(
        'lecturers/create/',
        views.lecturer_create,
        name='lecturer_create'
    ),


    path(
        'lecturers/<int:pk>/update/',
        views.lecturer_update,
        name='lecturer_update'
    ),


    path(
        'lecturers/<int:pk>/delete/',
        views.lecturer_delete,
        name='lecturer_delete'
    ),





    # =========================
    # ACADEMIC PERIOD CRUD
    # =========================

    path(
        'academic-periods/',
        views.academic_period_list,
        name='academic_period_list'
    ),


    path(
        'academic-periods/create/',
        views.academic_period_create,
        name='academic_period_create'
    ),


    path(
        'academic-periods/<int:pk>/update/',
        views.academic_period_update,
        name='academic_period_update'
    ),


    path(
        'academic-periods/<int:pk>/delete/',
        views.academic_period_delete,
        name='academic_period_delete'
    ),





    # =========================
    # HOLIDAY CRUD
    # =========================

    path(
        'holidays/',
        views.holiday_list,
        name='holiday_list'
    ),


    path(
        'holidays/create/',
        views.holiday_create,
        name='holiday_create'
    ),


    path(
        'holidays/<int:pk>/update/',
        views.holiday_update,
        name='holiday_update'
    ),


    path(
        'holidays/<int:pk>/delete/',
        views.holiday_delete,
        name='holiday_delete'
    ),


]