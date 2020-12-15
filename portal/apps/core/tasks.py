import re

from background_task import background
from background_task.models import Task

from models import update_category_module as ucm


@background(schedule=1)
def update_category_module_task():
    ucm()


def update_category_module():
    """
    Schedule a task only if not exists already a similar not failed task
    """
    if not Task.objects.filter(
        task_name='core.tasks.update_category_module_task', failed_at=None
    ).exists():
        task = update_category_module_task()
        # Need to remove the "apps." at the beggining of the task name
        task.task_name = re.sub(r'^apps\.', '', task.task_name)
        task.save()
