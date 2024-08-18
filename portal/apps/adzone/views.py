# -*- coding: utf-8 -*-

# © Copyright 2009 Andre Engelbrecht. All Rights Reserved.
# This script is licensed under the BSD Open Source Licence
# Please see the text file LICENCE for more information
# If this script is distributed, it must be accompanied by the Licence
#
# Modifications made in utopia-cms (TODO: include them and the BSD Licence that the original author ask for)


from time import time

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.utils import timezone

from django_user_agents.utils import get_user_agent

from apps import mongo_db

from decorators import render_response

from signupwall.utils import get_ip
from adzone.models import AdBase


to_response = render_response('adzone/templates/adzone/')


@never_cache
def ad_view(request, id, tracking=None):
    """ Record the click in the mongo database, then redirect to ad url """
    ad = get_object_or_404(AdBase, id=id)
    if settings.ADZONE_LOG_AD_CLICKS:
        mongo_db.adzone_clicks.insert_one({'ad': ad.id, 'click_date': timezone.now(), 'source_ip': get_ip(request)})
    return HttpResponseRedirect(
        (ad.mobile_url if ad.mobile_url and get_user_agent(request).is_mobile else ad.url) % {'timestamp': time()}
    )


@never_cache
@to_response
def ad_content(request):
    """ render ad content to be filled by ajax request """
    return 'ad_content.html'
