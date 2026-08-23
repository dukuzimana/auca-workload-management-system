from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.contrib.auth import get_user_model

from accounts.decorators import admin_required


from .models import (
    Faculty,
    Program,
    Cohort,
    AcademicPeriod,
    Lecturer,
    Course,
    Holiday
)


from .forms import (
    FacultyForm,
    ProgramForm,
    CohortForm,
    AcademicPeriodForm,
    LecturerForm,
    CourseForm,
    HolidayForm,
)


User = get_user_model()


from common.search import (
    search,
    search_context,
    FACULTY_SEARCH_FIELDS,
    PROGRAM_SEARCH_FIELDS,
    COHORT_SEARCH_FIELDS,
    COURSE_SEARCH_FIELDS,
    LECTURER_SEARCH_FIELDS,
    PERIOD_SEARCH_FIELDS,
    HOLIDAY_SEARCH_FIELDS,
)


def searchable_list(request, queryset, fields, template, key, placeholder):
    """
    Render an admin list screen with its search box.

    Every list screen here does the same three things: read the
    search term, narrow the queryset, and report how many rows
    survived out of how many exist. Sharing it keeps the screens
    consistent and stops search drifting apart between them.
    """
    context = search_context(
        request,
        placeholder=placeholder
    )

    filtered = search(
        queryset,
        context["search_query"],
        fields
    )

    context.update({
        key: filtered,
        "total_count": queryset.count(),
        "result_count": filtered.count(),
    })

    return render(
        request,
        template,
        context
    )



# =====================================================
# GENERIC CRUD HELPERS
# =====================================================


def save_form(
    request,
    form_class,
    template,
    title,
    redirect_name,
    instance=None
):

    # Whether this is an edit decides the wording of the
    # confirmation, and it is only knowable before the save.
    is_update = instance is not None

    form = form_class(
        request.POST or None,
        instance=instance
    )


    if form.is_valid():

        obj = form.save()

        # Named from the model, so a new screen using this
        # helper is confirmed correctly without being listed
        # anywhere here.
        label = obj._meta.verbose_name

        messages.success(
            request,
            f"{label.title()} \u201c{obj}\u201d "
            f"{'updated' if is_update else 'added'} successfully."
        )

        return redirect(
            redirect_name
        )


    if request.method == "POST":

        messages.error(
            request,
            "Nothing was saved. Please correct the errors below."
        )


    return render(
        request,
        template,
        {
            "form": form,
            "title": title
        }
    )





def delete_object(
    request,
    obj,
    redirect_name
):

    if request.method == "POST":

        # Read both before the delete: afterwards the instance
        # is gone and str(obj) can no longer reach its
        # related rows.
        label = obj._meta.verbose_name
        name = str(obj)

        obj.delete()

        messages.success(
            request,
            f"{label.title()} \u201c{name}\u201d deleted successfully."
        )

        return redirect(
            redirect_name
        )


    return render(
        request,
        "academics/delete.html",
        {
            "object": obj
        }
    )





# =====================================================
# FACULTY
# =====================================================


@login_required
@admin_required
def faculty_list(request):

    return searchable_list(
        request,
        Faculty.objects.all(),
        FACULTY_SEARCH_FIELDS,
        "academics/faculties.html",
        "faculties",
        "Search faculties by name or description"
    )




@login_required
@admin_required
def faculty_create(request):

    return save_form(
        request,
        FacultyForm,
        "academics/form.html",
        "Add Faculty",
        "academics:faculty_list"
    )





@login_required
@admin_required
def faculty_update(request, pk):

    faculty = get_object_or_404(
        Faculty,
        pk=pk
    )

    return save_form(
        request,
        FacultyForm,
        "academics/form.html",
        "Update Faculty",
        "academics:faculty_list",
        faculty
    )





@login_required
@admin_required
def faculty_delete(request, pk):

    faculty = get_object_or_404(
        Faculty,
        pk=pk
    )

    return delete_object(
        request,
        faculty,
        "academics:faculty_list"
    )





# =====================================================
# PROGRAM
# =====================================================


@login_required
@admin_required
def program_list(request):

    return searchable_list(
        request,
        Program.objects.select_related("faculty"),
        PROGRAM_SEARCH_FIELDS,
        "academics/programs.html",
        "programs",
        "Search programmes by name or faculty"
    )





@login_required
@admin_required
def program_create(request):

    return save_form(
        request,
        ProgramForm,
        "academics/form.html",
        "Add Program",
        "academics:program_list"
    )





@login_required
@admin_required
def program_update(request, pk):

    program = get_object_or_404(
        Program,
        pk=pk
    )

    return save_form(
        request,
        ProgramForm,
        "academics/form.html",
        "Update Program",
        "academics:program_list",
        program
    )





@login_required
@admin_required
def program_delete(request, pk):

    program = get_object_or_404(
        Program,
        pk=pk
    )

    return delete_object(
        request,
        program,
        "academics:program_list"
    )





# =====================================================
# COHORT
# =====================================================


@login_required
@admin_required
def cohort_list(request):

    return searchable_list(
        request,
        Cohort.objects.select_related("program", "program__faculty", "representative"),
        COHORT_SEARCH_FIELDS,
        "academics/cohorts.html",
        "cohorts",
        "Search cohorts by name, programme or intake year"
    )





@login_required
@admin_required
def cohort_create(request):

    return save_form(
        request,
        CohortForm,
        "academics/form.html",
        "Add Cohort",
        "academics:cohort_list"
    )





@login_required
@admin_required
def cohort_update(request, pk):

    cohort = get_object_or_404(
        Cohort,
        pk=pk
    )

    return save_form(
        request,
        CohortForm,
        "academics/form.html",
        "Update Cohort",
        "academics:cohort_list",
        cohort
    )





@login_required
@admin_required
def cohort_delete(request, pk):

    cohort = get_object_or_404(
        Cohort,
        pk=pk
    )

    return delete_object(
        request,
        cohort,
        "academics:cohort_list"
    )





# =====================================================
# COURSE
# =====================================================


@login_required
@admin_required
def course_list(request):

    return searchable_list(
        request,
        Course.objects.select_related("program"),
        COURSE_SEARCH_FIELDS,
        "academics/courses.html",
        "courses",
        "Search courses by code, name or level"
    )





@login_required
@admin_required
def course_create(request):

    return save_form(
        request,
        CourseForm,
        "academics/form.html",
        "Add Course",
        "academics:course_list"
    )





@login_required
@admin_required
def course_update(request, pk):

    course = get_object_or_404(
        Course,
        pk=pk
    )


    return save_form(
        request,
        CourseForm,
        "academics/form.html",
        "Update Course",
        "academics:course_list",
        course
    )





@login_required
@admin_required
def course_delete(request, pk):

    course = get_object_or_404(
        Course,
        pk=pk
    )


    return delete_object(
        request,
        course,
        "academics:course_list"
    )





# =====================================================
# LECTURER
# =====================================================


@login_required
@admin_required
def lecturer_list(request):

    return searchable_list(
        request,
        Lecturer.objects.select_related("user"),
        LECTURER_SEARCH_FIELDS,
        "academics/lecturers.html",
        "lecturers",
        "Search lecturers by name, qualification or status"
    )





@login_required
@admin_required
def lecturer_create(request):

    return save_form(
        request,
        LecturerForm,
        "academics/form.html",
        "Add Lecturer",
        "academics:lecturer_list"
    )





@login_required
@admin_required
def lecturer_update(request, pk):

    lecturer = get_object_or_404(
        Lecturer,
        pk=pk
    )


    return save_form(
        request,
        LecturerForm,
        "academics/form.html",
        "Update Lecturer",
        "academics:lecturer_list",
        lecturer
    )





@login_required
@admin_required
def lecturer_delete(request, pk):

    lecturer = get_object_or_404(
        Lecturer,
        pk=pk
    )


    return delete_object(
        request,
        lecturer,
        "academics:lecturer_list"
    )





# =====================================================
# ACADEMIC PERIOD
# =====================================================


@login_required
@admin_required
def academic_period_list(request):

    return searchable_list(
        request,
        AcademicPeriod.objects.all(),
        PERIOD_SEARCH_FIELDS,
        "academics/academic_periods.html",
        "periods",
        "Search periods by year, semester or teaching period"
    )





@login_required
@admin_required
def academic_period_create(request):

    return save_form(
        request,
        AcademicPeriodForm,
        "academics/form.html",
        "Add Academic Period",
        "academics:academic_period_list"
    )





@login_required
@admin_required
def academic_period_update(request, pk):

    period = get_object_or_404(
        AcademicPeriod,
        pk=pk
    )


    return save_form(
        request,
        AcademicPeriodForm,
        "academics/form.html",
        "Update Academic Period",
        "academics:academic_period_list",
        period
    )





@login_required
@admin_required
def academic_period_delete(request, pk):

    period = get_object_or_404(
        AcademicPeriod,
        pk=pk
    )


    return delete_object(
        request,
        period,
        "academics:academic_period_list"
    )





# =====================================================
# HOLIDAY
# =====================================================


@login_required
@admin_required
def holiday_list(request):

    return searchable_list(
        request,
        Holiday.objects.all(),
        HOLIDAY_SEARCH_FIELDS,
        "academics/holidays.html",
        "holidays",
        "Search holidays by name or date"
    )





@login_required
@admin_required
def holiday_create(request):

    return save_form(
        request,
        HolidayForm,
        "academics/form.html",
        "Add Holiday",
        "academics:holiday_list"
    )





@login_required
@admin_required
def holiday_update(request, pk):

    holiday = get_object_or_404(
        Holiday,
        pk=pk
    )


    return save_form(
        request,
        HolidayForm,
        "academics/form.html",
        "Update Holiday",
        "academics:holiday_list",
        holiday
    )





@login_required
@admin_required
def holiday_delete(request, pk):

    holiday = get_object_or_404(
        Holiday,
        pk=pk
    )


    return delete_object(
        request,
        holiday,
        "academics:holiday_list"
    )
