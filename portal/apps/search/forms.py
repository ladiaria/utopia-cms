# -*- coding: utf-8 -*-
from models import Search

from django.forms import ModelForm


class SearchForm(ModelForm):
    """Search form."""

    class Meta:
        model = Search
        fields = "__all__"
