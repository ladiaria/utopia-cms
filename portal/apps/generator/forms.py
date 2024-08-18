# -*- coding: utf-8 -*-
from .models import Contribution

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import mail_managers
from django.forms import ModelForm
from django.template.loader import render_to_string


class ContributionForm(ModelForm):

    class Meta:
        model = Contribution
        fields = "__all__"

    def get_body(self, instance):
        site = Site.objects.get(id=getattr(settings, 'SITE_ID'))
        return render_to_string('generator/templates/mail_body.txt', {'apply': instance, 'site': site})

    def save(self, *args, **kwargs):
        instance = super(ContributionForm, self).save(*args, **kwargs)
        mail_managers('Contribución', self.get_body(instance))
