# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date
import re

from django.template.defaultfilters import slugify
from django.conf import settings
from django.http import UnreadablePostError
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.core.mail import mail_managers
from django.forms import (
    Form,
    ModelForm,
    BooleanField,
    CharField,
    EmailField,
    PasswordInput,
    TextInput,
    HiddenInput,
    ChoiceField,
    ValidationError,
)
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned

from captcha.fields import ReCaptchaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, BaseInput, Field, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from crispy_forms.utils import get_template_pack

from thedaily.models import Subscription, Subscriber

from libs.tokens.email_confirmation import default_token_generator


CSS_CLASS = 'form-input1'
RE_ALPHANUM = re.compile(u'^[A-Za-z0-9ñüáéíóúÑÜÁÉÍÓÚ _\'.\-]*$')


def check_password_strength(password):
    if len(password) < 6:
        return False
    else:
        return True


class Submit(BaseInput):
    """ Use a custom submit because crispy's adds btn and btn-primary in the class attribute """
    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'submit submitButton' if get_template_pack() == 'uni_form' else ''
        super(Submit, self).__init__(*args, **kwargs)


class PhoneInput(TextInput):
    input_type = 'tel'


class EmailInput(TextInput):
    input_type = 'email'


class LoginForm(Form):
    """ Login form """
    name_or_mail = CharField(label='Email', widget=TextInput(attrs={'class': CSS_CLASS}))
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(attrs={'class': CSS_CLASS, 'autocomplete': 'current-password', 'autocapitalize': 'none'}),
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'account_login'
        self.helper.form_style = 'inline'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('account-login')
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.render_unmentioned_fields = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Field(
                'name_or_mail',
                title="Ingresá tu nombre de usuario o email",
                template='materialize_css_forms/layout/email-login.html',
            ),
            Field(
                'password',
                title="Contraseña. Si no la recordás la podés restablecer.",
                template='materialize_css_forms/layout/password-login.html',
            ),
        )
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = self.data
        USER_PASS_ERROR = 'Email y/o contraseña incorrectos.'
        nom = data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                self.username = User.objects.get(email__iexact=nom).username
            except Exception:
                raise ValidationError(USER_PASS_ERROR)
        else:
            try:
                self.username = Subscriber.objects.get(name__iexact=nom).user.username
            except Exception:
                if User.objects.filter(username__iexact=nom).count():
                    self.username = nom
                else:
                    raise ValidationError(USER_PASS_ERROR)
        return data


terms_and_conditions_field = BooleanField(label='Leí y acepto los <a>términos y condiciones</a>', required=False)
terms_and_conditions_layout_tuple = (
    Field('terms_and_conditions', css_class='filled-in'),
) if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID else ()


class SignupForm(ModelForm):
    """ Formulario con campos para crear una instancia del modelo User """
    first_name = CharField(
        label='Nombre',
        widget=TextInput(attrs={'autocomplete': 'name', 'autocapitalize': 'sentences', 'spellcheck': 'false'}),
    )
    email = EmailField(
        label='Email',
        widget=EmailInput(
            attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
        ),
    )
    phone = CharField(
        label='Teléfono',
        widget=PhoneInput(attrs={'class': 'textinput textInput', 'autocomplete': 'tel', 'spellcheck': 'false'}),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conditions = terms_and_conditions_field
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'signup_form'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.render_unmentioned_fields = False
        self.helper.form_tag = True
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            *('first_name', 'email', 'phone', Field('password', template='materialize_css_forms/layout/password.html'))
            + terms_and_conditions_layout_tuple
            + (
                'next_page',
                HTML('<div class="align-center">'),
                Submit('save', 'Crear cuenta', css_class='ut-btn ut-btn-l'),
                HTML('</div">'),
            )
        )
        super(SignupForm, self).__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ('first_name', 'email', 'password')
        widgets = {
            'password': PasswordInput(
                attrs={
                    'class': 'textinput textInput',
                    'autocomplete': 'new-password',
                    'autocapitalize': 'none',
                    'spellcheck': 'false',
                }
            ),
        }

    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        email = cleaned_data.get('email')
        if not email:
            msg = 'El email ingresado no es un email válido.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        password = cleaned_data.get('password')

        if User.objects.filter(email__iexact=email).exists():
            msg = 'El email ingresado ya posee una cuenta de usuario.'
            msg += ' <a href="/usuarios/entrar/?next=%s">Ingresar</a>.' % self.cleaned_data.get('next_page', '/')
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        if User.objects.filter(username__iexact=email).exists():
            mail_managers("Multiple username in users", email)
            msg = 'El email ingresado no puede ser utilizado.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        return cleaned_data

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            self._errors['first_name'] = self.error_class(
                ['El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.']
            )
        return first_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.lower()

    def clean_password(self):
        data = self.cleaned_data
        password = data.get('password')
        if check_password_strength(password):
            return password
        else:
            self._errors['password'] = self.error_class(['La contraseña debe tener 6 o más caracteres.'])
            return password

    def clean_terms_and_conditions(self):
        terms_and_conditions = self.cleaned_data.get('terms_and_conditions')
        if terms_and_conditions:
            return terms_and_conditions
        else:
            raise ValidationError('Los términos y condiciones deben ser aceptados.')

    def create_user(self):
        DIGIT_RE = re.compile(r'\d')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        user = User.objects.create_user(email, email, password)
        if not user.subscriber.phone:
            user.subscriber.phone = ''.join(DIGIT_RE.findall(self.cleaned_data.get('phone', '')))
        user.subscriber.save()
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_active = False
        user.save()
        return user


class SubscriberForm(ModelForm):
    """ Formulario con la información para crear un suscriptor """
    first_name = CharField(
        label='Nombre',
        widget=TextInput(attrs={'autocomplete': 'name', 'autocapitalize': 'sentences', 'spellcheck': 'false'}),
    )
    email = EmailField(
        label='Email',
        widget=EmailInput(
            attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
        ),
    )
    telephone = CharField(
        label='Teléfono',
        widget=PhoneInput(attrs={'class': 'textinput textInput', 'autocomplete': 'tel', 'spellcheck': 'false'}),
    )
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                'Datos personales',
                Field('first_name', readonly=True),
                Field('email', readonly=True),
                Field('telephone'),
            ),
        )
        super(SubscriberForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Subscriber
        fields = ('first_name', 'email', 'telephone')

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            raise ValidationError(
                'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
            )
        return first_name

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone.isdigit():
            raise ValidationError("Ingresá sólo números en el teléfono.")
        elif any(telephone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLACKLIST', [])):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return telephone

    def clean_email(self):
        return self.cleaned_data.get('email').lower()

    def is_valid(self, subscription_type, payment_type='tel'):
        result = super(SubscriberForm, self).is_valid()
        if result and payment_type == 'tel':
            # continue validation to check for repeated email and subsc. type, for "tel" subscriptions in same day:
            try:
                s = Subscription.objects.get(
                    email__iexact=self.cleaned_data.get('email'), date_created__date=date.today()
                )
                if subscription_type in s.subscription_type_prices.values_list('subscription_type', flat=True):
                    self._errors['email'] = self.error_class(["Su email ya posee una suscripción en proceso"])
                    result = False
            except Subscription.MultipleObjectsReturned:
                # TODO: this can be relaxed using the same "if" above and only invalidate when all objects found
                #       evaluates the "if" to True, and also the view should be changed to be aware of this.
                self._errors['email'] = self.error_class(["Su email ya posee más de una suscripción en proceso"])
                result = False
            except Subscription.DoesNotExist:
                pass
        return result


class SubscriberAddressForm(SubscriberForm):
    address = CharField(
        label='Dirección',
        widget=TextInput(
            attrs={'autocomplete': 'street-address', 'autocapitalize': 'sentences', 'spellcheck': 'false'}
        ),
    )
    city = CharField(label='Ciudad')
    province = ChoiceField(
        label='Departamento',
        choices=settings.THEDAILY_PROVINCE_CHOICES,
        initial=getattr(settings, 'THEDAILY_PROVINCE_CHOICES_INITIAL', None),
    )

    def __init__(self, *args, **kwargs):
        super(SubscriberAddressForm, self).__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            Field('first_name', readonly=True),
            Field('email', readonly=True),
            Field('telephone'),
            HTML(
                '<div class="validate col s12">'
                '  <h3 class="medium" style="color:black;">Información de entrega</h3>'
                '</div>'
            ),
            'address',
            'city',
            Field('province', template='materialize_css_forms/layout/select.html'),
        )

    class Meta:
        model = Subscriber
        fields = ('first_name', 'email', 'telephone', 'address', 'city', 'province')


class SubscriberSubmitForm(SubscriberForm):
    """ Adds a submit button to the SubscriberForm """
    def __init__(self, *args, **kwargs):
        super(SubscriberSubmitForm, self).__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            Fieldset('Datos personales', 'first_name', 'email', 'telephone'),
            FormActions(Submit('save', 'Enviar suscripción')),
        )


class SubscriberSignupForm(SubscriberForm):
    """ Adds a password to the SubscriberForm to also signup """
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(
            attrs={
                'class': 'textinput textInput',
                'autocomplete': 'new-password',
                'autocapitalize': 'none',
                'spellcheck': 'false',
            }
        ),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conditions = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        super(SubscriberSignupForm, self).__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            'first_name',
            'email',
            'telephone',
            'next_page',
            Field('password', template='materialize_css_forms/layout/password.html'),
        )

    def is_valid(self, subscription_type, payment_type=None):
        # call is_valid first with the parent class, only to fill the cleaned_data
        result = super(SubscriberForm, self).is_valid()
        if result:
            # validate signup first
            signup_form = SignupForm(
                {
                    'first_name': self.cleaned_data.get('first_name'),
                    'email': self.cleaned_data.get('email'),
                    'phone': self.cleaned_data.get('telephone'),
                    'password': self.cleaned_data.get('password'),
                    'terms_and_conditions': self.cleaned_data.get('terms_and_conditions'),
                    'next_page': self.cleaned_data.get('next_page'),
                }
            )
            signup_form_valid = signup_form.is_valid()
            result = signup_form_valid and (
                super(SubscriberSignupForm, self).is_valid(subscription_type, payment_type) if payment_type else
                super(SubscriberSignupForm, self).is_valid(subscription_type)
            )
            if result:
                self.signup_form = signup_form
            else:
                if not signup_form_valid:
                    self._errors = signup_form._errors
                # TODO: telephone an phone should have same name to avoid this
                if 'phone' in self._errors:
                    self._errors['telephone'] = self._errors.pop('phone')
        return result


class SubscriberSignupAddressForm(SubscriberAddressForm):
    """ Adds password (like SubscriberSignupForm) and address """
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(
            attrs={
                'class': 'textinput textInput',
                'autocomplete': 'new-password',
                'autocapitalize': 'none',
                'spellcheck': 'false',
            }
        ),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conditions = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        super(SubscriberSignupAddressForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'first_name',
            'email',
            'telephone',
            'next_page',
            Field('password', template='materialize_css_forms/layout/password.html'),
            HTML(
                '<div class="validate col s12">'
                '  <h3 class="medium" style="color:black;">Información de entrega</h3>'
                '</div>'
            ),
            'address',
            'city',
            Field('province', template='materialize_css_forms/layout/select.html'),
        )

    def is_valid(self, subscription_type, payment_type=None):
        # call is_valid first with the parent class, only to fill the cleaned_data
        result = super(SubscriberForm, self).is_valid()
        if result:
            # validate signup first
            signup_form = SignupForm(
                {
                    'first_name': self.cleaned_data.get('first_name'),
                    'email': self.cleaned_data.get('email'),
                    'phone': self.cleaned_data.get('telephone'),
                    'password': self.cleaned_data.get('password'),
                    'terms_and_conditions': self.cleaned_data.get('terms_and_conditions'),
                    'next_page': self.cleaned_data.get('next_page'),
                }
            )
            signup_form_valid = signup_form.is_valid()
            result = signup_form_valid and (
                super(SubscriberSignupAddressForm, self).is_valid(subscription_type, payment_type) if payment_type else
                super(SubscriberSignupAddressForm, self).is_valid(subscription_type)
            )
            if result:
                self.signup_form = signup_form
            else:
                if not signup_form_valid:
                    self._errors = signup_form._errors
                # TODO: telephone an phone should have same name to avoid this
                if 'phone' in self._errors:
                    self._errors['telephone'] = self._errors.pop('phone')
        return result


class SubscriptionForm(ModelForm):
    subscription_type_prices = ChoiceField(choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, widget=HiddenInput())
    payment_type = ChoiceField(
        label='Elegí la forma de suscribirte', choices=(('tel', 'Telefónica (te llamamos)'), ), initial='tel'
    )
    preferred_time = ChoiceField(
        label='Hora de contacto preferida',
        choices=(
            ('1', 'Cualquier hora (9:00 a 20:00)'),
            ('2', 'En la mañana (9:00 a 12:00)'),
            ('3', 'En la tarde (12:00 a 18:00)'),
            ('4', 'En la tarde-noche (18:00 a 20:00)'),
        ),
        initial='1',
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conditions = terms_and_conditions_field

    # TODO: init method here
    choice = ()
    helper = FormHelper()
    helper.form_tag = False
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        *(
            HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 50px;">'),
            Field('payment_type', template='payment_type.html'),
            Field('preferred_time', template='preferred_time.html'),
            HTML('</div>'),
        ) + terms_and_conditions_layout_tuple
        + (
            HTML('<div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
            HTML('<div class="ld-text-secondary align-center ld-subscription-step" style="display:none;">Paso 1 de 2'),
        )
    )

    def clean_terms_and_conditions(self):
        terms_and_conditions = self.cleaned_data.get('terms_and_conditions')
        if terms_and_conditions:
            return terms_and_conditions
        else:
            raise ValidationError('Los términos y condiciones deben ser aceptados.')

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices']

    class Media:
        js = ('js/preferred_time.js', )


class SubscriptionPromoCodeForm(SubscriptionForm):
    promo_code = CharField(label='Código promocional (opcional)', required=False, max_length=8)

    def __init__(self, *args, **kwargs):
        super(SubscriptionPromoCodeForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'promo_code',
            HTML('<div class="col s12" style="margin-top: 25px;margin-bottom: 25px;">'),
            Field('payment_type', template='payment_type.html'),
            Field('preferred_time', template='preferred_time.html'),
            HTML('</div><div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
            HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2'),
        )

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices', 'promo_code']

    def clean_promo_code(self):
        # TODO: write better documentation (can be here in a doctring) instead refer to a commit:
        # see 2bz2cT4R to disable the promo code
        promo_code = self.cleaned_data.get('promo_code')
        if promo_code and promo_code != getattr(settings, 'PROMO_CODE'):
            raise ValidationError('Código promocional incorrecto.')
        return promo_code


class SubscriptionCaptchaForm(SubscriptionForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super(SubscriptionCaptchaForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *(
                HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 25px;">'),
                Field('payment_type', template='payment_type.html'),
                Field('preferred_time', template='preferred_time.html'),
            ) + terms_and_conditions_layout_tuple
            + (
                HTML(
                    '</div><div class="col s12" style="margin-top: 25px; margin-bottom: 25px;">'
                    '<strong>Comprobá que no sos un robot</strong>'
                ),
                'captcha',
                HTML('</div><div class="ld-block--sm align-center">'),
                FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
                HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2'),
            )
        )


class SubscriptionPromoCodeCaptchaForm(SubscriptionPromoCodeForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super(SubscriptionPromoCodeCaptchaForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'promo_code',
            HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 25px;">'),
            Field('payment_type', template='payment_type.html'),
            Field('preferred_time', template='preferred_time.html'),
            HTML(
                '</div><div class="col s12" style="margin-top: 25px; margin-bottom: 25px;">'
                '<strong>Comprobá que no sos un robot</strong>'
            ),
            'captcha',
            HTML('</div><div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
            HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2'),
        )


class GoogleSigninForm(ModelForm):
    """
    Ask for phone number when sign-in is made by Google social login
    """
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conditions = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'google_signin'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            *('phone', ) + terms_and_conditions_layout_tuple
            + (FormActions(Submit('save', 'Crear cuenta', css_class='ut-btn ut-btn-l')), )
        )
        super(GoogleSigninForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Subscriber
        fields = ('phone', )
        widgets = {'phone': PhoneInput(attrs={'autocomplete': 'tel', 'spellcheck': 'false'})}

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise ValidationError("Ingresá sólo números en el teléfono.")
        elif any(phone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLACKLIST', [])):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return phone

    def clean_terms_and_conditions(self):
        terms_and_conditions = self.cleaned_data.get('terms_and_conditions')
        if terms_and_conditions:
            return terms_and_conditions
        else:
            raise ValidationError('Los términos y condiciones deben ser aceptados.')


class GoogleSignupForm(GoogleSigninForm):
    """ Child class to use the same form but without the submit button """
    def __init__(self, *args, **kwargs):
        super(GoogleSignupForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<div class="ld-block--sm align-center">Para continuar completá los siguientes datos</div>'), 'phone'
        )

    def is_valid(self, *args):
        # wrapper to allow compatibility with calls with arguments
        return super(GoogleSignupForm, self).is_valid()


class GoogleSignupAddressForm(GoogleSignupForm):
    """ Child class to not exclude address info (address, city and province) """
    address = CharField(
        label='Dirección',
        widget=TextInput(
            attrs={'autocomplete': 'street-address', 'autocapitalize': 'sentences', 'spellcheck': 'false'}
        ),
    )
    city = CharField(label='Ciudad')
    province = ChoiceField(label='Departamento', choices=settings.THEDAILY_PROVINCE_CHOICES)

    def __init__(self, *args, **kwargs):
        super(GoogleSignupAddressForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            HTML('<div class="ld-block--sm align-center">Para continuar completá los siguientes datos</div>'),
            'phone',
            HTML(
                '<div class="validate col s12">'
                '  <h3 class="medium" style="color:black;">Información de entrega</h3>'
                '</div>'
            ),
            'address',
            'city',
            Field('province', template='materialize_css_forms/layout/select.html'),
        )

    class Meta:
        model = Subscriber
        fields = ('phone', 'address', 'city', 'province')
        widgets = {'phone': PhoneInput(attrs={'autocomplete': 'tel', 'spellcheck': 'false'})}


class PasswordResetRequestForm(Form):
    name_or_mail = CharField(label='Email')

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'reset_password'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('account-password_reset')
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.render_unmentioned_fields = False
        self.helper.layout = Layout(
            Field(
                'name_or_mail',
                id="name_or_email",
                title="Nombre de usuario o email.",
                template='materialize_css_forms/layout/email-login.html'
            ),
            HTML('<div class="align-center form-group">'),
            Submit('save', 'Restablecer contraseña', css_class='ut-btn ut-btn-l'),
            HTML('</div>'),
        )

        super(PasswordResetRequestForm, self).__init__(*args, **kwargs)

    def clean(self):
        nom = self.data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                user = User.objects.get(email__iexact=nom)
            except MultipleObjectsReturned:
                mail_managers("Multiple email in users", nom)
                raise ValidationError('Error, comunicate con nosotros.')
            except User.DoesNotExist:
                raise ValidationError('No hay usuarios registrados con ese email.')
            if user.email is None:
                raise ValidationError(
                    'Tu usuario no está activado, si crees que esto es un error, comunicate con nosotros.'
                )
            else:
                if not user.is_active:
                    raise ValidationError('El suscriptor no está registrado en el sitio.')
        else:
            try:
                user = Subscriber.objects.get(name__iexact=nom).user
            except Exception:
                try:
                    nom = slugify(nom).replace("-", "_")
                    user = User.objects.get(username__iexact=nom)
                except Exception:
                    raise ValidationError('No hay usuarios registrados con ese nombre.')
            if not user.is_active:
                raise ValidationError('El suscriptor no está registrado en el sitio.')
        return self.data

    @property
    def user(self):
        nom = self.data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                return User.objects.get(email__iexact=nom)
            except Exception:
                return None
        else:
            try:
                return Subscriber.objects.get(name__iexact=nom).user
            except Exception:
                try:
                    nom = slugify(nom).replace("-", "_")
                    return User.objects.get(username__iexact=nom)
                except Exception:
                    return None
        return None


class ConfirmEmailRequestForm(Form):
    email = EmailField(
        label='Email',
        widget=EmailInput(attrs={'inputmode': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}),
    )

    # TODO: init method here
    helper = FormHelper()
    helper.form_id = 'confirm_email'
    helper.form_class = 'form-horizontal'
    helper.form_style = 'inline'
    helper.form_method = 'post'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.render_unmentioned_fields = False
    helper.layout = Layout(
        'email',
        HTML('<div class="align-center">'),
        FormActions(Submit('save', 'Enviar mensaje de activación', css_class='ut-btn ut-btn-l')),
        HTML('</div">'),
    )

    def clean(self):
        email = self.data.get('email').strip()
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except MultipleObjectsReturned:
                mail_managers("Multiple email in users", email)
                raise ValidationError('Error, comunicate con nosotros.')
            except User.DoesNotExist:
                raise ValidationError('No hay usuarios registrados con ese email.')
            if user.is_active:
                raise ValidationError('El usuario correspondiente a ese email ya está activo.')
        else:
            raise ValidationError('Tenés que ingresar un email válido')
        return self.data

    @property
    def user(self):
        email = self.data.get('email').strip()
        if email:
            try:
                return User.objects.get(email__iexact=email)
            except Exception:
                return None
        return None


class PasswordChangeBaseForm(Form):
    new_password_1 = CharField(
        label='Nueva contraseña',
        widget=PasswordInput(attrs={"autocomplete": "new-password", 'autocapitalize': 'none', 'spellcheck': 'false'}),
    )
    new_password_2 = CharField(
        label='Repetir contraseña',
        widget=PasswordInput(attrs={"autocomplete": "new-password", 'autocapitalize': 'none', 'spellcheck': 'false'}),
    )

    def clean(self):
        p1 = self.data.get('new_password_1', '')
        p2 = self.data.get('new_password_2', '')
        if p1 and p2:
            if p1 != p2:
                raise ValidationError('Las contraseñas no coinciden.')
            if check_password_strength(p1):
                return self.data
        return self.data

    def get_password(self):
        return self.data.get('new_password_1')


class PasswordChangeForm(PasswordChangeBaseForm):
    old_password = CharField(
        label='Contraseña actual',
        widget=PasswordInput(
            attrs={'autocomplete': 'current-password', 'autocapitalize': 'none', 'spellcheck': 'false'}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'change_password'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'old_password',
            'new_password_1',
            'new_password_2',
            HTML('<div class="align-center">'),
            FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )

        self.user = kwargs.get('user')
        if 'user' in kwargs:
            del(kwargs['user'])

        super(PasswordChangeForm, self).__init__(*args, **kwargs)

    def clean_old_password(self):
        from django.contrib.auth import authenticate

        password = self.cleaned_data.get('old_password', '')
        user = authenticate(username=self.user.username, password=password)
        if not user:
            raise ValidationError('Contraseña incorrecta.')
        return password


class PasswordResetForm(PasswordChangeBaseForm):
    new_password_1 = CharField(
        label='Contraseña',
        widget=PasswordInput(attrs={"autocomplete": "new-password", 'autocapitalize': 'none', 'spellcheck': 'false'}),
    )
    hash = CharField(widget=HiddenInput())
    gonzo = CharField(widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        initial = {}
        if 'hash' not in kwargs:
            raise AttributeError('Missing hash')
        self.user = kwargs.get('user')
        self.hash = kwargs.get('hash')
        initial['hash'] = self.hash
        initial['gonzo'] = self.gen_gonzo()
        kwargs['initial'] = initial
        del(kwargs['hash'])
        del(kwargs['user'])

        self.helper = FormHelper()
        self.helper.form_id = 'reset_password'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('new_password_1', template='materialize_css_forms/layout/password.html'),
            Field('new_password_2', template='materialize_css_forms/layout/password.html'),
            Field('gonzo', type='hidden', value=initial['gonzo']),
            Field('hash', type='hidden', value=initial['gonzo']),
            FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
        )

        super(PasswordResetForm, self).__init__(*args, **kwargs)

    def gen_gonzo(self):
        from libs.utils import do_gonzo
        return do_gonzo(self.hash)

    def clean(self, *args, **kwargs):
        super(PasswordResetForm, self).clean(*args, **kwargs)
        password = self.get_password()
        if password:
            if self.data.get('gonzo') != self.gen_gonzo():
                raise ValidationError('Ocurrió un error interno.')
            user = get_object_or_404(User, id=self.user)
            if not default_token_generator.check_token(user, self.hash):
                raise ValidationError('Ocurrió un error interno.')
        return self.data
