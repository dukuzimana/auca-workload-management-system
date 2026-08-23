import csv

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from django.db.models import Sum

from accounts.decorators import admin_required

from workload.models import Workload

from .forms import WorkloadReportFilterForm


BASE_RELATED = (
    "course",
    "course__program",
    "course__program__faculty",
    "lecturer",
    "cohort",
    "cohort__program",
    "academic_period",
)


# ==================================================
# FILTERING
# ==================================================

def filtered_workloads(request):
    """
    Apply the report filter form to the full workload table.

    Returns (form, queryset, applied) where "applied" is a list
    of (label, value) pairs describing the active filters, so a
    printed report states the criteria it was built from.
    """

    workloads = Workload.objects.select_related(
        *BASE_RELATED
    ).order_by(
        "academic_period",
        "cohort",
        "start_date",
    )

    workloads.refresh_statuses()

    form = WorkloadReportFilterForm(request.GET or None)

    applied = []

    if form.is_valid():

        lookups = [
            ("academic_period", "academic_period", "Academic period"),
            ("faculty", "course__program__faculty", "Faculty"),
            ("program", "course__program", "Programme"),
            ("lecturer", "lecturer", "Lecturer"),
            ("cohort", "cohort", "Cohort"),
            ("status", "status", "Status"),
        ]

        for field, lookup, label in lookups:

            value = form.cleaned_data.get(field)

            if value:

                workloads = workloads.filter(**{lookup: value})

                applied.append((label, str(value)))

    return form, workloads, applied


# ==================================================
# INTERACTIVE REPORT
# ==================================================

@login_required
@admin_required
def workload_report(request):

    form, workloads, applied = filtered_workloads(request)

    context = {

        "form": form,
        "workloads": workloads,
        "applied": applied,
        "query_string": request.GET.urlencode(),

        "total_courses": workloads.values("course").distinct().count(),
        "total_lecturers": workloads.values("lecturer").distinct().count(),
        "total_cohorts": workloads.values("cohort").distinct().count(),

        "total_hours": workloads.aggregate(
            total=Sum("hours")
        )["total"] or 0,

        "workload_count": workloads.count(),
    }

    return render(
        request,
        "reports/workload_report.html",
        context
    )


# ==================================================
# PRINTABLE REPORT
# ==================================================

@login_required
@admin_required
def workload_report_print(request):

    form, workloads, applied = filtered_workloads(request)

    workloads = list(workloads)

    return render(
        request,
        "print/admin_report.html",
        {
            "workloads": workloads,
            "applied": applied,
            "query_string": request.GET.urlencode(),
            "total_hours": sum(w.hours or 0 for w in workloads),
            "total_sessions": sum(w.total_classes() for w in workloads),
            "total_lecturers": len({w.lecturer_id for w in workloads}),
            "total_cohorts": len({w.cohort_id for w in workloads}),
            "total_courses": len({w.course_id for w in workloads}),
            "generated_at": timezone.localtime(),
        }
    )


# ==================================================
# CSV EXPORT
# ==================================================

@login_required
@admin_required
def workload_report_csv(request):

    form, workloads, applied = filtered_workloads(request)

    stamp = timezone.localdate().isoformat()

    response = HttpResponse(content_type="text/csv")

    response["Content-Disposition"] = (
        f'attachment; filename="auca-workload-{stamp}.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Academic year",
        "Semester",
        "Cohort",
        "Programme",
        "Course code",
        "Course name",
        "Credits",
        "Lecturer",
        "Employment status",
        "Teaching days",
        "Start date",
        "End date",
        "Credit hours",
        "Sittings",
        "Status",
    ])

    for w in workloads:

        writer.writerow([
            w.academic_period.academic_year,
            w.academic_period.semester,
            w.cohort.name,
            w.cohort.program.name if w.cohort.program_id else "",
            w.course.code,
            w.course.name,
            w.course.credits,
            w.lecturer.name,
            w.lecturer.employment_status,
            w.course_days,
            w.start_date.isoformat() if w.start_date else "",
            w.end_date.isoformat() if w.end_date else "",
            w.hours or 0,
            w.total_classes(),
            w.status,
        ])

    return response
