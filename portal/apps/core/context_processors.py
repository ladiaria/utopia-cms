# -*- coding: utf-8 -*-
from django.conf import settings
from datetime import date


def aniosdias(request):
    meses = [
        ('Enero', '1'),
        ('Febrero', '2'),
        ('Marzo', '3'),
        ('Abril', '4'),
        ('Mayo', '5'),
        ('Junio', '6'),
        ('Julio', '7'),
        ('Agosto', '8'),
        ('Setiembre', '9'),
        ('Octubre', '10'),
        ('Noviembre', '11'),
        ('Diciembre', '12'),
    ]
    return {'anios': range(2009, date.today().year + 1), 'meses': meses}


def secure_static(request):
    return {'STATIC_URL': settings.SECURE_STATIC_URL if request.is_secure() else settings.STATIC_URL}
