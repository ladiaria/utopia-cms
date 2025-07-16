from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta

from adzone.models import AdImpression, AdClick


class Command(BaseCommand):
    help = "Delete impressions and clicks registered more than 90 days ago."

    def handle(self, *args, **options):
        # TODO: support to override this default timedelta of 90 days with an argument
        since = now().date() - timedelta(90)
        AdImpression.objects.filter(impression_date__lt=since).delete()
        AdClick.objects.filter(click_date__lt=since).delete()
