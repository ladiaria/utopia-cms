# -*- coding: utf-8 -*-
from exchange import brou

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Updates the exchange database'
    requires_model_validation = False

    def handle(self, *args, **kwargs):
        brou.update()
