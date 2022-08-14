# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals
from django import forms
from .models import EpubFile


class UploadEpubForm(forms.ModelForm):
    """Upload files with this form"""
    def __init__(self, *args, **kwargs):
        super(UploadEpubForm, self).__init__(*args, **kwargs)
        self.fields['f'].error_messages = {'required': 'Por favor seleccione un archivo Epub.'}
        self.fields['section'].error_messages = {'required': 'Debe seleccionar una sección donde se crearan los articulos'}

    class Meta:
        model = EpubFile
        fields = "__all__"


class EpubChangeSectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(EpubChangeSectionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = EpubFile
        fields = "__all__"
