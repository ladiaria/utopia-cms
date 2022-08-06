# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.forms import ModelForm

from events.models import Attendant


class AttendantForm(ModelForm):
    class Meta:
        model = Attendant
        exclude = ('subscriber', )


class AttendantFormRender(AttendantForm):
    class Meta(AttendantForm.Meta):
        exclude = ('activity', )
