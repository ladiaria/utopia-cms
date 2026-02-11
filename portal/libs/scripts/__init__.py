# useful functions for development and test
from django.conf import settings
from django.contrib.auth.models import User

from thedaily.models import Subscriber


def debug_prt(obj):
    if settings.DEBUG:
        print(obj)


def delete_phone(subscriber_id=None):
    try:
        debug_prt(Subscriber.objects.filter(id__in=[subscriber_id]).update(phone=""))
    except Exception as exc:
        debug_prt(exc)


def delete_user(qarg, by_subscriber_id=False):
    try:
        if isinstance(qarg, str):
            filter_kwargs = {"email": qarg}
        else:
            filter_kwargs = {"%sid__in" % ("subscriber__" if by_subscriber_id else ""): [qarg]}
        debug_prt(User.objects.filter(**filter_kwargs).delete())
    except Exception as exc:
        debug_prt(exc)
