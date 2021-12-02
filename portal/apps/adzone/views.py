# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence
from time import time
from datetime import datetime

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache

from apps import adzone_mdb

from decorators import render_response

from signupwall.utils import get_ip
from adzone.models import AdBase


to_response = render_response('adzone/templates/adzone/')


@never_cache
def ad_view(request, id, tracking=None):
    """ Record the click in the mongo database, then redirect to ad url """
    ad = get_object_or_404(AdBase, id=id)
    if settings.ADZONE_LOG_AD_CLICKS:
        adzone_mdb.clicks.insert_one({'ad': ad.id, 'click_date': datetime.now(), 'source_ip': get_ip(request)})
    return HttpResponseRedirect(
        (ad.mobile_url if ad.mobile_url and request.flavour == 'mobile' else ad.url) % {'timestamp': time()}
    )


@never_cache
@to_response
def ad_content(request):
    """ render ad content to be filled by ajax request """
    return 'ad_content.html'
