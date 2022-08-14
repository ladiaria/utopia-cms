# -*- coding: utf-8 -*-
# utopia-cms 2022. Aníbal Pacheco.

from __future__ import unicode_literals
from django.core.management import BaseCommand

from core.admin import update_category_home


class Command(BaseCommand):
    help = "Creates a background_task for the update_category_home function"

    def handle(self, *args, **options):
        update_category_home()
