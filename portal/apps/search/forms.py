# -*- coding: utf-8 -*-

from django.forms import ModelForm

from .models import Search


class SearchForm(ModelForm):

    class Meta:
        model = Search
        fields = "__all__"
