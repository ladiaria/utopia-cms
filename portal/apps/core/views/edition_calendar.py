# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from calendar import LocaleHTMLCalendar

from django.utils.timezone import now, datetime
from django.template.loader import render_to_string


class EditionCalendar(LocaleHTMLCalendar,):

    def __init__(self, editions, *args):
        self.editions = self.group_by_day(editions)
        super(EditionCalendar, self).__init__(*args)

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if now().date() == datetime(self.year, self.month, day).date():
                cssclass += ' today'
            if day in self.editions:
                cssclass += ' filled'
                edition = self.editions[day]
                return self.day_cell(
                    cssclass, render_to_string('core/templates/edition/calendar_edition.html', {'edition': edition})
                )
            return self.day_cell(cssclass, day)
        return self.day_cell('noday', '&nbsp;')

    def formatmonth(self, year, month):
        self.year, self.month = int(year), int(month)
        return super(EditionCalendar, self).formatmonth(self.year, self.month)

    def group_by_day(self, editions):
        return dict([(edition.date_published.day, edition) for edition in editions])

    def day_cell(self, cssclass, body):
        return '<td class="%s">%s</td>' % (cssclass, body)
