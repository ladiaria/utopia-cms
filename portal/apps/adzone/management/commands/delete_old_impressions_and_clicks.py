from datetime import date, timedelta

from django.core.management.base import BaseCommand

from adzone.models import AdImpression, AdClick


class Command(BaseCommand):

    help = "Delete impressions and clicks registered more than 180 days ago."

    def handle(self, *args, **options):
        AdImpression.objects.filter(
            impression_date__lt=date.today() - timedelta(90)).delete()
        AdClick.objects.filter(
            click_date__lt=date.today() - timedelta(90)).delete()
