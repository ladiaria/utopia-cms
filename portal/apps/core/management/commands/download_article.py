from __future__ import unicode_literals
import os
from pygit2 import Repository
from pygit2 import discover_repository

from django.core.management import BaseCommand
from django.test.client import Client
from django.template.defaultfilters import slugify


class Command(BaseCommand):
    help = """Downloads the HTML for the article given and saves it in /tmp/<year><month><slug>_<branch>.html

Example: if you are in branch master and run

    $ ./manage.py download_article 2016/3/article1

The command saves the file /tmp/20163article1_master.html"""

    def handle(self, *args, **options):
        url = args[0]
        f = open('/tmp/%s_%s.html' % (slugify(url), Repository(
            discover_repository(os.getcwd())).head.name.split('/')[-1]), 'w')
        f.write(Client().get('/articulo/%s/' % url).content)
        f.close()