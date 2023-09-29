# -*- coding: utf-8 -*-
from django import forms

from .models import BannerAd


MAX_UPLOAD_SIZE = "150165"  # 150kb


class UploadFileForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        self.check_file(self)
        return self.cleaned_data

    def check_file(self, form):
        content = self.cleaned_data.get("content")
        mobile_content = self.cleaned_data.get("mobile_content")

        content_excedeed, mobile_content_excedeed = False, False
        if content:
            content_excedeed = content.size > int(MAX_UPLOAD_SIZE)
        if mobile_content:
            mobile_content_excedeed = mobile_content.size > int(MAX_UPLOAD_SIZE)
        if content_excedeed and mobile_content_excedeed:
            msg_details = "'Banner escritorio y el Banner móvil' tienen cada uno "
            msg = "El " + msg_details + " un tamaño mayor al máximo permitido (150kb). " + \
                  "Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["content"] = self.error_class([msg])
            form._errors["mobile_content"] = self.error_class([msg])
            del self.cleaned_data["content"]
            del self.cleaned_data["mobile_content"]
        elif content_excedeed:
            msg_details = "'Banner escritorio' tiene"
            msg = "El " + msg_details + " un tamaño mayor al máximo permitido (150kb). " + \
                  "Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["content"] = self.error_class([msg])
            del self.cleaned_data["content"]
        elif mobile_content_excedeed:
            msg_details = "'Banner móvil' tiene"
            msg = "El " + msg_details + " un tamaño mayor al máximo permitido (150kb). " + \
                  "Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["mobile_content"] = self.error_class([msg])
            del self.cleaned_data["mobile_content"]

    class Meta:
        model = BannerAd
        fields = '__all__'
