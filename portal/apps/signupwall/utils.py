from __future__ import unicode_literals
from builtins import str
import unicodedata
import socket

from django.conf import settings


def get1st_valid_ip_address(ip_addresses):
    try:
        ip_address = ip_addresses.split(', ')[0]
        try:
            socket.inet_pton(socket.AF_INET6, ip_address)
            return ip_address
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET, ip_address)
                return ip_address
            except socket.error:
                return None
    except (AttributeError, IndexError):
        return None


def get_ip(request):
    """
    Retrieves the remote IP address from the request data. If the user is behind a proxy, they may have a
    comma-separated list of IP addresses, so we need to account for that. In such a case, only the first IP in the list
    will be retrieved. Also, some hosts that use a proxy will put the REMOTE_ADDR into HTTP_X_FORWARDED_FOR.
    This will handle pulling back the IP from the proper place.
    But first of all be aware of cloudflare (HTTP_CF_CONNECTING_IP)
    """

    # if neither header contain a value, just use local loopback
    ip_addresses = request.headers.get(
        'cf-connecting-ip', request.headers.get('x-forwarded-for', request.META.get('REMOTE_ADDR', '127.0.0.1'))
    )
    if ip_addresses:
        # make sure we have one and only one IP
        ip_address = get1st_valid_ip_address(ip_addresses)
        if not ip_address:
            # no IP, probably from some dirty proxy or other device throw in some bogus IP
            ip_address = '10.0.0.1'
        return ip_address
    else:
        return ip_addresses


def get_timeout():
    """
    Gets any specified timeout from the settings file, or use 10 minutes by
    default
    """
    return getattr(settings, 'TRACKING_TIMEOUT', 10)


def get_cleanup_timeout():
    """
    Gets any specified visitor clean-up timeout from the settings file, or
    use 24 hours by default
    """
    return getattr(settings, 'TRACKING_CLEANUP_TIMEOUT', 24)


def u_clean(s):
    """A strange attempt at cleaning up unicode"""

    uni = ''
    try:
        # try this first
        uni = str(s).decode('iso-8859-1')
    except UnicodeDecodeError:
        try:
            # try utf-8 next
            uni = str(s).decode('utf-8')
        except UnicodeDecodeError:
            # last resort method... one character at a time (ugh)
            if s and type(s) in (str, str):
                for c in s:
                    try:
                        uni += unicodedata.normalize('NFKC', str(c))
                    except UnicodeDecodeError:
                        uni += '-'

    return uni.encode('ascii', 'xmlcharrefreplace')
