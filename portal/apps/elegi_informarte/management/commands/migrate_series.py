# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from elegi_informarte.models import Suscripcion, Serie


class Command(BaseCommand):
    help = """ migrate serie to fk serie model """

    def handle(self, *args, **options):
        for s in Suscripcion.objects.all():
            try:
                fk = Serie.objects.get(serie=s.credencial_serie.upper())
                s.credencial_serie_fk = fk
                s.save()
            except Serie.DoesNotExist:
                print(s)
