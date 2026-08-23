# Shared search helper for the list screens.
#
#     query = get_query(request)
#     rows = search(qs, query, LECTURER_SEARCH_FIELDS)

from django.db.models import Q


def get_query(request, param="q"):
    """
    The search term from the query string, trimmed.

    Returns "" when absent or blank, so a stray "?q=" or a
    box submitted with only spaces behaves as no search at
    all rather than filtering everything away.
    """
    return (request.GET.get(param) or "").strip()


def search(queryset, query, fields):
    """
    Narrow a queryset to rows matching `query` in any of `fields`.

    `fields` are ORM lookup paths, so related columns work:
    "lecturer__name", "course__code". Each term in a multi-word
    query must match somewhere in the row, which makes
    "kumar networks" find Kumar's networking module rather than
    every row mentioning either word.

    An empty query returns the queryset untouched.
    """
    if not query or not fields:
        return queryset

    for term in query.split():
        matches = Q()

        for field in fields:
            matches |= Q(**{f"{field}__icontains": term})

        queryset = queryset.filter(matches)

    return queryset.distinct()


def search_context(request, param="q", placeholder="Search..."):
    """
    Context entries the shared search box template expects.

    Merge into a view's context alongside the filtered
    queryset:

        context = {"lecturers": lecturers}
        context.update(search_context(request, placeholder="Search lecturers"))
    """
    query = get_query(request, param)

    return {
        "search_query": query,
        "search_param": param,
        "search_placeholder": placeholder,
        "is_searching": bool(query),
    }


# Field sets, so a model is searched the same way wherever it
# is listed.

USER_SEARCH_FIELDS = (
    "username",
    "email",
    "first_name",
    "last_name",
    "role",
)

LECTURER_SEARCH_FIELDS = (
    "name",
    "qualification",
    "employment_status",
    "user__username",
    "user__email",
)

FACULTY_SEARCH_FIELDS = (
    "name",
    "description",
)

PROGRAM_SEARCH_FIELDS = (
    "name",
    "faculty__name",
)

COHORT_SEARCH_FIELDS = (
    "name",
    "program__name",
    "program__faculty__name",
    "intake_year",
    "representative__username",
)

COURSE_SEARCH_FIELDS = (
    "code",
    "name",
    "level",
    "program__name",
    "program__faculty__name",
)

PERIOD_SEARCH_FIELDS = (
    "academic_year",
    "semester",
    "teaching_period",
)

HOLIDAY_SEARCH_FIELDS = (
    "name",
    "date",
)

WORKLOAD_SEARCH_FIELDS = (
    "course__code",
    "course__name",
    "lecturer__name",
    "cohort__name",
    "cohort__program__name",
    "academic_period__academic_year",
    "academic_period__semester",
    "status",
    "course_days",
)

# A lecturer searching their own workload already knows who
# the lecturer is; searching by their own name is noise.
OWN_WORKLOAD_SEARCH_FIELDS = (
    "course__code",
    "course__name",
    "cohort__name",
    "cohort__program__name",
    "academic_period__academic_year",
    "academic_period__semester",
    "status",
    "course_days",
)

# A representative's calendar is one cohort, so the cohort
# name is likewise not worth searching.
COHORT_WORKLOAD_SEARCH_FIELDS = (
    "course__code",
    "course__name",
    "lecturer__name",
    "academic_period__academic_year",
    "academic_period__semester",
    "status",
    "course_days",
)
