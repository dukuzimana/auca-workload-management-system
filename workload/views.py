from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from accounts.decorators import (
    admin_required,
    lecturer_required,
    representative_required
)

from .models import Workload
from .forms import WorkloadForm
from .notifications import notify_assignment, report
from .selectors import (
    is_admin,
    resolve_lecturer,
    resolve_cohort,
    workloads_for_lecturer,
    periods_for,
    apply_period_filter,
)
from .utils import holidays_between

from common.search import (
    search,
    search_context,
    WORKLOAD_SEARCH_FIELDS,
    OWN_WORKLOAD_SEARCH_FIELDS,
    COHORT_WORKLOAD_SEARCH_FIELDS,
)


BASE_RELATED = (
    "course",
    "lecturer",
    "cohort",
    "academic_period",
)


# ==================================================
# ANNOUNCE AN ASSIGNMENT
# ==================================================

def announce(request, workload, created=True):
    """
    Email the teaching team and the class representative, then
    say on screen what actually happened.

    Both halves are shared with the Django admin, which assigns
    workloads too, so that the two screens cannot tell an
    administrator different things about the same send.
    """

    return report(
        request,
        notify_assignment(
            workload,
            request=request,
            created=created
        )
    )


# ==================================================
# LECTURER DASHBOARD
# ==================================================
@login_required
@lecturer_required
def lecturer_dashboard(request):

    lecturer = resolve_lecturer(request.user)

    if lecturer:

        workloads = workloads_for_lecturer(
            lecturer
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        # Statuses are stored, so correct any that have gone
        # stale before counting by them.
        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    today = timezone.localdate()


    # Tiles count everything; search narrows only the table.
    search_ctx = search_context(
        request,
        placeholder="Search my modules by course, cohort or status"
    )

    visible = search(
        workloads,
        search_ctx["search_query"],
        OWN_WORKLOAD_SEARCH_FIELDS
    )


    context = {

        "lecturer": lecturer,
        "workloads": visible,
        "result_count": visible.count(),
        "total_workloads": workloads.count(),
        "completed": workloads.filter(status="Done").count(),
        "ongoing": workloads.filter(status="Ongoing").count(),
        "upcoming": workloads.filter(status="Upcoming").count(),
        "pending": workloads.filter(status="Pending").count(),

        "total_hours": sum(
            w.hours or 0 for w in workloads
        ),

        "current_course": workloads.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first(),

        "next_course": workloads.filter(
            start_date__gt=today
        ).first(),

    }

    context.update(search_ctx)

    context["total_count"] = context["total_workloads"]


    if lecturer is None:

        messages.warning(
            request,
            "Your account is not linked to a lecturer record yet. "
            "Ask an administrator to link it so your workload appears."
        )


    return render(
        request,
        "workload/lecturer_dashboard.html",
        context
    )



# ==================================================
# LECTURER CALENDAR
# ==================================================
@login_required
@lecturer_required
def lecturer_calendar(request):

    lecturer = resolve_lecturer(request.user)

    if lecturer:

        workloads = workloads_for_lecturer(
            lecturer
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    context = search_context(
        request,
        placeholder="Search my schedule by course or cohort"
    )

    visible = search(
        workloads,
        context["search_query"],
        OWN_WORKLOAD_SEARCH_FIELDS
    )

    context.update({
        "lecturer": lecturer,
        "workloads": visible,
        "schedule_count": workloads.count(),
        "total_count": workloads.count(),
        "result_count": visible.count(),
        "is_admin": False,
    })


    return render(
        request,
        "workload/calendar.html",
        context
    )



# ==================================================
# MASTER CALENDAR
# Every cohort, every lecturer. Administrators only.
# ==================================================
@login_required
@admin_required
def master_calendar(request):

    workloads = Workload.objects.select_related(
        *BASE_RELATED
    ).order_by("start_date")

    workloads.refresh_statuses()


    context = search_context(
        request,
        placeholder="Search by course, lecturer, cohort or status"
    )

    visible = search(
        workloads,
        context["search_query"],
        WORKLOAD_SEARCH_FIELDS
    )

    context.update({
        "lecturer": None,
        "workloads": visible,
        "schedule_count": workloads.count(),
        "total_count": workloads.count(),
        "result_count": visible.count(),
        "is_admin": True,
    })


    return render(
        request,
        "workload/calendar.html",
        context
    )



# ==================================================
# CALENDAR ENTRY POINT
# Routes to the master or personal calendar by role, so the
# one sidebar link works for both administrators and lecturers.
# ==================================================
@login_required
def calendar(request):

    if is_admin(request.user):
        return master_calendar(request)

    return lecturer_calendar(request)



# ==================================================
# REPRESENTATIVE DASHBOARD
# ==================================================
@login_required
@representative_required
def representative_dashboard(request):

    cohort = resolve_cohort(request.user)

    if cohort:

        workloads = Workload.objects.filter(
            cohort=cohort
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    today = timezone.localdate()


    # As on the lecturer dashboard, the tiles count the whole
    # cohort calendar while search narrows only the table.
    search_ctx = search_context(
        request,
        placeholder="Search modules by course or lecturer"
    )

    visible = search(
        workloads,
        search_ctx["search_query"],
        COHORT_WORKLOAD_SEARCH_FIELDS
    )


    context = {

        "cohort": cohort,
        "workloads": visible,
        "result_count": visible.count(),
        "total_courses": workloads.count(),
        "completed": workloads.filter(status="Done").count(),
        "ongoing": workloads.filter(status="Ongoing").count(),
        "upcoming": workloads.filter(status="Upcoming").count(),

        "current_course": workloads.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first(),

        "next_course": workloads.filter(
            start_date__gt=today
        ).first(),

    }

    context.update(search_ctx)

    context["total_count"] = context["total_courses"]


    if cohort is None:

        messages.warning(
            request,
            "Your account is not linked to a cohort yet. "
            "Ask an administrator to link it so your calendar appears."
        )


    return render(
        request,
        "workload/representative_dashboard.html",
        context
    )



# ==================================================
# REPRESENTATIVE CALENDAR
# ==================================================
@login_required
@representative_required
def representative_calendar(request):

    cohort = resolve_cohort(request.user)

    if cohort:

        workloads = Workload.objects.filter(
            cohort=cohort
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    context = search_context(
        request,
        placeholder="Search our calendar by course or lecturer"
    )

    visible = search(
        workloads,
        context["search_query"],
        COHORT_WORKLOAD_SEARCH_FIELDS
    )

    context.update({
        "cohort": cohort,
        "workloads": visible,
        "schedule_count": workloads.count(),
        "total_count": workloads.count(),
        "result_count": visible.count(),
    })


    return render(
        request,
        "workload/representative_calendar.html",
        context
    )



# ==================================================
# CREATE WORKLOAD
# ==================================================
@login_required
@admin_required
def assignment(request):

    workloads = Workload.objects.select_related(
        *BASE_RELATED
    ).order_by("-id")

    workloads.refresh_statuses()


    if request.method == "POST":

        form = WorkloadForm(request.POST)

        if form.is_valid():

            workload = form.save()

            messages.success(
                request,
                f"Workload assigned successfully: {workload.course} "
                f"to {workload.lecturer} for {workload.cohort}."
            )

            # Runs after the save and never raises: the assignment stands
            # whether or not mail is reachable.
            announce(request, workload, created=True)

            return redirect(
                "workload:assignment"
            )


        # The form re-renders with its field errors, but a long
        # page can scroll them out of sight and the row simply
        # looks like it was ignored. Say so at the top, the same
        # way the academics screens do.
        messages.error(
            request,
            "Nothing was assigned. Please correct the errors below."
        )


    else:

        form = WorkloadForm()



    context = search_context(
        request,
        placeholder="Search assigned modules"
    )

    filtered = search(
        workloads,
        context["search_query"],
        WORKLOAD_SEARCH_FIELDS
    )

    context.update({
        "workloads": filtered,
        "total_count": workloads.count(),
        "result_count": filtered.count(),
        "form": form,
    })

    return render(
        request,
        "workload/assignment.html",
        context
    )



# ==================================================
# WORKLOAD LIST
# ==================================================
@login_required
@admin_required
def workload_list(request):

    workloads = Workload.objects.select_related(
        *BASE_RELATED
    ).order_by("-id")

    workloads.refresh_statuses()

    context = search_context(
        request,
        placeholder="Search by course, lecturer, cohort or status"
    )

    filtered = search(
        workloads,
        context["search_query"],
        WORKLOAD_SEARCH_FIELDS
    )

    context.update({
        "workloads": filtered,
        "total_count": workloads.count(),
        "result_count": filtered.count(),
    })

    return render(
        request,
        "workload/workload_list.html",
        context
    )



# ==================================================
# WORKLOAD DETAIL
# ==================================================
@login_required
@admin_required
def workload_detail(request, pk):

    workload = get_object_or_404(
        Workload.objects.select_related(*BASE_RELATED),
        pk=pk
    )


    return render(
        request,
        "workload/workload_detail.html",
        {
            "workload": workload,
            "missed_holidays": workload.missed_holidays(),
        }
    )



# ==================================================
# UPDATE WORKLOAD
# ==================================================
@login_required
@admin_required
def workload_update(request, pk):

    workload = get_object_or_404(
        Workload,
        pk=pk
    )


    if request.method == "POST":

        form = WorkloadForm(
            request.POST,
            instance=workload
        )


        if form.is_valid():

            workload = form.save()

            messages.success(
                request,
                "Workload updated successfully."
            )

            # An edit moves real class dates, so the same people
            # are told again -- with wording that makes clear it
            # is a change, not a new assignment.
            announce(request, workload, created=False)


            return redirect(
                "workload:workload_detail",
                pk=pk
            )


        messages.error(
            request,
            "Nothing was changed. Please correct the errors below."
        )


    else:

        form = WorkloadForm(
            instance=workload
        )


    return render(
        request,
        "workload/workload_form.html",
        {
            "form": form,
            "title": "Update Workload",
            "workload": workload
        }
    )



# ==================================================
# DELETE WORKLOAD
# ==================================================
@login_required
@admin_required
def workload_delete(request, pk):

    workload = get_object_or_404(
        Workload,
        pk=pk
    )


    if request.method == "POST":

        workload.delete()

        messages.success(
            request,
            "Workload deleted successfully."
        )

        return redirect(
            "workload:workload_list"
        )



    return render(
        request,
        "workload/workload_confirm_delete.html",
        {
            "workload": workload
        }
    )


# Printable lecturer workload. Scoped to the lecturer first,
# then narrowed by period.
@login_required
@lecturer_required
def lecturer_workload_print(request):

    lecturer = resolve_lecturer(request.user)

    if lecturer:

        workloads = workloads_for_lecturer(
            lecturer
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    periods = periods_for(workloads)

    workloads, selected_period = apply_period_filter(
        workloads,
        request.GET.get("period")
    )

    workloads = list(workloads)

    missed_any = [
        (w, w.missed_holidays())
        for w in workloads
        if w.missed_holidays()
    ]


    return render(
        request,
        "print/lecturer_workload.html",
        {
            "lecturer": lecturer,
            "workloads": workloads,
            "periods": periods,
            "selected_period": selected_period,
            "total_hours": sum(w.hours or 0 for w in workloads),
            "total_sessions": sum(w.total_classes() for w in workloads),
            "missed_any": missed_any,
            "generated_at": timezone.localtime(),
        }
    )



# ==================================================
# PRINTABLE: COHORT ACADEMIC CALENDAR
# ==================================================
@login_required
@representative_required
def representative_calendar_print(request):

    cohort = resolve_cohort(request.user)

    if cohort:

        workloads = Workload.objects.filter(
            cohort=cohort
        ).select_related(
            *BASE_RELATED
        ).order_by("start_date")

        workloads.refresh_statuses()

    else:

        workloads = Workload.objects.none()


    periods = periods_for(workloads)

    workloads, selected_period = apply_period_filter(
        workloads,
        request.GET.get("period")
    )

    workloads = list(workloads)

    calendar_start = workloads[0].start_date if workloads else None

    calendar_end = max(
        (w.end_date for w in workloads if w.end_date),
        default=None
    )


    return render(
        request,
        "print/cohort_calendar.html",
        {
            "cohort": cohort,
            "workloads": workloads,
            "periods": periods,
            "selected_period": selected_period,
            "calendar_start": calendar_start,
            "calendar_end": calendar_end,
            "holidays": holidays_between(
                calendar_start,
                calendar_end,
                workloads
            ),
            "generated_at": timezone.localtime(),
        }
    )
