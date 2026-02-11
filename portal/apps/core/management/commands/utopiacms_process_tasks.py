# -*- coding: utf-8 -*-
# utopia-cms 2023. Aníbal Pacheco.

from django.db.utils import OperationalError

from background_task.management.commands.process_tasks import Command as ProcessTasksCommand


class Command(ProcessTasksCommand):
    help = "Wrapper for process_tasks that also handle exceptions"

    def handle(self, *args, **options):
        try:
            super().handle(*args, **options)
        except OperationalError:
            pass
