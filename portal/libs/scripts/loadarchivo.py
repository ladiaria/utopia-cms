#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
from datetime import date, timedelta
from string import uppercase, lower
import os
import re
import shutil
import sys
import traceback

dir = os.path.dirname(os.path.abspath(__file__))
# >>> len('/libs/scripts')
# >>> 13
PROJECT_ABSOLUTE_DIR = dir[:-13]
sys.path.insert(0, PROJECT_ABSOLUTE_DIR)

from django.core.management import setup_environ
import settings

setup_environ(settings)

from core.models import Edition, Supplement

LADIARIA_RE = re.compile(r'^ladiaria_\d{8}\.pdf$')
CANARIA_RE = re.compile(r'^ladiaria_\d{8}_canaria.pdf$')
SUPPLEMENT_RE = re.compile(r'^ladiaria_\d{8}_sup_.*\.pdf$')
CANARIA_SUPPLEMENT_RE = re.compile(r'^ladiaria_\d{8}_canaria_sup_.*\.pdf$')
SUPS = (
    ('ag', 'agenda_global'),
    ('cn', 'cine_nacional'),
    ('cp', 'puerto'),
    ('cu', 'cumbre'),
    ('ed', 'educacion'),
    ('el', 'circuito_elecciones_imm'),
    ('en', 'energia'),
    ('iv', 'ivc'),
    ('li', 'los_informantes'),
    ('ma', 'medio_ambiente'),
    ('me', 'mercosur'),
    ('pa', 'patrimonio'),
    ('rn', 'rn'),
    ('rr', 'rock'),
    ('sa', 'salud'),
    ('tc', 'catalogo_tarjeta_cultural'),
    ('uv', 'el_uruguay_que_viene'),
    ('yf', 'yo_firme'),)
MONTHS = [('01', 'enero'),
          ('02', 'febrero'),
          ('03', 'marzo'),
          ('04', 'abril'),
          ('05', 'mayo'),
          ('06', 'junio'),
          ('07', 'julio'),
          ('08', 'agosto'),
          ('09', 'setiembre'),
          ('10', 'octubre'),
          ('11', 'noviembre'),
          ('12', 'diciembre')]

def get_edition_from_date(type, from_date):
    if isinstance(from_date, (str, unicode)):
        pubdate = date(*time.strptime(date_str, '%Y%m%d')[:3])
    elif isinstance(from_date, date):
        pubdate = from_date
    try:
        return Edition.objects.get(name=type, date_published=pubdate)
    except Edition.DoesNotExist:
        return None

def strip_media(path):
    from django.conf import settings

    media = settings.MEDIA_ROOT
    return path.replace(media, '')

def mkeditiondir(for_date):
    dest_path = os.path.join(PROJECT_ABSOLUTE_DIR, 'media', 'editions', for_date.strftime('%Y%m%d'))
    if not os.path.exists(dest_path):
        os.mkdir(dest_path)
    return dest_path

def format_fname(fname):
    fname = fname.replace('ladiaria_', 'la_diaria-')
    nre = re.compile(r'_\d{1,3}\.pdf$')
    split = nre.split(fname)[0]
    if '_canaria' in fname:
        fname = fname.replace('_canaria', '')
        fname = fname.replace('la_diaria-', 'la_diaria_canaria-')
    if '_sup_' in fname:
        fname = fname.replace('_sup_', '-')
    if not split.endswith('.pdf'):
        fname = '%s.pdf' % split
    return fname

def save_edition(type, file_path, today):
    if not Edition.objects.filter(name=type, date_published=today).count():
        dest_file = file_path[file_path.rfind('/')+1:]
        dest_path = os.path.join(mkeditiondir(today), format_fname(dest_file))
        shutil.copy(file_path, dest_path)
        e = Edition(name=type, pdf=strip_media(dest_path), date_published=today)
        try:
            e.save()
            return True
        except Exception, e:
            traceback.print_exc()
            print dest_path
            return False
    else:
        # print 'Existe edición para %s' % today.strftime('%Y.%m.%d')
        return False

def save_supplement(file_path, edition):
    if not edition:
        print 'Missing edition for %s' % file_path[file_path.rfind('/'):]
        return False
    for sup_name in SUPS:
        if sup_name[1] in file_path:
            name = sup_name[0]
    headline = '!'
    if not Supplement.objects.filter(name=name, edition=edition).count():
        dest_path = os.path.join(mkeditiondir(edition.date_published), format_fname(file_path))
        shutil.copy(file_path, dest_path)
        s = Supplement(name=name, headline=headline,
            pdf=format_fname(strip_media(file_path)), edition=edition)
        try:
            s.save()
            return True
        except Exception, e:
            print '%s: %s' % (dest_path, e)
            return False
    else:
        # print 'Ya existe suplemento %s (%s)' % (name, today.strftime('%Y.%m.%d'))
        return False

def save(dir, fname, today):
    file_path = os.path.join(dir, fname)
    if LADIARIA_RE.findall(fname):
        # print 'la diaria: %s' % fname
        return save_edition(0, file_path, today)
    if CANARIA_RE.findall(fname):
        # print 'la diaria canaria: %s' % fname
        return save_edition(1, file_path, today)
    if SUPPLEMENT_RE.findall(fname):
        # print 'suplemento la diaria: %s' % fname
        return save_supplement(file_path, get_edition_from_date(0, today))
    if CANARIA_SUPPLEMENT_RE.findall(fname):
        # print 'suplemento la diaria canaria: %s' % fname
        return save_supplement(1, file_path, today)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Invalid arguments'
        sys.exit(1)
    from_date = date(2006, 03, 20)
    to_date = date(2009, 06, 16)
    current_date = from_date
    curr_dir = None
    while current_date <= to_date:
        if current_date.weekday() in (0, 1, 2, 3, 4):
            if current_date.day == 1 or curr_dir is None:
                month = MONTHS[current_date.month-1]
                # print '%s de %i' % (month[1], current_date.year)
                curr_dir = os.path.join(sys.argv[1], str(current_date.year), '%s_%s' % month)
                try:
                    contents = os.listdir(curr_dir)
                except OSError:
                    break
                contents.sort()
                # print '%i/\n  %s_%s/' % (current_date.year, month[0], month[1])
                # for f in contents:
                #     print '    %s' % f
            for filename in contents:
                if filename.startswith('ladiaria_%s' % (current_date.strftime('%Y%m%d'))):
                    save(curr_dir, filename, current_date)
        current_date += timedelta(1)
