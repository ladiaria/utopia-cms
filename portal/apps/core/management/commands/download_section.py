from __future__ import unicode_literals
import os
from pygit2 import Repository
from pygit2 import discover_repository

from django.core.management import BaseCommand
from django.test.client import Client


class Command(BaseCommand):
    help = "Downloads the HTML for the section given and saves it in /tmp/<section>_<branch>.html"

    def handle(self, *args, **options):
        section = args[0]
        f = open('/tmp/%s_%s.html' % (section, Repository(
            discover_repository(os.getcwd())).head.name.split('/')[-1]), 'w')
        f.write(Client().get('/seccion/%s/' % section).content)
        f.close()
