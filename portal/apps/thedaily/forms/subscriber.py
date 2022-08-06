# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, HTML

from django.conf import settings
from django.forms import ModelForm, ValidationError
from django.core.mail import mail_managers
from django.contrib.auth.models import User

from thedaily.models import Subscriber
from thedaily.forms import RE_ALPHANUM, EmailInput


class ProfileForm(ModelForm):
    # TODO: init method here
    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Fieldset(u'Datos de suscriptor', 'document', 'phone'),
        Fieldset(u'Ubicación', 'country', 'province', 'city', 'address'),
        HTML('</div>'),     # close div opened in edit_profile.html
        HTML('{% include "profile/submit.html" %}'),
        HTML(
            '{%% include "%s" %%}' % getattr(settings, 'THEDAILY_SUBSRIPTIONS_TEMPLATE', 'profile/suscripciones.html')
        ),
        Field('newsletters', template='profile/newsletters.html'),
        Field('category_newsletters', template='profile/category_newsletters.html'),
        HTML(
            '''
            <section id="ld-comunicaciones" class="ld-block section scrollspy">
              <h2 class="ld-title ld-title--underlined">Comunicaciones</h2>
            '''
        ),
        Field('allow_news', template=getattr(settings, 'THEDAILY_ALLOW_NEWS_TEMPLATE', 'profile/allow_news.html')),
        Field('allow_promotions', template='profile/allow_promotions.html'),
        Field('allow_polls', template='profile/allow_polls.html'),
        HTML('</section>'),
    )

    class Meta:
        model = Subscriber
        # TODO: use fields instead of exclude
        exclude = (
            'contact_id',
            'user',
            'name',
            'profile_photo',
            'downloads',
            'pdf',
            'lento_pdf',
            'ruta',
            'plan_id',
            'ruta_lento',
            'ruta_fs',
            'last_paid_subscription',
        )


class UserForm(ModelForm):
    # TODO: init method here
    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(Fieldset(u'Datos personales', 'first_name', 'last_name', 'email'))

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'email': EmailInput(
                attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
            ),
        }

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        email = cleaned_data.get('email')

        if User.objects.filter(email__iexact=email).exclude(id=self.instance.id).exists():
            msg = u'El email ingresado ya posee una cuenta de usuario.'
            msg += u' <a href="/usuarios/entrar">Ingresar</a>.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        if User.objects.filter(username__iexact=email).exclude(id=self.instance.id).exists():
            mail_managers("Multiple username in users", email)
            msg = u'El email ingresado no puede ser utilizado.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        return cleaned_data

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            raise ValidationError(
                u'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
            )
        return first_name

    def clean_email(self):
        # TODO: check if length should be validated here
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError(u'La dirección de correo electrónico no puede ser vacia.')
        return email
