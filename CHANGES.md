# AUCA Workload Management System — completion notes

Goal: every lecturer sees their own workload, and every class
representative sees their own cohort's academic calendar.

## The blocker

`workload/__init__.py` did not exist. Python therefore did not treat
`workload/` as a package, so `INSTALLED_APPS` could not import it and
the project would not start at all. Adding the empty file fixes it.

## Bugs fixed

| # | Problem | Effect | Fix |
|---|---------|--------|-----|
| 1 | `workload/__init__.py` missing | Project would not boot | File added |
| 2 | Four templates used `{% url 'workload_list' %}` etc. without the `workload:` namespace | `NoReverseMatch` 500 on the workload list, detail, edit and delete pages | Namespaced the tags |
| 3 | `lecturer_calendar` branched on `request.user.is_superuser` alone | The only admin account (`Dismas`, `role="admin"`, not a superuser) saw an **empty** calendar | Role check is now "superuser OR role == admin", shared via `selectors.is_admin` |
| 4 | `status` is stored but only recalculated on save | A module that finished months ago still read "Upcoming"; the Ongoing/Completed counters were wrong | `Workload.objects.refresh_statuses()`, called by each dashboard, plus a `refresh_workload_status` command for cron |
| 5 | `hours` stored the number of sittings (8) but the UI labels it "Total Hours" | Reports totalled sittings, not hours | `hours` is now credit hours (3 credits = 45, 4 = 60), matching the faculty spreadsheet. Sittings remain on `total_classes()` |
| 6 | `generate_course_schedule` raised `ValueError` for any credit value other than 3 or 4 | Adding a 2- or 6-credit course crashed the assignment form | Unlisted credit values fall back to a 4-week block |
| 7 | An invalid day name raised `KeyError` | 500 on save from the admin (the source spreadsheet contains "Thusday" and "SUNDAY") | Day parsing is case-insensitive and raises a clear `ValueError` |
| 8 | Lecturers were resolved only via `Lecturer.user`, representatives only via `Cohort.representative` | Anyone linked through the "Lecturer Assignments" / "Representative Assignments" screens saw nothing | Both linkage paths are checked (`workload/selectors.py`) |
| 9 | `lecturer_calendar` had no role guard | A representative got a silent empty calendar | Guarded; one entry point routes by role |
| 10 | `TIME_ZONE = 'UTC'` | Between 00:00 and 02:00 in Kigali "today's class" was computed against the previous day | `Africa/Kigali` |
| 11 | The `reports` app was never included in `config/urls.py` | `/reports/workload-report/` was unreachable | Wired in under the `reports` namespace |
| 12 | One database query per candidate date when checking holidays | Slow schedule generation | Holidays are loaded once per generation |

## What was already correct

The holiday engine was sound and is unchanged in behaviour: it skips
public holidays and extends the block so a module always delivers the
same number of sittings. The `holidays` package's Rwandan dates were
verified against the 2026 calendar (Eid al-Fitr 20 March, Good Friday
3 April, Easter Monday 6 April, Eid al-Adha 27 May) and are correct.
Administrator-entered holidays in `academics.Holiday` are honoured too.

## New files

- `workload/__init__.py`
- `workload/selectors.py` — role resolution
- `workload/management/commands/refresh_workload_status.py`
- `workload/migrations/0005_alter_workload_hours.py`
- `workload/tests.py` — 25 tests
- `requirements.txt`

## Running

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py test workload
    python manage.py runserver

Schedule daily so statuses stay right without anyone opening a page:

    python manage.py refresh_workload_status

## Still open

- `academic_calendar` duplicates `academics.Holiday`. Only the
  `academics` one is used; the other app has no rows and no UI. Worth
  deleting once you are sure nothing depends on it.
- `AcademicPeriod` has no cohort field, so two cohorts cannot both
  have their own "Semester 2, 2025/2026" with different dates. The
  per-cohort calendar works because `Workload` carries both `cohort`
  and `academic_period`, but the period dates themselves are shared.
- `ALLOWED_HOSTS` is empty and `DEBUG = True` — fine for development,
  must change before deployment.

---

# Printing and reporting

## How printing works

There is no PDF library in the project and none was added. WeasyPrint
needs Cairo and Pango, and xhtml2pdf needs ReportLab — both are awkward
to install on Windows and would have broken your existing virtualenv.

Instead the print screens are real HTML pages with an A4 `@media print`
stylesheet. "Print / Save as PDF" calls `window.print()`; every browser
offers **Save as PDF** in that dialog, which produces a proper PDF with
selectable text. Adding `?auto=1` to any print URL opens the dialog
automatically, which is handy for a "print" link elsewhere in the UI.

The toolbar and the site sidebar are marked `.no-print` and disappear on
paper. Table headers repeat across pages and rows are not split.

## Lecturer — print own workload by period

`/workload/lecturer-workload/print/`

- Period dropdown at the top; picking one reloads the sheet.
- The dropdown only lists periods the lecturer actually teaches in.
- Sheet shows: letterhead, lecturer details, module table with credit
  hours and a total, every class date per module, any holidays that
  displaced a sitting, and signature blocks for lecturer, HoD and Dean.
- Reachable from "Print my workload" on the dashboard and the sidebar.

## Class representative — print cohort academic calendar

`/workload/representative-calendar/print/`

- Same period dropdown, scoped to that cohort's periods.
- Sheet shows: cohort and programme, calendar span, module table with
  lecturer names, all class dates per module, and a table of public
  holidays in the span. Each holiday is marked as either costing a class
  or falling on a non-teaching day.
- Signature blocks for the representative and the programme coordinator.

## Administrator — filtered reports

`/reports/workload-report/`

`templates/reports/workload_report.html` and
`templates/reports/workload_report_pdf.html` were both zero-byte files,
so this page rendered blank. The interactive page is now built out:

- Filter by academic period, faculty, programme, lecturer, cohort and
  status, in any combination (the form already existed in
  `reports/forms.py` and was unused).
- Summary tiles: assignments, courses, lecturers, cohorts, credit hours.
- Two export buttons that carry the current filters through:
  - **Print / Save as PDF** → `/reports/workload-report/print/`,
    landscape A4, and it prints the criteria it was built from so a
    filtered report is not mistaken for a complete one.
  - **Export CSV** → `/reports/workload-report/csv/`, fifteen columns,
    opens directly in Excel.

The empty `workload_report_pdf.html` placeholder is now unused; the
print layout lives in `templates/print/`.

## Scoping

Filtering never widens what someone can see. Each print view scopes the
queryset to the signed-in person **first** and only then narrows it by
the period in the query string; an unknown or tampered period id is
ignored rather than obeyed. Every print and export route carries the
same role decorator as its screen equivalent, so a lecturer cannot open
a cohort calendar or an admin report, and a representative cannot open a
lecturer's workload. There are tests for each of these.

## New files

- `templates/print/base_print.html` — shared A4 layout and print CSS
- `templates/print/lecturer_workload.html`
- `templates/print/cohort_calendar.html`
- `templates/print/admin_report.html`
- `templates/reports/workload_report.html` — was empty

## Tests

41 in total, 16 of them covering printing and reporting: period
filtering, dropdown scoping, credit-hour totals, holiday clash
detection, CSV contents, and the cross-role access rules.


---

# Lecturer accounts and search

## The lecturer account fault

Four separate faults were stacked on top of each other. The visible
symptom was that the **Lecturer Accounts** screen read
"No lecturer assignments available" while all ten lecturers had
working logins.

| # | Problem | Effect | Fix |
|---|---------|--------|-----|
| 1 | `accounts_lectureraccountassignment` was empty while all ten lecturers were linked through `academics_lecturer.user` | The screen reads the assignment table, so it looked as though nothing was configured | Data migration `accounts/0004` creates the missing rows from the links that already exist |
| 2 | `LecturerAccountAssignmentForm.clean()` checked only the assignment table, never `Lecturer.user` | Adding the missing link by hand passed validation, then died on `UNIQUE constraint failed: academics_lecturer.user_id` — a 500 page | Both one-to-one columns are validated, and conflicts are reported as field errors naming the person already holding the link |
| 3 | The view saved the assignment row first and set `Lecturer.user` afterwards | When the second write failed the first survived, leaving a row claiming a link the lecturer did not mirror; the two screens then disagreed about who owned the account | Both writes happen in one `@transaction.atomic` block inside the form's `save()` |
| 4 | `Lecturer.user` was `on_delete=CASCADE` | Deleting a **login** from the Users screen destroyed the academic record and every `Workload` row attached to it | `on_delete=SET_NULL` (migration `academics/0004`). Removing an account unlinks it; the lecturer and their workload survive |

Reproduced before fixing: deleting one lecturer login returned
`{'workload.Workload': 1, 'accounts.User': 1, 'academics.Lecturer': 1}`.

### Also fixed while in there

- `accounts/views.py` defined `delete_lecturer_assignment` and the
  entire representative CRUD **twice**. The duplicates are gone.
- The delete-user page passed the target into the context as `user`,
  which shadowed the signed-in administrator in `base.html` — opening
  "Delete" on a lecturer redrew the sidebar as that lecturer's menu.
  It is now `account`, and the page shows what the deletion touches
  before it happens.
- A role change that would strand a link (lecturer to representative
  while still linked) is refused with an explanation instead of
  silently orphaning the record.
- Deleting the last administrator, or the account you are signed in
  with, is refused. There was no way back in through the UI.
- Creating a lecturer or representative login now says that a link is
  the next step, rather than letting the person discover it when the
  new user reports an empty dashboard.
- Both assignment screens list **accounts with no record** and
  **records with no account** side by side, so the situation that
  started all this is visible rather than silent.

## Search

`common/search.py` holds one helper used by every screen. Terms are
matched case-insensitively as substrings, across related tables, and
**every** term must match — "nizeyimana pacifique" finds the two
lecturers of that name rather than everyone matching either word.
A blank or whitespace-only `q` is treated as no search at all.

Search is a GET form, so a filtered list is a URL that can be
bookmarked, shared or reloaded. Any other query-string values already
on the page are preserved as hidden inputs, so searching does not drop
a period filter.

Added to sixteen screens:

- **Accounts** — users, lecturer accounts, representative accounts
- **Academics** — faculties, programmes, cohorts, courses, lecturers,
  academic periods, holidays
- **Workload** — workload list, assignment, master calendar
- **Lecturer** — dashboard, calendar
- **Representative** — dashboard, calendar

Two details worth knowing:

- On the dashboards the **summary tiles keep counting everything**
  while search narrows only the table underneath. A filtered tile
  reading "3 modules" looked as though the rest had been deleted.
- Search never widens scope. Each personal screen is scoped to the
  signed-in person first and searched second, so a lecturer typing
  another lecturer's module name gets nothing. There is a test for it.

Empty states are search-aware: a table emptied by a search says
nothing matched and offers to clear it, instead of "No users
available." implying the system has none.

## Files

New:

- `common/__init__.py`, `common/search.py`
- `templates/partials/search_box.html`
- `academics/migrations/0004_alter_lecturer_user.py`
- `accounts/migrations/0004_backfill_account_assignments.py`
- `accounts/tests.py` — 21 tests

Changed: `accounts/forms.py`, `accounts/views.py` (rewritten,
deduplicated), `academics/models.py`, `academics/views.py`,
`workload/views.py`, `templates/accounts/delete_user.html`,
`static/css/style.css`, and the sixteen list templates.

## Tests

**62 pass** — the original 41, plus 21 covering the account faults
above and search behaviour (blank and whitespace queries, multi-term
matching, related-field matching, scope containment, and that the box
renders on all eleven admin list screens).

    python manage.py migrate
    python manage.py test

## Note on running the migrations

`accounts/0004` writes the missing assignment rows and is safe to run
on a database that already has some — it skips anything already
linked. It is deliberately **not** reversible: telling apart the rows
it created from ones an administrator added by hand is guesswork, and
guessing wrong would unlink working accounts.


---

# Spreadsheet import, notification emails, and the Clear button

Three things were asked for: make the Clear button match the rest
of the app, load the faculty workbook into the system, and email
the lecturer and the class representative when an administrator
assigns a workload.

**125 tests pass** — the 62 that existed before, plus 63 new.

    python manage.py migrate
    python manage.py test

## The Clear button

`.search-box-clear` was a bare text link sitting immediately
beside the Search button, so the pair looked mismatched and
Clear read as body copy rather than an action. It now uses the
app's secondary-button treatment: the same padding, radius,
font weight and gap as `.admin-dashboard-btn`, in
`--auca-light` on `--auca-blue`.

The reports screen had its own grey `.btn-clear` in an inline
`<style>` block, off the AUCA palette and a different size
again. Both of its filter buttons now use the shared classes.

The inline "Clear the search" links inside empty-state
sentences were left alone. They sit mid-sentence — *Nothing
matches "x". Clear the search to see all 12.* — where a button
would be wrong.

## Loading the workbook

    python manage.py import_workload_excel path/to/file.xlsx

Options:

| Option | Effect |
|---|---|
| `--dry-run` | Reports what would happen, then rolls back |
| `--create-accounts` | Creates logins for lecturers and cohorts that have none |

`--dry-run` runs the real import inside a transaction and undoes
it at the end, so it exercises exactly the code a real run does
rather than a parallel "pretend" path that can drift.

The command is safe to run twice. Every object is matched before
it is created, so a second run reports "already present" instead
of building a duplicate set beside the first.

### What went in

| | Created | Already present |
|---|---|---|
| Workload assignments | 176 | 0 |
| Cohorts | 6 | 4 |
| Academic periods | 40 | 0 |
| Courses | 4 | 15 |
| Lecturers | 5 | 10 |
| Co-taught modules | 50 | — |

The ten lecturers and fifteen courses already entered by hand
were reused, not duplicated.

### What the spreadsheet needed

It is a working document, not an export. Everything below is
**reported at the end of the run**, never applied silently — an
import that quietly guesses is worse than one that refuses,
because there is no way to know afterwards which rows to check.

| Problem | What the import does |
|---|---|
| Dates in two formats: real datetimes and `D/M/YYYY - D/M/YYYY` text | Both read, day-first throughout |
| `13/10/203` and `15/4/3031` — mistyped years | Rebuilt from the year in the other half of the same cell |
| `../7/2026` — no usable day | Row skipped and listed; not guessed |
| `13/12/2026 - 13/3/2026` — ends before it starts | End year moved: that gives a three-month term, moving the start would give fifteen |
| "Thusday" (≈50 times), "SUNDAY", "Sunday Thusday" | Normalised to `Sunday,Thursday` |
| "All days" | Read as the full week |
| `MSDA 9233` used for two different courses | Courses match on **name**, not code. `Course.code` is unique, so trusting it would have collapsed two courses into one. Clashing codes get a suffix and are reported |
| "...Big Data Analytics third semester" in the programme cell | Trailing phrase stripped — keeping it created a second programme that five cohorts then hung off |
| "Dr. Fabrice" in the database, "Dr. Fabrice Sibomana" in the sheet | Matched as one person; the record takes the fuller name |
| "Dr. Pacifique Nizeyimana" vs "Nizeyimana Pacifique" | One record. Names compare with titles dropped and words sorted |
| Co-taught cells: "Dr. Eric Nizeyimana, Mr. david Hagumuwumva" | Split; first is the lead, the rest become co-lecturers |

### Two judgement calls that need your decision

Both are printed under **"Needs your confirmation"** every time
the import runs.

1. **Internship shows `60` and Thesis `20` in the credits
   column, with the hours column blank.** Every other row has
   hours = credits × 15. Stored as credits, Internship would
   record 900 teaching hours against one module. They are read
   as hours instead: Internship becomes 4 credits / 60 hours,
   which is exact. **Thesis becomes 1 credit / 15 hours against
   the sheet's 20, which does not divide cleanly.** Correct the
   Thesis course if 20 hours is right.

2. **Six "Mathematical Computing" rows have no credits and no
   teaching days.** Dropping them would hide an assignment that
   exists, so they are imported with 3 credits assumed and no
   schedule, showing as **Pending**. Set their teaching days on
   the assignment screen.

## Notification emails

When an administrator clicks **Assign Workload**, the lecturer
and the cohort's class representative are emailed. An edit sends
the same email worded as an update, because an edit moves real
class dates.

Each email carries the course code, name, credits and hours; the
teaching team; cohort, programme and faculty; academic period;
teaching days, start, end and status; **every class date**; any
public holiday that displaced a sitting; and a link to that
person's own screen — the lecturer to their workload, the
representative to their cohort calendar. A second link carries
the same destination in `?next=`, so someone not signed in lands
on the right page rather than a generic home screen.

Both an HTML and a plain-text body are sent. The HTML is written
for email clients: table layout, inline styles, no external
stylesheet and no web fonts.

### Two rules this is built on

**Delivery never breaks the assignment.** The workload row is
already saved by the time any email is attempted. A refused SMTP
connection turning a successful save into a 500 would be the
worse failure by a distance, so every send is wrapped, logged
and reported rather than raised. There is a test that points the
mail backend at a socket that refuses and checks the row
survives.

**The administrator is told who was *not* reached, and why.**
"Assigned successfully" while an email silently went nowhere is
worse than no email at all, because you believe the lecturer has
been told. Every recipient ends up in `sent`, `skipped` or
`failed` with a reason, surfaced on screen:

> Notified Nizeyimana Pacifique (pacifique@gmail.com).
> Not notified: Cohort 9 representative — this cohort has no
> class representative linked.

The success message for the save is kept separate from the
delivery message on purpose, so a green tick cannot hide a
non-delivery.

Someone linked through the **Lecturer Assignments** or
**Representative Assignments** screens is reachable too, not
only someone linked through `Lecturer.user` — both paths are
checked, matching how `resolve_lecturer` already worked.

## Schema changes

Three, each forced by data that could not otherwise be recorded.

**`AcademicPeriod.cohort`** (nullable). Uniqueness was
`(academic_year, semester)`, so `("2028 - 2030", "Semester 1")`
could exist once in the whole institution. Cohort 12 and Cohort
13 both run exactly that, ten months apart. Nullable, so periods
created before this field keep working as institution-wide ones.
This was listed as an open issue in the previous round.

**`Workload.co_lecturers`** (M2M). A single lecturer column
cannot hold "Dr. Eric Nizeyimana, Mr. david Hagumuwumva". The
second name was simply lost, and the co-lecturer's own dashboard
showed nothing for a module they teach. Lecturer dashboards,
calendars and print views now use `workloads_for_lecturer()`,
which matches the lead column and the co-lecturer table and
de-duplicates. Scope is not widened: a lecturer still cannot see
another lecturer's module, and there is a test for it.

**`Workload.duration_weeks`** (nullable). Internship and Thesis
run a whole term irrespective of credits. Blank keeps the
standard credit-derived block, so nothing else changes
behaviour.

Both new fields are on the assignment form, marked optional.
Selecting the lead lecturer as their own co-lecturer is dropped
rather than rejected — the intent is clear and there is nothing
to correct.

## Accounts

Five lecturers and six cohorts in the workbook had no login.
`--create-accounts` created them:

    DrFlorenceMukamanzi   DrMusabeJeanBosco   MrDavidHagumuwumva
    ProfGogaNicu          ProfSundayIdowu
    Cohort9Rep  Cohort10Rep  Cohort11Rep
    Cohort12Rep Cohort13Rep  Cohort14Rep

**Their email addresses are blank and their passwords unusable,
deliberately.** Inventing an address would mean the system
reporting a notification as sent while it went nowhere, which is
the one outcome the design exists to prevent. Set real addresses
on the Users screen; until then the import and the notification
both say plainly that these people cannot be reached.

Every lecturer and every cohort now has an account, so no
assignment goes unnotified for want of a linked record.

## Configuration

`ALLOWED_HOSTS` was empty and `DEBUG` hard-coded on — flagged as
an open issue previously, and now fixed. `DEBUG`,
`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, the email
settings and `SITE_URL` all read from the environment, with
development-safe defaults. See `.env.example`.

**Nothing needs configuring to try this out.** With no
`EMAIL_HOST` set, every notification is printed to the terminal
running `runserver`, so you can read exactly what the lecturer
and the representative would receive. Set `EMAIL_HOST` and it
switches to real delivery.

`SITE_URL` matters once deployed: it is what makes the links in
an email absolute. Left at its default, every lecturer receives
a link to `127.0.0.1`, which works only on the server itself.

## Files

New:

- `workload/notifications.py`
- `workload/management/commands/import_workload_excel.py`
- `templates/email/workload_assigned.html`
- `templates/email/workload_assigned.txt`
- `templates/email/workload_assigned_subject.txt`
- `workload/tests_notifications.py` — 43 tests
- `workload/tests_import.py` — 20 tests
- `academics/migrations/0005_...`, `workload/migrations/0006_...`
- `.env.example`

Changed: `config/settings.py`, `workload/models.py`,
`workload/views.py`, `workload/forms.py`, `workload/utils.py`,
`workload/selectors.py`, `academics/models.py`,
`static/css/style.css`, `templates/workload/assignment.html`,
`templates/reports/workload_report.html`, `requirements.txt`.

## Tests

The 20 import tests run the real command against a small
workbook built in memory that reproduces each fault above, so a
failure names the fault that broke rather than pointing at an
opaque fixture.

## Still open

- The Thesis credit value (see above).
- The six Mathematical Computing rows need teaching days.
- Eleven accounts need email addresses and passwords.
- `academic_calendar` still duplicates `academics.Holiday` and
  remains unused.


---

# Email delivery, and "All days"

## "All days" now means the working week

Internship and Thesis are written "All days" in the
spreadsheet. That was read literally as all seven days, which
scheduled Saturday and Sunday sittings on every placement and
gave a thirteen-week internship **91 class dates**.

It now means Monday to Friday: **65 sittings**. Twenty
workloads were affected and have been corrected in place by
re-running the import.

The phrase is still reported at import time, so the reading is
visible rather than assumed.

## Why no email arrived

The notification code was firing correctly on both adding and
editing a workload. Two other things stopped anything reaching
an inbox.

**1. No mail server was configured.** `EMAIL_BACKEND` falls
back to Django's console backend when `EMAIL_HOST` is unset, so
messages were printed to the terminal running `runserver` and
never sent. The system reported them as sent because, as far as
it was concerned, they were handed over successfully.

That report was misleading, so it no longer says it. When mail
is only being printed, the assignment screen now says so
explicitly:

> Notification for Prof. Goga Nicu (goga.nicu@auca.ac.rw),
> Cohort12Rep (cohort.12.rep@auca.ac.rw) was written to the
> server console, **NOT delivered**: no mail server is
> configured.

**2. Eleven accounts had no email address**, including every
one of the ten class representatives, so they were skipped
entirely. All eleven now have one.

### To send real email

    export EMAIL_HOST=smtp.gmail.com
    export EMAIL_PORT=587
    export EMAIL_HOST_USER=workload@auca.ac.rw
    export EMAIL_HOST_PASSWORD=your-app-password
    export SITE_URL=https://workload.auca.ac.rw

For Gmail this must be an **App Password** from
<https://myaccount.google.com/apppasswords>; the account's
normal password is rejected. `SITE_URL` matters as much as the
rest: left at its default, every recipient gets a link to
`127.0.0.1`, which works only on the server itself.

## New commands

**`check_email`** answers "why did nothing arrive?" directly.
It reports which backend is in use, opens a real connection to
the mail server and reports what it says, then lists every
lecturer and cohort that cannot be reached and why.

    python manage.py check_email
    python manage.py check_email --to you@example.com

**`set_emails`** fills in missing addresses in bulk.

    python manage.py set_emails --domain auca.ac.rw --dry-run
    python manage.py set_emails --domain auca.ac.rw
    python manage.py set_emails --user Cohort9Rep --email joy@auca.ac.rw

It will not overwrite an address already set unless
`--overwrite` is given, so a real address entered by hand is
never replaced by a generated guess. Addresses already in use
are skipped and listed rather than assigned twice — without
that, every class representative would have collapsed onto one
address and the first would have received all ten cohorts'
mail.

Generated addresses are **guesses about real people**. Use
`--dry-run` first and check them against your mail directory:
one that does not exist bounces silently, and the person never
learns they were assigned.

## Still open

- The Thesis credit value: the sheet shows 20 hours, which
  converts to 1 credit / 15 hours.
- Six Mathematical Computing rows need teaching days.
- The eleven generated addresses need confirming.
- Five addresses entered previously look like typos and will
  bounce: `fidele@gamil.com`, `emmanuel@gamil.com`,
  `lema@gamil.com`, `eric@gamil.com`, `arthur@gmai.com`.


---

# Assignment confirmation screens

The delete pages rendered a bold label for every field whether
or not there was a value behind it. When a value was empty the
page showed **User Account:**, **Lecturer:** and
**Qualification:** each followed by blank space, above a
working Delete button.

That is the worst shape this screen can take. It looks like
corrupted data, it gives no way to tell whether the right
record is loaded, and it still invites the administrator to
confirm the removal of something the page never identified.

Both delete pages now:

- name every value, and say **(not recorded)**, **(no email
  address set)** or **(no account linked)** in muted italics
  where one is genuinely absent, so a gap is never ambiguous;
- show the lecturer's email, and the cohort's programme, so
  the record can be identified with certainty before pressing
  Delete;
- explain what removal actually does. Unlinking keeps the
  lecturer and every workload on their record; only the login
  connection goes. Without that sentence "Delete" reads as
  though it destroys their teaching history;
- warn, on the representative page, that nobody will be
  notified on the cohort's behalf until another account is
  linked;
- refuse to render a Delete button at all if the assignment
  itself could not be loaded.

Seven tests were added covering populated fields, each missing
value, and the note about what is kept.

## Note on versions

The screenshots that prompted this showed a page headed
"Delete Lecturer **Account** Assignment" with a
**Qualification** field. Neither the original uploaded project
nor the version delivered here contained that template — both
were headed "Delete Lecturer Assignment" and had only User and
Lecturer.

A third copy of the codebase is therefore in use somewhere. The
work above is on this copy. If the fault persists after taking
these files, the running templates and `accounts/views.py`
differ from these and need comparing directly.


---

# Why the notification emails were not arriving

The email feature itself was already built and wired in: both
adding and editing a workload on the app's own assignment
screen called `notify_assignment`, which resolves the lecturer
(and any co-lecturers) and the cohort's class representative,
reads the address from each person's own user account, and
sends an HTML and plain-text message.

That code was working. Four other things stopped a message
reaching an inbox, and one of them stopped the Django admin
loading at all.

**148 tests pass** — the 132 that existed before, plus 16 new.

    python manage.py migrate
    python manage.py test

## 1. `.env` was documented but never read

`.env.example` said to copy the file to `.env` and fill in the
SMTP credentials. Nothing loaded that file. Every setting was
read with `os.environ.get`, which sees only real environment
variables, so a completed `.env` full of correct Gmail
credentials changed nothing at all and notifications carried on
going to the console.

This is the worst shape the problem can take, because the
system looks configured and still delivers nothing.

On Windows it was worse again: the documented
`export EMAIL_HOST=...` is shell syntax that PowerShell and
`cmd` do not understand, so there was no working way to set
these at all short of editing `settings.py` by hand.

`config/settings.py` now reads `.env` from the project root on
startup. It is written out rather than pulling in
`python-dotenv`, so nothing new has to be installed for email
to start working. It tolerates comments, blank lines, a pasted
`export ` prefix, quoted values and `=` inside a password.

**A real environment variable always wins over the file.** A
server that sets `EMAIL_HOST` in its own configuration must not
be overridden by a stray `.env` left in the checkout.

To send real mail now:

    cp .env.example .env

then uncomment and fill in:

    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_HOST_USER=workload@auca.ac.rw
    EMAIL_HOST_PASSWORD=your-app-password
    DEFAULT_FROM_EMAIL="AUCA Workload <workload@auca.ac.rw>"
    SITE_URL=https://workload.auca.ac.rw

Restart the server, then confirm what was picked up:

    python manage.py check_email

For Gmail the password must be an **App Password** from
<https://myaccount.google.com/apppasswords>; the account's
normal password is rejected.

`SITE_URL` matters as much as the credentials. Left at its
default, every lecturer receives a link to `127.0.0.1`, which
works only on the server itself.

## 2. `templates/admin` was a zero-byte file

Django expects `templates/admin/` to be a directory. A
zero-byte **file** of that name sat where the directory would
go, so the template loader called `open()` on
`templates/admin/workload/workload/change_list.html` and hit
`NotADirectoryError`. That is not a `FileNotFoundError`, so
Django did not fall through to the next loader — it raised.

**Every page of the Django admin returned a 500**, including
`/admin/workload/workload/`, which the sidebar links to as
"Workload Assignment". The file is removed; the admin loads.

It was almost certainly created by accident. It was in the
uploaded archive at zero bytes, matching the two zero-byte
report templates found in an earlier round.

## 3. The Django admin notified nobody

With the admin reachable again, a second gap showed. The
sidebar sends administrators straight to
`/admin/workload/workload/`, but `WorkloadAdmin` had no save
hook, so a workload assigned or edited there emailed nobody.

Which of the two screens an administrator happened to use
silently decided whether the lecturer and the class
representative were ever told, and nothing on screen revealed
the difference.

`WorkloadAdmin.save_related` now sends the same notification,
with the same on-screen report, as the app's own form.

It hangs off `save_related` rather than `save_model` because
`co_lecturers` is a many-to-many. At `save_model` time those
rows are not written yet, so `teaching_team()` would return the
lead alone and a co-teacher added in that same edit would never
hear about the module they are teaching. `save_related` runs
immediately after `form.save_m2m()`, by which point the team is
complete. There is a test for exactly that.

The wording of the on-screen report moved from `workload/views.py`
into `notifications.report()` so both screens share one copy.
Two copies would drift, and the drift would be invisible until
an administrator on one screen was told less than an
administrator on the other.

## 4. The admin form was missing two fields

`co_lecturers` and `duration_weeks` were added to the model in
an earlier round and added to the app's assignment form, but
never to the admin's `fieldsets`. A co-teacher entered in the
Django admin was therefore silently dropped — the field was not
on the form to begin with.

Both are now on the admin form, with `co_lecturers` searchable
like the other lecturer fields.

## What was already correct, and is unchanged

- Addresses come from each person's own user account, which is
  what was asked for. Both linkage paths are honoured: through
  `Lecturer.user` and through the Lecturer / Representative
  Assignment screens.
- Co-lecturers are notified, not just the lead.
- An edit is worded as an update, because an edit moves real
  class dates.
- Delivery never breaks the assignment. The row is committed
  before any send is attempted, and a refused SMTP connection
  is reported rather than raised.
- The administrator is told who was **not** reached and why,
  separately from the green "assigned successfully" tick.
- All 15 lecturers and all 10 class representatives currently
  have an address on file, so nobody is skipped for want of one.

## New files

- `.gitignore` — `.env` now holds the mail password, and
  committing it would publish the sending mailbox's app
  password. `db.sqlite3` is ignored too: it carries real staff
  and student addresses.
- `workload/tests_admin_notifications.py` — 16 tests covering
  assign and edit from the admin, the co-lecturer timing case,
  the "who was not reached" report, survival of a dead mail
  server, the console-backend warning, and `.env` parsing.

Changed: `config/settings.py`, `workload/admin.py`,
`workload/notifications.py`, `workload/views.py`,
`.env.example`. Removed: `templates/admin` (the stray file).

## Still open

Unchanged from the previous round:

- The Thesis credit value: the sheet shows 20 hours, which
  converts to 1 credit / 15 hours.
- Six Mathematical Computing rows need teaching days.
- The eleven generated addresses need confirming against the
  mail directory.
- Five addresses look like typos and will bounce silently:
  `fidele@gamil.com`, `emmanuel@gamil.com`, `lema@gamil.com`,
  `eric@gamil.com`, `arthur@gmai.com`. A bounced address means
  the person is never told, and nothing on screen will say so.
- `academic_calendar` still duplicates `academics.Holiday`.

New, and worth a decision:

- **Deleting a workload notifies nobody.** A representative who
  was emailed a list of class dates still believes those
  classes are running after the assignment is removed. This was
  left alone because it was not asked for and it sends mail to
  real people, but it is the obvious next gap.
- The admin's "Mark as Done" / "Mark as Pending" bulk actions
  use `queryset.update()`, which bypasses `save()` entirely. No
  email is sent, and no schedule is recalculated. That is
  probably right for a status flag, but it is a deliberate
  choice rather than an accident.


---

# Removing the account assignment screens

"Assign Lecturer Account" and "Assign Representative Account"
are gone. Adding a lecturer or a cohort already collects the
login, so the two screens recorded a fact the system had
already been told.

**143 tests pass.**

    python manage.py migrate
    python manage.py test

## Why they were worth removing

`LecturerForm` has a **User Account** field limited to accounts
with `role="lecturer"`. `CohortForm` has a **Representative**
field limited to `role="representative"`. Both are filled in at
the moment the record is created, and can be changed by editing
it.

The assignment screens wrote the same link into a second pair
of tables. One fact, two homes, and nothing keeping them in
step. That had three costs:

- **The two screens could disagree.** A previous round fixed a
  crash caused by exactly this — the assignment table said one
  account owned a lecturer record while `Lecturer.user` said
  another, and saving raised `UNIQUE constraint failed`.
- **Every lookup had to ask twice.** `workload/selectors.py`
  existed largely to try both paths and decide which to believe
  when they differed.
- **A notification could be sent to the wrong inbox**, because
  "which account does this lecturer use" had two possible
  answers and the code picked one by ordering.

## The database was audited before anything was dropped

If any lecturer or cohort were linked **only** through an
assignment row, deleting those tables would have cost that
person their dashboard and their assignment emails, silently.

Checked first, on the uploaded database:

| | Records | Linked on their own record |
|---|---|---|
| Lecturers | 16 | 16 |
| Cohorts | 10 | 10 |

Nothing was reachable only through the assignment tables, and
no row disagreed with the record it pointed at. Nothing was at
risk here.

**A backfill migration was written anyway.** `accounts/0005`
runs before the tables are dropped and copies any
assignment-only link onto `Lecturer.user` /
`Cohort.representative`. This database does not need it; a copy
running somewhere unaudited might. It only ever fills a gap —
an existing link is never overwritten, because that is the
value the Add screen collected and the one someone most
recently confirmed. It refuses to point two lecturers at the
same login rather than failing mid-migration on the one-to-one
constraint.

Deliberately not reversible: recreating the rows would mean
guessing which links had come from the assignment table, and
guessing wrong would resurrect links an administrator removed.

`accounts/0006` then deletes both models.

Verified after migrating a copy: 16 of 16 lecturers and 10 of
10 cohorts still linked, every workload still resolving its
recipients, nobody unreachable.

## What was removed

- `LecturerAccountAssignment`, `RepresentativeAccountAssignment`
- 8 views, 8 routes, 2 forms, 10 templates
- Both sidebar entries and both buttons on the Users screen
- `LECTURER_ASSIGNMENT_SEARCH_FIELDS`,
  `REPRESENTATIVE_ASSIGNMENT_SEARCH_FIELDS`
- The assignment-table writes in `import_workload_excel`

`workload/selectors.py` now resolves through one path. The
reverse lookups (`account_for_lecturer`, `account_for_cohort`)
are kept as named functions rather than inlined: returning
`None` is what the notification code reports as "no account is
linked", and that message is the only warning an administrator
gets that an assignment email went nowhere.

## Two messages were redirected, not deleted

Creating a lecturer login used to say "link this on the
Lecturer Accounts screen". Left alone it would have pointed at
a screen that no longer exists. It now names the surviving one
and says what is at stake:

> Next, open Academics > Lecturers and set this account on the
> lecturer's record — either by adding the lecturer, or by
> editing an existing one. Until then their workload will not
> appear when they sign in, and assignment emails cannot reach
> them.

The role-change guard did the same. It refuses to turn a linked
lecturer into a representative, and now names the record
blocking it:

> This account is set as the login for the lecturer record
> 'Kumar Kundan'. Open Academics > Lecturers, clear the User
> Account field on that record, then change the role.

## Unlinking

Removal used to be its own screen. It is now clearing the
**User Account** field on the lecturer, or **Representative**
on the cohort. Behaviour is unchanged and still tested: the
lecturer, their workload and the login all survive; only the
connection goes.

## Tests

Removed the classes that only exercised the deleted screens
(`LecturerLinkValidationTests`, `RepresentativeLinkTests`,
`UnlinkedVisibilityTests`, `DeleteAssignmentPageTests`) and the
two-path linkage tests in `workload/tests.py` and
`workload/tests_notifications.py`, rewriting each to cover the
surviving path.

Added two classes:

- `AssignmentScreensRemovedTests` — the models are gone, the
  routes raise `NoReverseMatch`, the sidebar does not link to
  them, and every admin screen still loads. A dead `{% url %}`
  in `base.html` is not a broken link, it is a 500 on every
  page that extends it.
- `LinkingStillReachesTheInboxTests` — the removal must not
  cost anyone their notification email. Covers both directions,
  the unlinked case resolving to `None` rather than to somebody
  else, and that Add Lecturer links in a single step.

Also fixed: the eight `.env` tests used the real setting names
(`EMAIL_HOST` and friends). Now that `settings.py` loads the
project's `.env` at import, a machine with mail configured
already had those in `os.environ` — which the loader correctly
refuses to overwrite — so the tests passed or failed depending
on whether email happened to be set up. They use dedicated
`AUCA_TEST_*` keys instead. A test that depends on the
developer's mail configuration is worse than no test.

## Still open

- **Your `.env` shipped inside the uploaded zip, with a live
  Gmail app password in it.** `.gitignore` keeps it out of git,
  but it travels in any archive. Revoke that password at
  <https://myaccount.google.com/apppasswords> and generate a
  fresh one — it has left your machine.
- Deleting a workload still notifies nobody, so a
  representative keeps believing cancelled classes are running.
- The Thesis credit value: the sheet shows 20 hours, which
  converts to 1 credit / 15 hours.
- Six Mathematical Computing rows need teaching days.
- Five addresses look like typos and will bounce silently:
  `fidele@gamil.com`, `emmanuel@gamil.com`, `lema@gamil.com`,
  `eric@gamil.com`, `arthur@gmai.com`.
- `academic_calendar` still duplicates `academics.Holiday`.


---

# The Days column was hiding the action buttons

On the Workload Assignment screen the View / Edit / Delete
buttons sat off the right-hand edge, reachable only by
scrolling sideways. The Internship and Thesis rows were the
ones doing it.

**172 tests pass.**

## What was actually wrong

`course_days` is stored the way the spreadsheet writes it, with
no space after the commas:

    Monday,Tuesday,Wednesday,Thursday,Friday

To a browser that is a single unbreakable forty-character word.
There is no legal place to break it, so the column could not be
made narrower, and the whole table grew wider than the card
holding it. The Actions column was last, so it was the part
pushed out of sight.

Measured across every row on the real data, the longest
unbreakable run per column:

| Column | Longest value | Longest unbreakable run |
|---|---|---|
| Academic Period | 43 | 14 |
| Course | 37 | 14 |
| Lecturer | 26 | 13 |
| **Days** | **40** | **40** |

Academic Period is the longer column overall and causes no
trouble at all, because it contains spaces and wraps by itself.
Days was the only value in the table that could not wrap, which
is why it alone set the width. Only Internship and Thesis run
five days a week, which is why only those rows showed it.

## The fix

The cell now renders one element per day instead of one string,
which gives the browser somewhere to wrap, and the names are
abbreviated:

    [Mon] [Tue] [Wed]
    [Thu] [Fri]

The longest unbreakable run in that column goes from **40
characters to 3**. A five-day module takes two short lines; the
common two-day modules still take one.

Hovering a chip shows the full day name, so shortening costs no
information. Days are ordered by the calendar week rather than
the order they were typed, so `Thursday,Sunday` and
`Sunday,Thursday` read identically. A row with no days recorded
shows a dash rather than an empty cell, because blank space
reads as a page that failed to load.

`Workload.teaching_days()` does the parsing, reusing the
existing `parse_course_days` helper rather than splitting on
commas again. An unrecognised day name falls back to showing
whatever was typed: bad data is a reason to surface the value,
not to break the page.

## The Actions column is now pinned

Wrapping the days is enough on a normal laptop. But this table
carries ten columns, and there will always be a screen narrow
enough to push the last one out of view -- which is the fault
being fixed, so fixing it only for wide screens is not fixing
it.

Actions is now pinned to the right edge and the other columns
scroll underneath. The buttons are reachable at any width.

Scoped to `.table-sticky-actions`, applied to this one table,
so the tables on every other screen are untouched. Two details
that matter: the pinned cell needs an opaque background or the
columns sliding beneath show through the buttons, and
`.modern-table` sets `overflow:hidden` to clip its rounded
corners, which creates a clipping context that stops a sticky
cell sticking -- so the scoped rule overrides it.

## Also applied to the two calendar screens

`workload/calendar.html` and
`workload/representative_calendar.html` print the same field
and had the same unbreakable string setting their table width.
Neither has action buttons to lose, but the tables were wider
than they needed to be. The print and report templates are
untouched -- they lay out differently and full day names read
better on paper.

## A bug I introduced and then caught

The Lecturers screen was returning a 500:

    TypeError: searchable_list() takes 6 positional arguments
    but 7 were given

A stray `REPRESENTATIVE_SEARCH_FIELDS,` argument had been left
inside the `lecturer_list` call when the Representatives screen
was added. Removed. It was caught by
`test_every_admin_screen_still_loads`, which is exactly the
test that exists to catch it.

## Tests

`workload/tests_days_column.py`, 18 tests. The one that matters
most asserts the string `Monday,Tuesday,Wednesday,Thursday,Friday`
does not appear in the rendered page -- if anyone puts
`{{ workload.course_days }}` back in the table, it fails.
Another walks every days cell in the rendered HTML and asserts
no remaining text run is longer than three characters, which
measures the fix rather than assuming it.

The rest cover calendar ordering, duplicates, spacing and
casing, empty and invalid values, the full-name tooltip, the
dash for missing days, the action links being present on every
row, both calendar screens, and the stylesheet rules the markup
depends on.

## Still open

- Your `.env` shipped inside an uploaded zip with a live Gmail
  app password. Revoke it at
  <https://myaccount.google.com/apppasswords>.
- Deleting a workload notifies nobody.
- The Thesis credit value: the sheet shows 20 hours, which
  converts to 1 credit / 15 hours.
- Six Mathematical Computing rows need teaching days. They now
  show a dash in the Days column, so they are easy to spot.
- Five addresses look like typos and will bounce silently:
  `fidele@gamil.com`, `emmanuel@gamil.com`, `lema@gamil.com`,
  `eric@gamil.com`, `arthur@gmai.com`.
- `academic_calendar` still duplicates `academics.Holiday`.

---

# Class representative CRUD, and button sizing

> **Superseded in part.** The Class Representatives screen
> described below was removed in the next section. The button
> sizing work stands. Kept for the record of why the screen
> existed and what its constraints were, since those
> constraints now live on the Cohort form.

## Class Representative was missing two of the four operations

The screen listed cohorts and let you change who represents one.
There was no way to **add** a representative and no way to **remove**
one. The only "Add" button on the page linked to Create User, which
makes a login account but never attaches it to a class, so a new
representative account sat unused until somebody thought to open the
right cohort and use Change.

Add and Remove now exist, and the screen is genuine CRUD.

### Add works the way Add Lecturer works

`/academics/representatives/create/`

Add Lecturer picks an **existing** user account with `role="lecturer"`
from a dropdown and joins it to a Lecturer record. Add Representative
now does the same thing with `role="representative"` accounts. Neither
screen creates the account: a login and its password belong on the
Users screen, and there is a secondary "Create User Account" button
for when one does not exist yet.

The one structural difference is where the link lives. A lecturer has
a record of its own; a representative does not. The entire
relationship is the `Cohort.representative` column, so "adding a
representative" means picking a cohort that has nobody and filling
that column in. The form therefore has two dropdowns, cohort first.

### The OneToOne constraint had to be respected in both directions

`Cohort.representative` is a `OneToOneField`. Two cohorts pointing at
the same account is a database error, not a policy choice, so:

- the Add form offers only cohorts with `representative__isnull=True`
- it offers only accounts with `representing_cohort__isnull=True`
- and it re-checks the posted values on save

The last point matters on its own. Hiding a choice in a dropdown is
not validation: a stale page could still post an account that has been
taken in the meantime, and the result would have been a
`UNIQUE constraint failed` traceback.

The **existing Edit screen had this bug**. It offered every account
with the representative role, including ones already speaking for
another class, and saving one raised that error. It now offers
unassigned accounts plus the current holder of this cohort — the
current holder has to stay in the queryset or re-showing the form
would blank a valid value.

### Remove deletes the link, not the people

`Remove` clears `Cohort.representative` and nothing else. Both the
cohort and the user account outlive the relationship: the account may
represent a different class next intake, and the cohort certainly
still exists. Deleting a login belongs on the Users screen.

"Delete" on this screen could plausibly have meant the link, the
account, or the cohort, so the confirmation page states which of the
three survive rather than leaving it to be discovered afterwards. It
also warns that nobody will be emailed for that class from then on.

### Empty states

Add has two, with different causes and different advice:

- every cohort already has a representative — the finished state, not
  a fault, so it says so instead of showing two empty dropdowns
- cohorts are waiting but no free account exists — a missing
  prerequisite, so it links to Create User

## Buttons were different heights

Adjacent buttons did not match. There were three independent causes.

**1. A `<button>` does not inherit font-size.** Browsers give it their
own default of about 13px while an `<a>` beside it renders at the
body's 16px, so identical padding produced different heights.
`accounts/update_user.html` had exactly this: `<button class="btn
btn-primary">Update</button>` next to `<a class="btn
btn-secondary">Cancel</a>`. Buttons now inherit type like anything
else.

**2. `form input` was styling submit buttons as text fields.** The
rule gave every `input` inside a form `width:100%`, `padding:12px` and
a grey border. An `<input type="submit">` looked nothing like the
`<button>` next to it. The selector now excludes submit, button,
reset, checkbox and radio.

**3. Height was built from vertical padding**, so it moved with font
size, with whether the label wrapped, and with whether the button
carried an icon. Height is now set once as `min-height` with the label
centred inside, so neither icons nor label length can change it.

Spacing had the same problem: `margin-bottom:20px` was on some button
classes and not others, so a pair sat at different heights on the page
even once the boxes matched. Spacing now comes from the row —
`.btn-row` for form actions, `.table-actions` for actions in a table
cell — and the buttons carry none.

### Two tiers, documented

Mixing tiers was the fourth way this went wrong: a full-size
`.admin-dashboard-btn` was being placed next to a table-row
`.edit-btn`, which is deliberately smaller. `representative_form.html`
did this with Save and Cancel. The tiers are now written down:

- **full size**, 42px — page and form actions
- **compact**, 34px — actions inside a table row

Every class in a tier shares height, padding, radius, weight and
alignment whatever element it is written as: `<a>`, `<button>` or
`<input type="submit">`.

### Classes that were used but never defined

`.btn`, `.btn.ghost` and `.btn.secondary` appeared in templates but
existed nowhere in `style.css` — only in the print stylesheet, which
does not apply to app screens. So `class="btn btn-primary"` was
getting its appearance from `.btn-primary` alone. Likewise
`.page-note`, `.status-warning` and `.logout-btn`. All are now
defined.

## Files

New:

- `academics/tests_representatives.py` — 16 tests
- `templates/academics/representative_confirm_delete.html`

Changed:

- `academics/forms.py` — `RepresentativeAssignmentForm`; the Edit form
  no longer offers accounts held by another cohort
- `academics/views.py` — `representative_create`, `representative_delete`
- `academics/urls.py` — the two new routes
- `templates/academics/representatives.html` — Add and Remove
- `templates/academics/representative_form.html` — create and update
- `static/css/style.css` — unified button sizing
- `templates/academics/{form,faculties,programs,cohorts,courses,lecturers,holidays,academic_periods}.html`,
  `templates/accounts/{users,update_user,delete_user}.html`,
  `templates/workload/assignment.html` — button rows and action cells

No migration: this reuses the existing `Cohort.representative` column
rather than adding a table.

## Tests

172 pass, 16 of them new: the four operations, the role filter on the
dropdown, both directions of the OneToOne guard, the posted-value
re-check, the missing-email warning, both empty states, search, and
that a non-admin is redirected away from all four screens.

## Note on your data

All ten cohorts currently have a representative and all ten
representative accounts are taken, so Add will correctly show the
"every cohort already has a representative" state until a new cohort
is added or one is freed with Remove.


---

# Removing the Class Representatives screen

Representatives are no longer managed on a screen of their own.
They are reached through **Users**.

## Why this is a clean removal

A representative never had a record of its own. It is a user
account with `role="representative"`, and the link to a class is
the `Cohort.representative` column. Both of those already have
screens:

- the **account** is created and edited under Users
- the **link** is set when editing the cohort, on a field the
  Cohort form has always had

So the dedicated screen was a third way of writing the same two
things. Removing it takes away a duplicate path, not a
capability.

## What was removed

- the **Class Representatives** entry in the sidebar under PEOPLE
- `representative_list`, `representative_create`,
  `representative_update`, `representative_delete`
- their four routes, now 404
- `RepresentativeAssignmentForm` and `CohortRepresentativeForm`
- `templates/academics/representatives.html`,
  `representative_form.html`,
  `representative_confirm_delete.html`
- `REPRESENTATIVE_SEARCH_FIELDS`, and the tests for the screen

## What had to move, not just be deleted

Deleting the screen made `CohortForm` the **only** path to the
link, so the rules that were enforced on the dedicated screen
had to be enforced there instead. They were not.

`Cohort.representative` is a `OneToOneField`. `CohortForm` was
filtering the dropdown to `role="representative"` and nothing
else, so it offered accounts already speaking for another class.
Choosing one raised `UNIQUE constraint failed` rather than a
message. It now offers accounts representing nobody, plus
whoever holds this cohort already — the current holder has to
stay in the queryset or re-showing the form would blank a valid
value.

The dropdown also annotates accounts with no email address, as
the removed screen did. An account with no address cannot be
emailed when a workload is assigned, which is most of the point
of linking one.

## Keeping the one thing the screen was good for

Its real value was seeing at a glance which classes nobody is
notified for. The **Cohorts** list already had a Representative
column, so that column now flags both failure modes instead of
printing plain text:

- no representative at all
- a linked account with no email address, which is the quieter
  failure: the class looks covered everywhere else and the
  notification reaches nobody

Cohort search already matched on `representative__username`.

## Making "accessed through Users" real

The Users screen had search but no role filter, so "show me the
representatives" meant reading the whole list. It now has role
tabs — All, Admin, Lecturer, Class Representative — as plain
`?role=` links, so a filtered view is a URL that can be
bookmarked. The filter is applied before the text search, so
searching within a role stays inside it, and an unknown value is
ignored rather than obeyed.

The dashboard tile counting representatives now links to
`/users/?role=representative` rather than the unfiltered list. It
is a count, not a management screen, so it stayed.

## Files

New:

- `academics/tests_cohort_representative.py` — 15 tests

Changed:

- `academics/forms.py` — `CohortForm` carries the OneToOne guard
- `academics/views.py`, `academics/urls.py` — screens removed
- `accounts/views.py` — role filter on the user list
- `templates/base.html` — sidebar entry removed
- `templates/accounts/users.html` — role tabs
- `templates/academics/cohorts.html` — gaps flagged
- `templates/analytics/dashboard.html` — tile retargeted
- `common/search.py`, `accounts/tests.py` — dead code removed
- `static/css/style.css` — `.filter-tabs`

No migration. Nothing about the data model changed; only which
screens write to it.

## Tests

161 pass. 15 are new: that the old routes 404 and the sidebar no
longer offers them, that the cohort form sets and clears the
link, both directions of the OneToOne guard, that a posted taken
account is refused rather than raising, that the cohort list
flags both failure modes, and the role filter including a
tampered value.

---

# Comment trim

Prose comments cut from 460 lines to 111 (76%). Kept only
where the code would otherwise look arbitrary:

- `Lecturer.user` is SET_NULL, not CASCADE
- `Cohort.representative` is OneToOne, so a taken account is a
  UNIQUE error rather than a choice
- `<button>` does not inherit font-size (the button sizing fix)
- `delete_user` names its context "account", not "user", because
  the sidebar renders from `{{ user }}`
- the spreadsheet quirks in `import_workload_excel` -- broken
  dates, co-teacher cells, copied sheet titles

Also removed a comment in `common/search.py` that still
described the deleted Representatives screen.

No behaviour changed. 161 tests pass.

---

# Add Cohort: the representative dropdown

## It was already a dropdown, but it rendered empty

The field lists user accounts with `role="representative"`, and
it did before this change. The problem on the live data was
that it showed nothing to pick.

`Cohort.representative` is OneToOne. All ten representative
accounts already hold one of the ten existing cohorts, so the
list of free accounts was empty and Add Cohort offered only
"-- No representative --". Nothing said why.

The dropdown now explains itself, with different advice for
the two causes:

- **no representative accounts exist at all** - create one under
  Users with the role set to Class Representative
- **all of them are already assigned** - the live case; a cohort
  holds one account and an account holds one cohort, so the way
  forward is another account, not another pick

Both link straight to Create User. When accounts are free, the
help text just notes the field is optional and can be set later.

Options read `username (email)`, or `username (no email address)`
when there is none - that address is what receives the workload
notification.

## A missing package marker was hiding the academics tests

`academics/__init__.py` did not exist.

Django still loaded the app, because Python 3 treats a folder
without `__init__.py` as a namespace package. But `unittest`
discovery skips such folders, so **every test under
`academics/` was silently never run** - it did not fail, it was
not collected. `manage.py test` reported 161 tests and looked
healthy.

This is the same fault as the missing `workload/__init__.py`
recorded at the top of this file. That one stopped the project
booting, so it was noticed immediately; this one only hid tests,
so it was not.

With the file added the suite collects **184**, all passing.
Worth checking a new app has this file before trusting a green
test run.

## Files

- `academics/__init__.py` - new, empty
- `academics/forms.py` - empty-state help on the dropdown
- `academics/tests_cohort_representative.py` - 8 more tests
- `static/css/style.css` - `.helptext`

---

# Action buttons and wide tables

## Buttons now match on every screen

`workload_list.html` used `.btn-primary` / `.btn-danger` -- the
full-size 42px page-action tier -- with no icons at all, inside
a table row. That is why its View/Edit/Delete looked nothing
like the Edit/Delete pair on every other list. It now uses the
compact 34px tier with icons, matching the rest.

Also missing icons: **Academic Periods** and **Holidays** had
none, and **Lecturers** used the Font Awesome 4 syntax
(`fa fa-edit`) rather than FA6 (`fa-solid fa-pen`). The page
loads FA6, so `fa-edit` was rendering as a blank box.

`assignment.html` had a `.table-actions` nested directly inside
an `.action-bar` -- two flex rows doing one job, from an earlier
pass -- and used the Edit style for its View link. Both fixed.

## Buttons never wrap

`.table-actions` was `flex-wrap: wrap`, so on a narrow screen
Delete dropped underneath Edit. It is now `nowrap`, and the
Actions column is `white-space: nowrap; width: 1%` so it takes
exactly the width its buttons need and no less.

## Wide tables scroll instead

If the buttons cannot wrap, something else has to give. All 18
list tables are now wrapped in `.table-scroll`
(`overflow-x: auto`), so a table wider than the screen scrolls
sideways rather than crushing its columns.

Cells stop wrapping their text inside a scroller, with one
exception: `.col-days` on the assignment screen packs weekday
chips into a block on purpose, and forcing it onto one line
would stretch the table by the width of a whole week. It opts
out via `white-space: normal`.

The assignment table already pinned its Actions column with
`position: sticky`. That column now pins against the scroll
container instead of the viewport, so View/Edit/Delete stay
reachable without scrolling the whole page.

## Files

- `static/css/style.css` -- `.table-scroll`, `.view-btn`,
  `.table-actions` set to nowrap
- `templates/workload/workload_list.html` -- correct tier, icons
- `templates/workload/assignment.html` -- nested wrapper removed,
  View restyled, table wrapped
- `academics/{academic_periods,holidays,lecturers}.html` -- icons
- 16 further templates -- scroll wrapper
- `academics/tests_cohort_representative.py` -- 4 more tests

## Tests

188 pass. The four new ones check that every list screen has a
scroll wrapper, that the workload actions carry their icons, and
that no full-size button class appears inside a table row. They
run against a real Workload row -- without one the action cells
never render and the assertions would pass against an empty
table.

---

# Qualification column, feedback messages, filter alignment

## Qualification column

The cell already carried `.col-qualification` and wrapped, but
at `max-width: 280px` the Lecturers table still ran wider than
the content area and pushed Actions out of view. Narrowed to
190px with `overflow-wrap: anywhere`, so the longest entry --
"Ph.D in Computer Science, Ph. D candidate in Data science" --
breaks over two or three lines and Edit/Delete are reachable
without scrolling.

## Filter buttons on the workload report

The reset named only one class:

    .filter-buttons .admin-dashboard-btn { margin-bottom:0; }

Apply lost its 20px bottom margin; Clear kept it. In a flex row
with `align-items:center` it is the **margin box** that gets
centred, so the extra 20px under Clear lifted it visibly above
Apply even though both are the same height.

Fixed for both (`.filter-buttons > *`), and the same reset now
applies globally to `.btn-row`, `.form-actions`, `.action-bar`
and `.filter-buttons`, so the next centred button row cannot
reproduce it.

## Messages

Most were already in place -- the academics CRUD helper names
the model and the record ("Faculty X added successfully"), and
assigning a workload reports both the save and who was emailed.

What was missing was the failure side. Submitting an invalid
workload assignment or edit produced **no message at all**: the
form re-rendered with field errors that scroll out of sight on
a long page, so the click looked ignored. Both now say so, in
the same words the academics screens use.

Also removed a dead `.alert` block that still carried Bootstrap
green and red. It was fully overridden by the AUCA-palette
rules further down, but left two definitions of the same class
in the file.

## Already present

The login password eye was already implemented -- toggle
button, icon swap, `aria-pressed`, and caret restored after the
type change. Tests now cover it, including that the toggle is
`type="button"`: without that it would default to submit inside
the login form and post the page instead of revealing the
password.

## Files

- `static/css/style.css` -- qualification width, global margin
  reset for centred rows, dead alert block removed
- `templates/reports/workload_report.html` -- filter reset
- `workload/views.py` -- failure messages on assign and edit
- `academics/tests_cohort_representative.py` -- 10 more tests

## Tests

198 pass.
