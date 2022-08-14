# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.forms import ModelForm

from .models import Search


class SearchForm(ModelForm):

    class Meta:
        model = Search
        fields = "__all__"
