# -*- coding: utf-8 -*-
from django.conf import settings
from django import forms
from django.utils.safestring import mark_safe
from .models import BannerAd


MAX_UPLOAD_SIZE = getattr(settings, "ADZONE_MAX_UPLOAD_SIZE", 150)
MAX_UPLOAD_SIZE_VERBOSE = f"{MAX_UPLOAD_SIZE}kb"


class UploadFileForm(forms.ModelForm):
    content_dimensions = "970x250"
    mobile_content_dimensions = "300x250"

    def content_help(self, dimensions):
        return mark_safe(
            f"Dimensiones: {dimensions}</br>Tamaño máximo permitido: {MAX_UPLOAD_SIZE_VERBOSE}</br>"
            "Formato: JPEG/JPG, GIF, PNG, WEBP"
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].help_text = self.content_help(self.content_dimensions)
        self.fields['mobile_content'].help_text = self.content_help(self.mobile_content_dimensions)

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get("content")
        mobile_content = cleaned_data.get("mobile_content")
        content_excedeed, mobile_content_excedeed = False, False
        if content:
            content_excedeed = content.size > MAX_UPLOAD_SIZE * 1024
        if mobile_content:
            mobile_content_excedeed = mobile_content.size > MAX_UPLOAD_SIZE * 1024
        if content_excedeed and mobile_content_excedeed:
            msg_details = "'Banner escritorio' y el 'Banner móvil' tienen cada uno "
            msg = (
                f"El {msg_details} un tamaño mayor al máximo permitido ({MAX_UPLOAD_SIZE_VERBOSE}). "
                f"Por favor, utilice banners de tamaño menor a {MAX_UPLOAD_SIZE_VERBOSE}."
            )
            self.add_error("content", msg)
            self.add_error("mobile_content", msg)
        elif content_excedeed:
            msg_details = "'Banner escritorio' tiene"
            msg = (
                f"El {msg_details} un tamaño mayor al máximo permitido ({MAX_UPLOAD_SIZE_VERBOSE}). "
                f"Por favor, utilice un banner de un tamaño menor a {MAX_UPLOAD_SIZE_VERBOSE}."
            )
            self.add_error("content", msg)
        elif mobile_content_excedeed:
            msg_details = "'Banner móvil' tiene"
            msg = (
                f"El {msg_details} un tamaño mayor al máximo permitido ({MAX_UPLOAD_SIZE_VERBOSE}). "
                f"Por favor, utilice un banner de un tamaño menor a {MAX_UPLOAD_SIZE_VERBOSE}."
            )
            self.add_error("mobile_content", msg)
        return self.cleaned_data

    class Meta:
        model = BannerAd
        fields = '__all__'
