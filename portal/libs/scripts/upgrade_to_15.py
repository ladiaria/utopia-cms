# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from builtins import input
from builtins import str
import os
import json

from django.conf import settings
from django.db import transaction

from photologue_ladiaria.models import (
    PhotoExtended, Photographer as pl_photographer, Agency as pl_agency)
from photologue.models import (
    Photographer as p_photographer, Agency as p_agency, Photo as p_photo)


__author__ = "Reidel Lazaro Rodriguez Torres, Anibal Pacheco"
__email__ = "reidelon@gmail.com, apacheco@ladiaria.com.uy"

FILE_NAME = 'migration_data.json'


def loaddata():
    database = settings.DATABASES['default']
    if os.system('''
            mysql -u %s -p %s -e "
            ALTER TABLE tagging_taggeditem MODIFY COLUMN added datetime;
            ALTER TABLE tagging_tag MODIFY COLUMN added varchar(50);
            ALTER TABLE tagging_tag MODIFY COLUMN is_valid tinyint(1);"
            ''' % (database['USER'], database['NAME'])) == 0:
        user_input = input('''
            ejecute en un shell de mysql:
                ALTER TABLE tagging_tag MODIFY COLUMN `usage` int(10) unsigned;
            si todo funciono bien presione c y ENTER para continuar o cualquier
            otra tecla para salir.''')
        if user_input == 'c':
            data = None

            with open(FILE_NAME, buffering=1000000, mode="r") as read_file:
                data = json.load(read_file)

                count = 1
                with transaction.commit_on_success():
                    for item in data:
                        new_agency = None
                        new_photograper = None
                        if item['model'] == 'photologue.photo':
                            print(str(item))
                            photo = p_photo.objects.get(id=item['pk'])
                            old_photographer = p_photographer.objects.get(
                                id=item['fields']['photographer']
                            ) if item['fields']['photographer'] is not None \
                                else None
                            if old_photographer is not None:
                                new_photograper, created = \
                                    pl_photographer.objects.get_or_create(
                                        name=old_photographer.name,
                                        defaults={
                                            'name': old_photographer.name,
                                            'email': old_photographer.email,
                                            'date_created':
                                                old_photographer.date_created
                                        })
                            old_agency = p_agency.objects.get(
                                id=item['fields']['agency']
                            ) if item['fields']['agency'] is not None else None
                            if old_agency is not None:
                                new_agency, created = \
                                    pl_agency.objects.get_or_create(
                                        name=old_agency.name,
                                        defaults={
                                            'name': old_agency.name,
                                            'info': old_agency.info,
                                            'date_created':
                                                old_agency.date_created})
                            photo_extended, created = \
                                PhotoExtended.objects.get_or_create(
                                    image=photo,
                                    defaults={
                                        'type': photo.type,
                                        'image': photo,
                                        'agency': new_agency,
                                        'photographer': new_photograper})
                            photo_extended.save()
                            print(
                                "\033[92m {}\033[00m".format(
                                    'photo_extended numero ' + str(count) +
                                    ' salvado ' + '*' * 10))
                            count += 1
        else:
            return
    else:
        print('error')
        return


loaddata()
