from __future__ import absolute_import
from __future__ import unicode_literals

import re

from background_task import background
from background_task.models import Task

from django.conf import settings
from django.core.management.base import CommandError

from .models import update_category_home as uch
from .management.commands.send_notification import send_notification_func


@background(schedule=1)
def update_category_home_task():
    uch()


def update_category_home():
    """
    Schedule a task only if not exists already a similar not failed task
    """
    if not Task.objects.filter(
        task_name='core.tasks.update_category_home_task', failed_at=None
    ).exists():
        task = update_category_home_task()
        # Need to remove the "apps." at the beggining of the task name
        task.task_name = re.sub(r'^apps\.', '', task.task_name)
        task.save()


@background(schedule=1)
def send_push_notification_task(msg, tag, url, img_url, user_id):
    try:
        send_notification_func(msg, tag, url, img_url, user_id)
    except CommandError as cmd_err:
        if settings.DEBUG:
            print(cmd_err)


def send_push_notification(msg, tag, url, img_url, user):
    task = send_push_notification_task(msg, tag, url, img_url, getattr(user, 'id', None))
    # Need to remove the "apps." at the beggining of the task name
    task.task_name = re.sub(r'^apps\.', '', task.task_name)
    task.save()
