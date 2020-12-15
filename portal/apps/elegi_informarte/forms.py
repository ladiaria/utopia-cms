# -*- coding: utf-8 -*-

from django import forms
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import mail_managers
from django.contrib.auth.models import User

from models import Serie, Suscripcion, Attribution


class SuscripcionForm(forms.ModelForm):
    credencial_serie = forms.CharField(min_length=3, max_length=3)
    not_valid_msg = u"tu credencial no es válida"

    def clean_credencial_serie(self):
        credencial_serie = self.cleaned_data.get('credencial_serie')
        if credencial_serie.isalpha():
            credencial_serie = credencial_serie.upper()
            try:
                return Serie.objects.get(serie=credencial_serie)
            except Serie.DoesNotExist:
                raise forms.ValidationError(self.not_valid_msg)
        else:
            raise forms.ValidationError(self.not_valid_msg)

    def clean_credencial_numero(self):
        credencial_numero = self.cleaned_data.get('credencial_numero')
        if credencial_numero > 0:
            return credencial_numero
        else:
            raise forms.ValidationError(self.not_valid_msg)

    class Meta:
        model = Suscripcion
        fields = ('subscriber', 'credencial_serie', 'credencial_numero')


class SuscripcionEmailForm(SuscripcionForm):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if len(email) <= 30:
            email = email.lower()
            msg = u'El email ingresado ya posee una cuenta de usuario.'
            try:
                u = User.objects.get(email__iexact=email)
                if u.subscriber.is_subscriber():
                    raise forms.ValidationError(msg)
                else:
                    raise forms.ValidationError('user_has_free_account')
            except MultipleObjectsReturned:
                mail_managers("Multiple email in users", email)
                raise forms.ValidationError(msg)
            except User.DoesNotExist:
                if User.objects.filter(username__iexact=email).exists():
                    mail_managers("Multiple username in users", email)
                    msg = u'El email ingresado no puede ser utilizado.'
                    raise forms.ValidationError(msg)
                return email
        else:
            raise forms.ValidationError(
                u'Email demasiado largo, se permiten hasta 30 caracteres.')

    class Meta:
        model = Suscripcion
        fields = ('credencial_serie', 'credencial_numero')


class AttributionAmountForm(forms.Form):
    radioAmounts = forms.TypedChoiceField(
        choices=((400, 400), (800, 800), (1200, 1200), (1600, 1600)),
        required=False, coerce=int)
    amount = forms.IntegerField(
        required=False, min_value=401, max_value=1000000)

    def clean(self):
        cleaned_data = super(AttributionAmountForm, self).clean()
        radioAmounts = cleaned_data.get("radioAmounts")
        amount = cleaned_data.get("amount")
        if not radioAmounts and not amount:
            raise forms.ValidationError(
                u'Se debe seleccionar o ingresar algún monto válido')
        return cleaned_data


class AttributionForm(forms.ModelForm):
    class Meta:
        model = Attribution
