# Recalculate stored workload statuses. Status is derived from
# the dates but stored, so it goes stale without this.

from django.core.management.base import BaseCommand
from django.utils import timezone

from workload.models import Workload


class Command(BaseCommand):

    help = "Recalculate Upcoming / Ongoing / Done for every workload."

    def handle(self, *args, **options):

        total = Workload.objects.count()

        changed = Workload.objects.all().refresh_statuses()

        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.localdate()}: checked {total} workload(s), "
                f"corrected {changed}."
            )
        )
