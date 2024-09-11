# -*- coding: utf-8 -*-

from builtins import range

from django.utils.timezone import now


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
    return {'anios': list(range(2009, now().date().year + 1)), 'meses': meses}
