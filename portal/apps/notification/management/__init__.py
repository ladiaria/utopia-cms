# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from django.conf import settings
from django.db.models import signals
from django.utils.translation import ugettext_noop as _

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification

    def create_notice_types(app, created_models, verbosity, **kwargs):
        notification.create_notice_type("follow", _(u"Guardaste un artículo para leer luego."), _("default notice"))
    signals.post_migrate.connect(create_notice_types, sender=notification)
else:
    print("Skipping creation of NoticeTypes as notification app not found")