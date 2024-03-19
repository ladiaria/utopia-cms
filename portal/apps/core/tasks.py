from time import sleep
from kombu.exceptions import OperationalError

from django.conf import settings
from django.core.management.base import CommandError

from celeryapp import celery_app

from .actions import update_category_home as update_category_home_func
from .management.commands.send_notification import send_notification_func
from .management.commands.update_article_urls import update_article_urls as update_article_urls_func


@celery_app.task(name="update-category-home")
def update_category_home_task():
    result = update_category_home_func()
    if settings.DEBUG:
        # TODO: log somewhere instead of print in celery worker stdout
        print(result)


@celery_app.task(name="update-article-urls")
def update_article_urls(pub_slug):
    return update_article_urls_func([pub_slug])


@celery_app.task(name="send-push-notification")
def send_push_notification_task(msg, tag, url, img_url, user_id):
    try:
        return send_notification_func(msg, tag, url, img_url, user_id)
    except CommandError as cmd_err:
        # TODO: maybe this exception also can be catched in the admin
        if settings.DEBUG:
            return "ERROR: %s" % cmd_err


@celery_app.task(name="test-sleep-task")
def test_sleep_task(secs=0, feedback_step=None):
    # was used for development only
    secs_remaining = secs
    while secs_remaining > 0:
        sleep_by = feedback_step if feedback_step and feedback_step < secs_remaining else secs_remaining
        sleep(sleep_by)
        secs_remaining -= sleep_by
        if feedback_step and secs_remaining:
            print("still sleeping, %s seconds remaining to wakeup." % secs_remaining)
    print("wokeup, task finished.")
    return "test_sleep_task executed with args: %s%s" % (secs, (", %s" % feedback_step) if feedback_step else "")


@celery_app.task(name="test-task")
def test_task(test_arg=None):
    # was used for development only
    return "test_task executed with arg: %s" % test_arg


def update_category_home():
    try:
        update_category_home_task.delay()
    except OperationalError as oe_exc:
        if settings.DEBUG:
            print("ERROR: update_category_home_task could not be started (%s)" % oe_exc)


def send_push_notification(msg, tag, url, img_url, user):
    send_push_notification_task.delay(msg, tag, url, img_url, getattr(user, 'id', None))
