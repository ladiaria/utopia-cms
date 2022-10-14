import logging
import sys
import json

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from django.conf import settings
from core.models import DeviceSubscribed


log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%H:%M:%S')
logger = logging.getLogger(__name__)

err_handler = logging.StreamHandler(sys.stderr)
err_handler.setFormatter(log_formatter)
logger.addHandler(err_handler)


@api_view(['DELETE', 'POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def subscribe(request):
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

    if request.method == 'POST':
        subscription_info = request.data
        if 'endpoint' not in subscription_info:
            log_error('A subscription sent without endpoint.')
            return Response({'subscribed': 'false'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            DeviceSubscribed.objects.create(user=request.user, subscription_info=json.dumps(subscription_info))
        except Exception:
            log_error("Exception occurred")
            return Response({'subscribed': 'false'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'subscribed': 'true'})
    elif request.method == 'DELETE':
        subscription_info = json.dumps(request.data)
        device_subscribed = DeviceSubscribed.objects.filter(user=request.user, subscription_info=subscription_info)
        if device_subscribed:
            device_subscribed.delete()
        else:
            logfile.warning(
                'DELETE request, DeviceSubscribed not found for the subscription info received: ' + subscription_info
            )
        return Response({'unsubscribed': 'true'})
