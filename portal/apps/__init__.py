# coding:utf8
"""
utopia-cms, 2018-2021, Aníbal Pacheco

The function register_actstream_model defined here was taken from [1] to fix

[1] https://github.com/justquick/django-activity-stream/issues/48#issuecomment-49170647
"""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from actstream import registry as activity_stream_registry
from actstream.models import Action

from django.conf import settings


def register_actstream_model(model_class):
    activity_stream_registry.register(model_class)
    for field in ('actor', 'target', 'action_object'):
        setattr(
            Action,
            'actions_with_%s_%s_as_%s' % (model_class._meta.app_label, model_class._meta.module_name, field),
            None,
        )

try:
    client = MongoClient(serverSelectionTimeoutMS=1000)
    client.server_info()
    global core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb
    core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb = (
        client[settings.CORE_MONGODB_ARTICLEVIEWEDBY] if settings.CORE_MONGODB_ARTICLEVIEWEDBY else None,
        client[settings.CORE_MONGODB_ARTICLEVISITS] if settings.CORE_MONGODB_ARTICLEVISITS else None,
        client[settings.SIGNUPWALL_MONGODB_VISITOR] if settings.SIGNUPWALL_MONGODB_VISITOR else None)
except ServerSelectionTimeoutError:
    core_articleviewedby_mdb = core_articlevisits_mdb = signupwall_visitor_mdb = None
