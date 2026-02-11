#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
from builtins import str
from os.path import abspath, dirname
import sys

dir = dirname(abspath(__file__))

PROJECT_ABSOLUTE_DIR = '%s/portal' % dir[:dir.rfind('/portal')]
sys.path.insert(0, PROJECT_ABSOLUTE_DIR)

from django.core.management import setup_environ
import settings

setup_environ(settings)

from thedaily.models import Subscriber
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

import re

DOCUMENT_RE = re.compile(r'\d')

def get_phone(varchar):
    try:
        if int(varchar) == 0:
            return None
    except:
        return None
    return varchar

def load_csv(csv_file):
    handler = open(csv_file, 'r')
    for line in handler.readlines():
        bits = [chunk.strip().strip('"').strip() for chunk in line.split(',')]
        name_slug = slugify(bits[1]).replace('-', '_')[:30]
        if User.objects.filter(username=name_slug).count() == 0:
            user = User(username=name_slug)
            user.is_active = False
            user.set_unusable_password()
            try:
                user.save()
            except Exception as e:
                print('User', str(e))
                print(bits)
            if user.id:
                document = ''.join(DOCUMENT_RE.findall(bits[2])) if bits[2] not in ('', '\N') else ''
                subscriber = Subscriber(user=user)
                subscriber.contact_id = int(bits[0])
                subscriber.name = bits[1]
                subscriber.document = document
                subscriber.phone = get_phone(bits[3])
                try:
                    subscriber.save()
                except Exception as e:
                    print('Subscriber', str(e))
                    print(bits)
                    user.delete()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Invalid arguments.')
        sys.exit(1)
    load_csv(sys.argv[1])
