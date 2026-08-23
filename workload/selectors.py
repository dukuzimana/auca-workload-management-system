# Role resolution.
#
# A person is linked to their record in exactly one place:
#   Lecturer : academics.Lecturer.user
#   Cohort   : academics.Cohort.representative

from django.db.models import Q

from academics.models import Lecturer, Cohort


def is_admin(user):
    """
    True for administrators.

    Checked as "superuser OR role == admin" to match
    accounts.decorators.admin_required. Testing is_superuser
    alone locks out administrators created through the user
    management screens, who have role="admin" but no superuser
    flag.
    """

    return bool(
        user.is_superuser
        or getattr(user, "role", None) == "admin"
    )


def resolve_lecturer(user):
    """Lecturer record for this user, or None."""

    return Lecturer.objects.filter(
        user=user
    ).first()


def resolve_cohort(user):
    """Cohort this user represents, or None."""

    return Cohort.objects.filter(
        representative=user
    ).select_related(
        "program"
    ).first()


# The same lookups in reverse: given a record, which login
# should be emailed? None means no account is linked.

def account_for_lecturer(lecturer):
    """The login attached to a lecturer record, or None."""

    if lecturer is None:
        return None

    return lecturer.user if lecturer.user_id else None


def account_for_cohort(cohort):
    """The class representative's login for a cohort, or None."""

    if cohort is None:
        return None

    return cohort.representative if cohort.representative_id else None


# ==========================================================
# WORKLOADS FOR A LECTURER
# ==========================================================

def workloads_for_lecturer(lecturer, queryset=None):
    """
    Every workload this lecturer teaches, led or co-taught.

    Filtering on the lecturer column alone hides co-taught
    modules from the person named second in the spreadsheet
    cell, so both the lead column and the co-lecturer table
    are matched. distinct() is required: without it a lecturer
    who is somehow both would appear twice.
    """

    from .models import Workload

    if lecturer is None:
        return (queryset if queryset is not None else Workload.objects).none()

    base = queryset if queryset is not None else Workload.objects.all()

    return base.filter(
        Q(lecturer=lecturer) | Q(co_lecturers=lecturer)
    ).distinct()


# ==========================================================
# PERIOD FILTERING
# ==========================================================

from academics.models import AcademicPeriod


def periods_for(workloads):
    """
    Academic periods that actually appear in this queryset.

    The period dropdown on a print screen should only offer
    periods the person has something in, not every period in
    the institution.
    """

    period_ids = workloads.values_list(
        "academic_period_id",
        flat=True
    ).distinct()

    return AcademicPeriod.objects.filter(
        id__in=list(period_ids)
    ).order_by(
        "-academic_year",
        "semester",
    )


def apply_period_filter(workloads, period_id):
    """
    Narrow a workload queryset to one academic period.

    Returns (queryset, selected_period). An absent, blank or
    unknown period id leaves the queryset untouched, so a
    tampered query string cannot widen what the user sees --
    the queryset was already scoped to them by the caller.
    """

    if not period_id:
        return workloads, None

    period = AcademicPeriod.objects.filter(
        pk=period_id
    ).first()

    if not period:
        return workloads, None

    return workloads.filter(academic_period=period), period
