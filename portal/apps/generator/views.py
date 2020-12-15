# -*- coding: utf-8 -*-
from forms import ContributionForm

from decorators import render_response

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

to_response = render_response('generator/templates/')

@login_required
@to_response
def contribute(request):
    contribution_form = ContributionForm()
    if request.method == 'POST':
        contribution_form = ContributionForm(request.POST)
        if contribution_form.is_valid():
            contribution_form.save()
    return 'contribute.html', {'form': contribution_form}
