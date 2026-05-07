from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from libs.scripts.pwclear import pwclear


class Command(BaseCommand):
    help = 'Resets the signupwall visitor counters (MongoDB collections)'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This command can only be run with DEBUG=True')
        pwclear()
        self.stdout.write(self.style.SUCCESS('Signupwall counters reset successfully'))
