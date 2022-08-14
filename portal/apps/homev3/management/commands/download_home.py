from __future__ import unicode_literals
import os
from pygit2 import Repository
from pygit2 import discover_repository

from django.core.management import BaseCommand
from django.test.client import Client


class Command(BaseCommand):
    help = 'Downloads the home HTML and saves it in /tmp/home_<branch>.html'

    def handle(self, *args, **options):
        f = open('/tmp/home_%s.html' % Repository(discover_repository(
            os.getcwd())).head.name.split('/')[-1], 'w')
        f.write(Client().get('/').content)
        f.close()