# Assignment notifications: emails the lecturer and the class
# representative when a workload is assigned or updated.


import logging

from dataclasses import dataclass, field

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .selectors import account_for_cohort, account_for_lecturer


logger = logging.getLogger(__name__)


# ==========================================================
# RESULT
# ==========================================================

@dataclass
class Recipient:
    """One person the notification was meant for."""

    role: str
    name: str
    email: str = ""
    reason: str = ""


@dataclass
class NotificationResult:
    """What happened when the emails went out."""

    sent: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    failed: list = field(default_factory=list)

    def summary(self):
        """One sentence an administrator can act on."""

        parts = []

        if self.sent:
            parts.append(
                "Notified "
                + ", ".join(
                    f"{r.name} ({r.email})" for r in self.sent
                )
                + "."
            )

        if self.skipped:
            parts.append(
                "Not notified: "
                + "; ".join(
                    f"{r.name} -- {r.reason}" for r in self.skipped
                )
                + "."
            )

        if self.failed:
            parts.append(
                "Delivery failed for "
                + "; ".join(
                    f"{r.name} ({r.email}) -- {r.reason}"
                    for r in self.failed
                )
                + "."
            )

        return " ".join(parts)

    @property
    def all_delivered(self):
        return bool(self.sent) and not (self.skipped or self.failed)


# ==========================================================
# LINKS
# ==========================================================

def _absolute(path, request=None):
    """
    Turn a path into a URL that works inside an email client.

    A relative link is useless in an email, and request is not
    available when the assignment is made from a management
    command or the Django admin. SITE_URL covers that case.
    """

    if request is not None:
        return request.build_absolute_uri(path)

    base = getattr(settings, "SITE_URL", "") or ""

    return f"{base.rstrip('/')}{path}"


def _destination_for(role):
    """The screen this role should land on."""

    if role == "lecturer":
        return reverse("workload:lecturer_dashboard")

    return reverse("workload:representative_dashboard")


def links_for(role, request=None):
    """
    Where the recipient is sent.

    Two links, because the recipient may or may not already
    have a session. "dashboard" is their own screen; "login"
    carries the same destination in ?next= so signing in lands
    them there rather than on a generic home page.
    """

    destination = _destination_for(role)

    login = f"{reverse('accounts:login')}?next={destination}"

    return {
        "dashboard_url": _absolute(destination, request),
        "login_url": _absolute(login, request),
    }


# ==========================================================
# CONTEXT
# ==========================================================

def build_context(workload, role, request=None, created=True):
    """
    Everything the email says about one assignment.

    Read once here so the text and HTML bodies cannot drift
    apart, and so the schedule is evaluated a single time.
    """

    schedule = [
        timezone.datetime.strptime(day, "%Y-%m-%d").date()
        if isinstance(day, str) else day
        for day in (workload.generated_schedule or [])
    ]

    context = {
        "workload": workload,
        "role": role,
        "created": created,

        "course": workload.course,
        "cohort": workload.cohort,
        "program": workload.cohort.program,
        "faculty": workload.cohort.program.faculty,
        "period": workload.academic_period,

        "lecturer": workload.lecturer,
        "teaching_team": workload.teaching_team(),
        "teaching_team_names": workload.teaching_team_names(),

        "schedule": schedule,
        "first_class": schedule[0] if schedule else None,
        "last_class": schedule[-1] if schedule else None,
        "total_classes": len(schedule),
        "missed_holidays": workload.missed_holidays(),

        "site_name": getattr(
            settings,
            "SITE_NAME",
            "AUCA Workload Management System"
        ),

        "generated_at": timezone.localtime(),
    }

    context.update(links_for(role, request))

    return context


def build_subject(context):
    """
    Subject line.

    Rendered from a template and flattened, because a newline
    in a subject header is a header-injection vector.
    """

    subject = render_to_string(
        "email/workload_assigned_subject.txt",
        context
    )

    return " ".join(subject.split())


# ==========================================================
# RECIPIENTS
# ==========================================================

def resolve_recipients(workload):
    """
    Who should be told, and who could not be.

    Everyone on the teaching team is included, not just the
    lead, so a co-lecturer is not left to find out from
    someone else. Anyone without a login or without an email
    address on it is returned as skipped with the reason,
    which is what the administrator needs in order to fix it.
    """

    found = []

    skipped = []

    seen_emails = set()

    # ---- Teaching team ----

    for lecturer in workload.teaching_team():

        account = account_for_lecturer(lecturer)

        if account is None:

            skipped.append(Recipient(
                role="lecturer",
                name=lecturer.name,
                reason="no user account is linked to this lecturer record"
            ))

            continue

        if not account.email:

            skipped.append(Recipient(
                role="lecturer",
                name=lecturer.name,
                reason=f"the account '{account.username}' has no email address"
            ))

            continue

        if account.email.lower() in seen_emails:
            continue

        seen_emails.add(account.email.lower())

        found.append(Recipient(
            role="lecturer",
            name=lecturer.name,
            email=account.email
        ))

    # ---- Class representative ----

    representative = account_for_cohort(workload.cohort)

    if representative is None:

        skipped.append(Recipient(
            role="representative",
            name=f"{workload.cohort.name} representative",
            reason="this cohort has no class representative linked"
        ))

    elif not representative.email:

        skipped.append(Recipient(
            role="representative",
            name=representative.get_full_name() or representative.username,
            reason=f"the account '{representative.username}' has no email address"
        ))

    elif representative.email.lower() not in seen_emails:

        seen_emails.add(representative.email.lower())

        found.append(Recipient(
            role="representative",
            name=representative.get_full_name() or representative.username,
            email=representative.email
        ))

    return found, skipped


# ==========================================================
# SENDING
# ==========================================================

def notify_assignment(workload, request=None, created=True):
    """
    Email the teaching team and the class representative.

    Returns a NotificationResult. Never raises: the workload is
    already saved when this is called, and losing the save
    because a mail server was unreachable would be the worse
    failure. Problems are reported back to the caller and
    logged.
    """

    result = NotificationResult()

    recipients, skipped = resolve_recipients(workload)

    result.skipped.extend(skipped)

    if not recipients:
        return result

    # One connection for both emails rather than one each.
    try:
        connection = get_connection()
        connection.open()

    except Exception as error:

        logger.exception(
            "Could not open a mail connection for workload %s",
            workload.pk
        )

        for recipient in recipients:
            recipient.reason = str(error) or error.__class__.__name__
            result.failed.append(recipient)

        return result

    try:

        for recipient in recipients:

            context = build_context(
                workload,
                recipient.role,
                request=request,
                created=created
            )

            context["recipient"] = recipient

            html_body = render_to_string(
                "email/workload_assigned.html",
                context
            )

            text_body = render_to_string(
                "email/workload_assigned.txt",
                context
            )

            message = EmailMultiAlternatives(
                subject=build_subject(context),
                body=text_body or strip_tags(html_body),
                from_email=getattr(
                    settings,
                    "DEFAULT_FROM_EMAIL",
                    None
                ),
                to=[recipient.email],
                connection=connection,
            )

            message.attach_alternative(html_body, "text/html")

            try:
                message.send(fail_silently=False)

                result.sent.append(recipient)

            except Exception as error:

                logger.exception(
                    "Could not email %s about workload %s",
                    recipient.email,
                    workload.pk
                )

                recipient.reason = (
                    str(error) or error.__class__.__name__
                )

                result.failed.append(recipient)

    finally:

        try:
            connection.close()
        except Exception:
            pass

    return result


# ==========================================================
# REPORTING TO THE ADMINISTRATOR
# ==========================================================

def report(request, result):
    """
    Put the outcome of a send on screen.

    This lives here rather than in a view because two screens
    assign workloads -- the app's own assignment form and the
    Django admin, which the sidebar links to as "Workload
    Assignment". Two copies of this wording would drift, and
    the drift would be invisible until an administrator on one
    screen was told less than an administrator on the other.

    The success message for the save is deliberately kept
    separate from this one by the callers. "Assigned
    successfully" is true even when nobody could be emailed,
    and running the two together would let a silent
    non-delivery hide behind a green tick.
    """

    if request is None:
        return result

    if result.sent:

        # Being told "sent" when Django is only printing to the
        # server terminal is the single most misleading thing
        # this screen can say, so it says which it was.
        printed_only = (
            settings.EMAIL_BACKEND
            == "django.core.mail.backends.console.EmailBackend"
        )

        recipients = ", ".join(
            f"{r.name} ({r.email})" for r in result.sent
        )

        if printed_only:

            messages.warning(
                request,
                f"Notification for {recipients} was written to the "
                f"server console, NOT delivered: no mail server is "
                f"configured. Set EMAIL_HOST to send real email, "
                f"then check it with: python manage.py check_email"
            )

        else:

            messages.info(
                request,
                f"Notification sent to {recipients}."
            )

    for recipient in result.skipped:

        messages.warning(
            request,
            f"{recipient.name} was not notified: {recipient.reason}."
        )

    for recipient in result.failed:

        messages.error(
            request,
            f"The email to {recipient.name} ({recipient.email}) "
            f"could not be delivered: {recipient.reason}. "
            "The assignment itself was saved."
        )

    if not (result.sent or result.skipped or result.failed):

        messages.warning(
            request,
            "No one could be notified about this assignment."
        )

    return result
