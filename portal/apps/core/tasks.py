from __future__ import absolute_import
from __future__ import unicode_literals
import re

from background_task import background
from background_task.models import Task

from .models import update_category_home as uch


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
