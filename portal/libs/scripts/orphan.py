#!/usr/bin/python2.5
# -*- coding: utf-8 -*-

import csv

from os.path import abspath
from os.path import dirname
import sys

dir = dirname(abspath(__file__))

PROJECT_ABSOLUTE_DIR = '%s/portal' % dir[:dir.rfind('/portal')]
sys.path.insert(0, PROJECT_ABSOLUTE_DIR)

from django.core.management import setup_environ
import settings

setup_environ(settings)

from thedaily.models import Subscriber, WebSubscriber
from django.contrib.auth.models import User

slugs = []


def cargar_suscriptores():
    for suscriptor in Subscriber.objects.all():
        slugs.append(suscriptor.user.username)

def cargar_suscriptores_web():
    for suscriptorWeb in WebSubscriber.objects.all():
        slugs.append(suscriptorWeb.user.username)

def buscar():
    for usuario in User.objects.all():
        if usuario.username not in slugs:
            print usuario.username, ' es huerfano.'

if __name__ == '__main__':
    print '- Cargando suscriptores.'
    cargar_suscriptores()
    cargar_suscriptores_web()
    print 'ok \n-Buscando usuarios huerfanos'
    buscar()
    print 'script finalizado!'



