# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from adzone.models import BannerAd
# 150kb - 150165
MAX_UPLOAD_SIZE = "150165"


class UploadFileForm(forms.ModelForm):

    def clean(self):
        self.check_file(self)
        return self.cleaned_data

    def check_file(self, form):
        content = None
        #if 'content' in self.data:
        content = self.cleaned_data["content"]
        mobile_content = None
        #if 'mobile_content' in self.data:
        mobile_content = self.cleaned_data["mobile_content"]

        content_excedeed, mobile_content_excedeed = False, False
        if content:
            content_excedeed = content.size > int(MAX_UPLOAD_SIZE)
        if mobile_content:
            mobile_content_excedeed = mobile_content.size > int(MAX_UPLOAD_SIZE)
        # import pdb; pdb.set_trace()
        if content_excedeed and mobile_content_excedeed:
            msg_details = u"'Banner escritorio y el Banner móvil' tienen cada uno "
            msg = u"El " + msg_details + u" un tamaño mayor al máximo permitido (150kb). " + \
                  u"Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["content"] = self.error_class([msg])
            form._errors["mobile_content"] = self.error_class([msg])
            del self.cleaned_data["content"]
            del self.cleaned_data["mobile_content"]
        elif content_excedeed:
            msg_details = u"'Banner escritorio' tiene"
            msg = u"El " + msg_details + u" un tamaño mayor al máximo permitido (150kb). " + \
                  u"Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["content"] = self.error_class([msg])
            del self.cleaned_data["content"]
        elif mobile_content_excedeed:
            msg_details = u"'Banner móvil' tiene"
            msg = u"El " + msg_details + u" un tamaño mayor al máximo permitido (150kb). " + \
                  u"Por favor, utiliza un banner de un tamaño menor a 150kb."
            form._errors["mobile_content"] = self.error_class([msg])
            del self.cleaned_data["mobile_content"]

    class Meta:
        model = BannerAd
