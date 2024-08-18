# -*- coding: utf-8 -*-

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.contrib.auth.decorators import login_required

from decorators import render_response

from .forms import ContributionForm


to_response = render_response('generator/templates/')


@login_required
@to_response
def contribute(request):
    if not getattr(settings, "GENERATOR_ENABLED", True):
        raise Http404
    contribution_form = ContributionForm()
    if request.method == 'POST':
        contribution_form = ContributionForm(request.POST)
        if contribution_form.is_valid():
            contribution_form.save()
    return 'contribute.html', {'form': contribution_form}
