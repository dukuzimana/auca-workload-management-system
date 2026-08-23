# Teaching schedule generation: a block of consecutive weeks on
# fixed weekdays, skipping public holidays.


from datetime import timedelta

import holidays

from academics.models import Holiday


rw_holidays = holidays.Rwanda()


# ==========================================================
# CONFIGURATION
# ==========================================================

# How many weeks a module runs, by credit value.
WEEKS_BY_CREDITS = {
    3: 4,
    4: 5,
}

# Used when a course has a credit value not listed above.
DEFAULT_DURATION_WEEKS = 4

# Notional teaching hours per credit (3 credits = 45 hours).
HOURS_PER_CREDIT = 15

# Stops the date walk running away if every candidate day is
# somehow excluded. Two years is far beyond any real module.
MAX_SEARCH_DAYS = 730


DAYS_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


# The same thing the other way round, for turning the stored
# indexes back into names to display. Derived from DAYS_MAP
# rather than typed out again, so the two cannot drift.
DAY_NAMES = {
    index: name for name, index in DAYS_MAP.items()
}


# ==========================================================
# HELPERS
# ==========================================================

def parse_course_days(days_per_week):
    """
    Turn "Sunday, Thursday" into [3, 6].

    Accepts any capitalisation and ignores empty entries.
    Raises ValueError on an unrecognised day name.
    """

    selected_days = []

    for raw_day in (days_per_week or "").split(","):

        day = raw_day.strip().title()

        if not day:
            continue

        if day not in DAYS_MAP:
            raise ValueError(
                f"'{raw_day.strip()}' is not a valid day name. "
                "Use full English day names, e.g. Sunday,Thursday."
            )

        index = DAYS_MAP[day]

        if index not in selected_days:
            selected_days.append(index)

    return sorted(selected_days)


def duration_weeks_for(credits):
    """Weeks a module of this credit value runs for."""

    return WEEKS_BY_CREDITS.get(
        credits,
        DEFAULT_DURATION_WEEKS
    )


def notional_hours_for(credits):
    """
    Official teaching hours recorded against a module.

    This is the credit-hour figure the faculty already uses in
    its workload spreadsheet: 3 credits = 45, 4 credits = 60.
    It is deliberately NOT the number of sittings, which is
    available separately via Workload.total_classes().
    """

    return (credits or 0) * HOURS_PER_CREDIT


# ==========================================================
# SCHEDULE GENERATION
# ==========================================================

def generate_course_schedule(
        start_date,
        credits,
        days_per_week,
        weeks=None
):
    """
    Return the list of dates a module is actually taught on.

    Public holidays are skipped and the block extends to keep
    the number of sittings constant.

    "weeks" overrides the block length implied by the credit
    value. It is used for modules that run for a whole term
    irrespective of their credits, such as Internship and
    Thesis. A value of None, 0 or less falls back to the
    credit-based length.
    """

    selected_days = parse_course_days(days_per_week)

    if not start_date or not selected_days:
        return []

    block_weeks = (
        weeks
        if weeks and weeks > 0
        else duration_weeks_for(credits)
    )

    total_sessions = (
        block_weeks
        *
        len(selected_days)
    )

    if total_sessions <= 0:
        return []

    # Pull administrator-entered holidays once rather than
    # querying the database for every candidate date.
    custom_holidays = set(
        Holiday.objects.values_list(
            "date",
            flat=True
        )
    )

    teaching_days = []

    current_date = start_date

    days_searched = 0

    while (
        len(teaching_days) < total_sessions
        and days_searched < MAX_SEARCH_DAYS
    ):

        if current_date.weekday() in selected_days:

            if (
                current_date not in rw_holidays
                and current_date not in custom_holidays
            ):

                teaching_days.append(current_date)

        current_date += timedelta(days=1)

        days_searched += 1

    return teaching_days


def excluded_holidays(
        start_date,
        end_date,
        days_per_week
):
    """
    Holidays that fell on a teaching weekday inside a module's
    span, i.e. the sittings that were lost and made up later.

    Returned as a list of (date, name) tuples so the calendar
    can explain why a block runs longer than its nominal weeks.
    """

    if not start_date or not end_date:
        return []

    try:
        selected_days = parse_course_days(days_per_week)
    except ValueError:
        return []

    if not selected_days:
        return []

    custom_holidays = dict(
        Holiday.objects.values_list(
            "date",
            "name"
        )
    )

    missed = []

    current_date = start_date

    while current_date <= end_date:

        if current_date.weekday() in selected_days:

            if current_date in custom_holidays:

                missed.append(
                    (current_date, custom_holidays[current_date])
                )

            elif current_date in rw_holidays:

                missed.append(
                    (current_date, rw_holidays.get(current_date))
                )

        current_date += timedelta(days=1)

    return missed


def holidays_between(start_date, end_date, workloads=None):
    """
    Every public holiday falling inside a date span.

    Each entry carries a "clashes" flag: True when the holiday
    lands on a weekday one of the given modules teaches on, so
    the printed calendar can distinguish a holiday that costs a
    class from one that falls on a day nobody was in anyway.
    """

    if not start_date or not end_date or end_date < start_date:
        return []

    custom_holidays = dict(
        Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
        ).values_list("date", "name")
    )

    # Weekday -> the modules that teach on it, with their spans.
    spans = []

    for workload in (workloads or []):

        try:
            weekdays = parse_course_days(workload.course_days)
        except ValueError:
            continue

        if workload.start_date and workload.end_date:
            spans.append(
                (workload.start_date, workload.end_date, set(weekdays))
            )

    def clashes(day):
        return any(
            begin <= day <= finish and day.weekday() in weekdays
            for begin, finish, weekdays in spans
        )

    found = []

    current_date = start_date

    while current_date <= end_date:

        name = custom_holidays.get(current_date)

        if name is None and current_date in rw_holidays:
            name = rw_holidays.get(current_date)

        if name:
            found.append({
                "date": current_date,
                "name": name,
                "clashes": clashes(current_date),
            })

        current_date += timedelta(days=1)

    return found
