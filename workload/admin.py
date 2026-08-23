from django.contrib import admin

from .models import Workload
from .notifications import notify_assignment, report


@admin.register(Workload)
class WorkloadAdmin(admin.ModelAdmin):

    # ==========================
    # LIST VIEW
    # ==========================

    list_display = (
        "course",
        "lecturer",
        "cohort",
        "academic_period",
        "hours",
        "start_date",
        "end_date",
        "status",
    )


    list_filter = (
        "status",
        "academic_period",
        "cohort",
        "lecturer",
        "course",
    )


    search_fields = (
        "course__name",
        "course__code",
        "lecturer__name",
        "cohort__name",
        "academic_period__academic_year",
        "academic_period__teaching_period",
    )


    date_hierarchy = "start_date"


    list_per_page = 25



    # ==========================
    # FOREIGN KEY SEARCH
    # ==========================

    autocomplete_fields = (
        "course",
        "lecturer",
        "co_lecturers",
        "cohort",
        "academic_period",
    )



    # ==========================
    # READ ONLY GENERATED FIELDS
    # ==========================

    readonly_fields = (
        "hours",
        "end_date",
        "generated_schedule",
        "status",
    )



    # ==========================
    # FORM LAYOUT
    # ==========================

    fieldsets = (

        (
            "Assignment Information",
            {
                "fields": (
                    "cohort",
                    "academic_period",
                    "lecturer",
                    "co_lecturers",
                    "course",
                )
            }
        ),


        (
            "Schedule Information",
            {
                "fields": (
                    "start_date",
                    "course_days",
                    "duration_weeks",
                    "hours",
                    "end_date",
                    "generated_schedule",
                    "status",
                )
            }
        ),

    )



    ordering = (
        "-id",
    )



    # ==========================
    # PERFORMANCE OPTIMIZATION
    # ==========================

    def get_queryset(self, request):

        queryset = super().get_queryset(request)

        return queryset.select_related(
            "course",
            "lecturer",
            "cohort",
            "academic_period",
        )



    # ==========================
    # NOTIFY ON ASSIGN AND EDIT
    # ==========================

    def save_related(self, request, form, formsets, change):
        """
        Email the teaching team and the class representative.

        The sidebar sends administrators straight here --
        "Workload Assignment" links to this screen -- so a
        workload assigned or edited from the Django admin has
        to notify exactly as one assigned from the app's own
        form does. Without this, which of the two screens an
        administrator happened to use silently decided whether
        the lecturer and the class representative were ever
        told, and nothing on screen revealed the difference.

        This hangs off save_related rather than save_model
        because co_lecturers is a many-to-many. At save_model
        time the co-lecturer rows are not written yet, so
        teaching_team() would return only the lead and a
        co-teacher added in that same edit would never be
        emailed. save_related runs immediately after
        form.save_m2m(), by which point the team is complete.

        notify_assignment never raises. The workload is already
        committed by the time this runs, and losing the save
        because a mail server refused a connection would be the
        worse failure by a distance.
        """

        super().save_related(request, form, formsets, change)

        report(
            request,
            notify_assignment(
                form.instance,
                request=request,
                created=not change
            )
        )


    # ==========================
    # ADMIN ACTIONS
    # ==========================

    actions = (
        "mark_as_done",
        "mark_as_pending",
    )


    @admin.action(
        description="Mark selected workloads as Done"
    )
    def mark_as_done(self, request, queryset):

        queryset.update(
            status="Done"
        )



    @admin.action(
        description="Mark selected workloads as Pending"
    )
    def mark_as_pending(self, request, queryset):

        queryset.update(
            status="Pending"
        )