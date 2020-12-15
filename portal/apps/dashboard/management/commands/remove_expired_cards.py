from django.core.management.base import BaseCommand
from datetime import date, timedelta

from dashboard.models import Card


class Command(BaseCommand):
    help = 'Deletes all card submissions that are 48 hours old'

    def handle(self, *args, **options):
        for card in Card.objects.filter(
                date_created__lte=date.today() - timedelta(2)):
            card.delete()
