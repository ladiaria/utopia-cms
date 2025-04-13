import json
import logging

from pywebpush import webpush, WebPushException

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from core.models import DeviceSubscribed


def send_notification_func(msg, tag, url, img_url, user_id):
    def log_error(log_message):
        if settings.DEBUG:
            # In test/production environments (DEBUG=False), do not write this on the output to avoid large outputs if
            # for example this runs in a cron job process.
            log.error(log_message, exc_info=True)
        logfile.error(log_message, exc_info=True)

    # log (logfile also info level)
    log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    h = logging.FileHandler(filename=settings.CORE_PUSH_NOTIFICATIONS_LOGFILE)
    h.setFormatter(log_formatter)

    logfile = logging.getLogger('push_notifications_logfile')
    logfile.propagate = False
    logfile.setLevel(logging.INFO)
    logfile.addHandler(h)

    log = logging.getLogger(__name__)

    if not settings.CORE_PUSH_NOTIFICATIONS_VAPID_PRIVKEY:
        raise CommandError('Private key not set')

    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError("The user with the user_id given was not found")
    else:
        user = None
    subscriptions = list(
        (user.devicesubscribed_set if user else DeviceSubscribed.objects).values_list('subscription_info', flat=True)
    )

    failed, success, opts = 0, 0, settings.CORE_PUSH_NOTIFICATIONS_OPTIONS.copy()
    opts.update(
        {
            'body': msg,
            'tag': str(tag),
            'data': {'link': url + ("?utm_source=push_notification" if settings.PORTAL_USE_UTM_LINKS else "")},
        }
    )
    if img_url:
        opts.update({'image': img_url})
    data = json.dumps(opts)

    for sinfo in subscriptions:
        try:
            subscription_info, vapid_claims = json.loads(sinfo), settings.CORE_PUSH_NOTIFICATIONS_VAPID_CLAIMS.copy()
            if subscription_info["endpoint"].startswith("https://updates.push.services.mozilla.com/"):
                vapid_claims.update({"aud": "https://updates.push.services.mozilla.com"})
            webpush(
                subscription_info=subscription_info,
                data=data,
                vapid_private_key=settings.CORE_PUSH_NOTIFICATIONS_VAPID_PRIVKEY,
                vapid_claims=vapid_claims,
                ttl=60,
            )
            success += 1
        except WebPushException:
            failed += 1
            log_error('device subscribed will be deleted, could not send: ' + sinfo)
            DeviceSubscribed.objects.filter(subscription_info=sinfo).delete()
        except Exception:
            failed += 1
            log_error('could not send to this device: ' + sinfo)

    send_results = "Send results (tag, #sent-ok, #sent-failed): '%s', %d, %d" % (tag, success, failed)
    logfile.info(send_results)
    return send_results


class Command(BaseCommand):
    help = """
        Sends a push notification to all subscribed devices of the user matching the user-id given only. If no user-id
        given, sends the notification to all subscribed devices of all users.
        Ex.: ./manage.py send_notification --msg 'notification msg' --tag tag01 --url https://yoogle.com/ \
            --img-url https://yoogle.com/static/img/logo-utopia.png --user-id 1
    """

    def add_arguments(self, parser):
        parser.add_argument('--msg', required=True, type=str, help='The content of the notification message')
        parser.add_argument('--tag', required=True, type=str, help='The notification tag')
        parser.add_argument('--url', required=True, type=str, help='The notification destination url')
        parser.add_argument('--img-url', dest='img_url', type=str, default=None, help='The notification image url')
        parser.add_argument(
            '--user-id',
            dest='user_id',
            type=int,
            default=None,
            help="Send to all the subscribed devices of this user only",
        )

    def handle(self, *args, **options):
        send_results = send_notification_func(
            options.get('msg'), options.get('tag'), options.get('url'), options.get('img_url'), options.get('user_id')
        )
        if options.get("verbosity") > 1:
            print(send_results)
