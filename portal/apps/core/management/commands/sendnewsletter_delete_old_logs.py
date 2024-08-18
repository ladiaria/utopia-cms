# -*- coding: utf-8 -*-
import os

from sortedcontainers import SortedList

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Group files in SENDNEWSLETTER_LOGFILE dir by pattern, sort them by date pattern and keep only the last N files by
    group, getting N from settings by NL name (default=5).
    """

    def handle(self, *args, **options):
        kept, keep = {}, getattr(settings, 'SENDNEWSLETTER_LOGFILE_KEEP', {})
        for logfileext in os.listdir(os.path.dirname(settings.SENDNEWSLETTER_LOGFILE)):
            logfile, ext = os.path.splitext(logfileext)
            nlname, nldate = logfile.split('-')
            sl = kept.get(nlname, SortedList())
            sl.add(nldate)
            if len(sl) > keep.get(nlname, 5):
                # remove oldest
                oldest = sl.pop(0)
                os.unlink(settings.SENDNEWSLETTER_LOGFILE % (nlname, oldest))
            kept[nlname] = sl
