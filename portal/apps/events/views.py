# -*- coding: utf-8 -*-
from .models import Event, Activity
from .forms import AttendantForm, AttendantFormRender
from thedaily.models import Subscriber

from decorators import render_response

from django.shortcuts import get_object_or_404, get_list_or_404

from calendar import Calendar
from datetime import date, timedelta


to_response = render_response('events/templates/')
DAYS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


@to_response
def calendar(request, year=None, month=None):
    if year and month:
        date_object = date(int(year), int(month), 1)
    else:
        date_object = date.today()
    year, month = date_object.year, date_object.month
    events = Event.objects.filter(date__year=year, date__month=month)
    prev, next = get_prev_next(date_object)
    cal = Calendar().itermonthdates(date_object.year, date_object.month)
    return (
        'calendar.html',
        {
            'date': date_object,
            'prev': prev,
            'next': next,
            'days': DAYS,
            'cal': cal,
            'today': date.today(),
            'events': events,
        },
    )


@to_response
def day_detail(request, year, month, day):
    date_object = date(int(year), int(month), int(day))
    events = get_list_or_404(Event, date__year=year, date__month=month, date__day=day)
    return 'day.html', {'day': date_object, 'events': events}


@to_response
def event_detail(request, year, month, day, event_slug):
    event = get_object_or_404(Event, date__year=year, date__month=month, date__day=day, slug=event_slug)
    return 'event.html', {'event': event}


def get_prev_next(date_object):
    this_month = date(date_object.year, date_object.month, 1)
    prev = this_month - timedelta(days=1)
    this_month = date(date_object.year, date_object.month, 28)
    next = this_month + timedelta(days=5)
    return prev, next


@to_response
def published_activities(request):
    """
    Render published activities with an attendance-enter form if the activity is not closed.
    """
    activity_id, form, success = None, None, None
    if request.method == 'POST':
        activity_id = int(request.POST.get('activity'))
        form = AttendantForm(request.POST)
        if form.is_valid():
            attendant = form.save()
            if request.user.is_authenticated():
                try:
                    attendant.subscriber = request.user.subscriber
                    attendant.save()
                except Subscriber.DoesNotExist:
                    pass
            success = True
        else:
            form = AttendantFormRender(request.POST)
            form.is_valid()
    return (
        'published_activities.html',
        {
            'object_list': Activity.objects.filter(published=True),
            'activity_id': activity_id,
            'form': form,
            'success': success,
        },
    )
