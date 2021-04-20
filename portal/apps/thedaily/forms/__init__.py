# -*- coding: utf-8 -*-
import re

from captcha.fields import ReCaptchaField

from django.template.defaultfilters import slugify
from django.conf import settings
from django.http import UnreadablePostError
from django.contrib.auth.models import User

from libs.tokens.email_confirmation import default_token_generator
from django.shortcuts import get_object_or_404

from django.core.mail import mail_managers
from django.forms import (
    Form, ModelForm, CharField, EmailField, PasswordInput, TextInput, Textarea, HiddenInput, ChoiceField,
    ValidationError)

from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, Fieldset, HTML
from crispy_forms.bootstrap import FormActions

from thedaily.models import Subscription, Subscriber


CSS_CLASS = 'form-input1'
RE_ALPHANUM = re.compile(u'^[A-Za-z0-9ñüáéíóúÑÜÁÉÍÓÚ _\'.\-]*$')


def check_password_strength(password):
    if len(password) < 6:
        return False
    else:
        return True


class PhoneInput(TextInput):
    input_type = 'tel'


class EmailInput(TextInput):
    input_type = 'email'


class LoginForm(Form):
    """ Login form """

    name_or_mail = CharField(
        label='Email', widget=TextInput(attrs={'class': CSS_CLASS}))
    password = CharField(
        label='Contraseña', widget=PasswordInput(attrs={'class': CSS_CLASS}))

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
                'name_or_mail', title=u"Ingresá tu nombre de usuario o email",
                template='materialize_css_forms/layout/email-login.html'),
            Field(
                'password',
                title=u"Contraseña. Si no la recordás la podés restablecer.",
                template='materialize_css_forms/layout/password-login.html'),

        )
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = self.data
        USER_PASS_ERROR = u'Email y/o contraseña incorrectos.'
        nom = data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                self.username = User.objects.get(email__iexact=nom).username
            except Exception:
                raise ValidationError(USER_PASS_ERROR)
        else:
            try:
                self.username = Subscriber.objects.get(
                    name__iexact=nom).user.username
            except Exception:
                if User.objects.filter(username__iexact=nom).count():
                    self.username = nom
                else:
                    raise ValidationError(USER_PASS_ERROR)
        return data


class SignupForm(ModelForm):
    """ Formulario con campos para crear una instancia del modelo User """

    first_name = CharField(label=u'Nombre')
    email = EmailField(label=u'Email', widget=EmailInput(attrs={'inputmode': 'email'}))
    phone = CharField(label='Teléfono',widget=PhoneInput(attrs={'class': 'textinput textInput'}))
    password = CharField(label=u'Contraseña', widget=PasswordInput())
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
            Fieldset(
                u'',
                'first_name',
                'phone',
                'email',
                Field('password', template='materialize_css_forms/layout/password.html'),
                'next_page',
            ),
            HTML('<div class="align-center">'),
            Submit('save', u'Suscribite', css_class='btn-register'),
            HTML('</div">'),
        )
        super(SignupForm, self).__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ('first_name', 'email', 'password')

    def clean(self):
        cleaned_data = super(SignupForm, self).clean()
        email = cleaned_data.get('email')
        if not email:
            msg = u'El email ingresado no es un email válido.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        password = cleaned_data.get('password')

        if User.objects.filter(email__iexact=email).exists():
            msg = u'El email ingresado ya posee una cuenta de usuario.'
            msg += u' <a href="/usuarios/entrar">Ingresar</a>.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        if User.objects.filter(username__iexact=email).exists():
            mail_managers("Multiple username in users", email)
            msg = u'El email ingresado no puede ser utilizado.'
            self._errors['email'] = self.error_class([msg])
            raise ValidationError(msg)

        return cleaned_data

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            self._errors['first_name'] = self.error_class([
                u'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'])
        return first_name

    def clean_email(self):
        email, email_max_length = self.cleaned_data.get('email'), getattr(settings, 'THEDAILY_EMAIL_MAX_LENGTH', 30)
        if len(email) <= email_max_length:
            return email.lower()
        else:
            self._errors['email'] = self.error_class([
                u'Email demasiado largo, se permiten hasta %d caracteres.' % email_max_length])
            return email

    def clean_password(self):
        data = self.cleaned_data
        password = data.get('password')
        if check_password_strength(password):
            return password
        else:
            self._errors['password'] = self.error_class([u'La contraseña debe tener 6 o más caracteres.'])
            return password

    def create_user(self):
        DIGIT_RE = re.compile(r'\d')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        user = User.objects.create_user(email.split('@')[0] if len(email) > 30 else email, email, password)
        if not user.subscriber.phone:
            user.subscriber.phone = ''.join(
                DIGIT_RE.findall(self.cleaned_data.get('phone', '')))
        user.subscriber.save()
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_active = False
        user.save()
        return user


class SubscriberForm(ModelForm):
    """ Formulario con la información para crear un suscriptor """

    first_name = CharField(label='Nombre')
    email = EmailField(label=u'Email', widget=EmailInput(attrs={'inputmode': 'email'}))
    telephone = CharField(
        label='Teléfono',
        widget=PhoneInput(attrs={'class': 'textinput textInput'}))

    helper = FormHelper()
    helper.form_tag = False
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Fieldset(
            u'Datos personales',
            Field('first_name', readonly=True),
            Field('email', readonly=True),
            Field('telephone', readonly=True)
        ),
    )

    class Meta:
        model = Subscriber
        fields = ('first_name', 'email', 'telephone')

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            raise ValidationError(
                u'El nombre sólo admite caracteres alfanuméricos, apóstrofes, '
                u'espacios, guiones y puntos.')
        return first_name

    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone.isdigit():
            raise ValidationError(u"Ingresá sólo números en el teléfono.")
        elif any(telephone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLACKLIST', [])):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return telephone

    def is_valid(self, subscription_type):
        result = super(SubscriberForm, self).is_valid()
        if result:
            # continue validation to check for repeated email and subsc. type:
            try:
                s = Subscription.objects.get(
                    email__iexact=self.cleaned_data.get('email'))
                if subscription_type in s.subscription_type_prices.values_list(
                        'subscription_type', flat=True):
                    self._errors['email'] = self.error_class([
                        u"Su email ya posee una suscripción"])
                    result = False
            except Subscription.MultipleObjectsReturned:
                self._errors['email'] = self.error_class([
                    u"Su email ya posee más de una suscripción"])
                result = False
            except Subscription.DoesNotExist:
                pass
        return result


class SubscriberAddressForm(SubscriberForm):
    address = CharField(label='Dirección')
    city = CharField(label='Ciudad')
    province = ChoiceField(
        label='Departamento', choices=settings.THEDAILY_PROVINCE_CHOICES,
        initial=getattr(settings, 'THEDAILY_PROVINCE_CHOICES_INITIAL', None))

    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(Fieldset(
        u'', Field('first_name', readonly=True), Field('email', readonly=True), Field('telephone', readonly=True),
        HTML(
            u'<div class="validate col s12 ">'
            u'<h3 class="medium" style="color:black;">'
            u'Información de entrega</h3></div>'), 'address', 'city',
        Field('province', template='materialize_css_forms/layout/select.html')))

    class Meta:
        model = Subscriber
        fields = (
            'first_name', 'email', 'telephone', 'address', 'city', 'province')


class SubscriberSubmitForm(SubscriberForm):
    """ Adds a submit button to the SubscriberForm """

    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Fieldset(
            u'Datos personales',
            'first_name',
            'email',
            'telephone',
        ),
        FormActions(
            Submit('save', u'Enviar suscripción'),
        ),
    )


class SubscriberSignupForm(SubscriberForm):
    """ Adds a password to the SubscriberForm to also signup """
    password = CharField(label=u'Contraseña', widget=PasswordInput())

    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Fieldset(
            u'', 'first_name', 'email', 'telephone', Field(
                'password',
                template='materialize_css_forms/layout/password.html')))

    def is_valid(self, subscription_type):
        result = super(SubscriberSignupForm, self).is_valid(subscription_type)
        if result:
            # continue validation to check for the new signup:
            self.signup_form = SignupForm({
                'first_name': self.cleaned_data.get('first_name'),
                'email': self.cleaned_data.get('email'),
                'phone': self.cleaned_data.get('telephone'),
                'password': self.cleaned_data.get('password')})
            result = self.signup_form.is_valid()
            if not result:
                self._errors = self.signup_form._errors
                # TODO: telephone an phone should have same name to avoid this
                if 'phone' in self._errors:
                    self._errors['telephone'] = self._errors.pop('phone')
        return result


class SubscriberSignupAddressForm(SubscriberAddressForm):
    """ Adds password (like SubscriberSignupForm) and address """
    password = CharField(label=u'Contraseña', widget=PasswordInput())

    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(Fieldset(
        u'', 'first_name', 'email', 'telephone', Field(
            'password',
            template='materialize_css_forms/layout/password.html'),
        HTML(
            u'<div class="validate col s12 ">'
            u'<h3 class="medium" style="color:black;">'
            u'Información de entrega</h3></div>'), 'address', 'city',
        Field('province', template='materialize_css_forms/layout/select.html')
    ))

    def is_valid(self, subscription_type):
        result = super(
            SubscriberSignupAddressForm, self).is_valid(subscription_type)
        if result:
            # continue validation to check for the new signup:
            self.signup_form = SignupForm({
                'first_name': self.cleaned_data.get('first_name'),
                'email': self.cleaned_data.get('email'),
                'phone': self.cleaned_data.get('telephone'),
                'password': self.cleaned_data.get('password')})
            result = self.signup_form.is_valid()
            if not result:
                self._errors = self.signup_form._errors
                # TODO: telephone an phone should have same name to avoid this
                if 'phone' in self._errors:
                    self._errors['telephone'] = self._errors.pop('phone')
        return result


class SubscriptionForm(ModelForm):
    subscription_type_prices = ChoiceField(choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, widget=HiddenInput())
    payment_type = ChoiceField(
        label=u'Elegí la forma de suscribirte', choices=(('tel', u'Telefónica (te llamamos)'), ), initial='tel')
    preferred_time = ChoiceField(
        label=u'Hora de contacto preferida', choices=(
            ('1', u'Cualquier hora (9:00 a 20:00)'),
            ('2', u'En la mañana (9:00 a 12:00)'),
            ('3', u'En la tarde (12:00 a 18:00)'),
            ('4', u'En la tarde-noche (18:00 a 20:00)')), initial='1')
    choice = ()
    helper = FormHelper()
    helper.form_tag = False
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        HTML('<div class="col s12" style="margin-top: 30px; \
            margin-bottom: 50px;">'),
        Field('payment_type', template='payment_type.html'),
        Field('preferred_time', template='preferred_time.html'),
        HTML('</div>'),
        HTML('<div class="ld-block--sm align-center">'),
        FormActions(
            Submit('save', u'Continuar', css_class='ld-btn-regular'),
        ),
        HTML('''<div class="ld-text-secondary align-center
         ld-subscription-step" style="display:none;">Paso 1 de 2<div></div>''')
    )

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices']


class SubscriptionPromoCodeForm(SubscriptionForm):
    promo_code = CharField(label=u'Código promocional (opcional)', required=False, max_length=8)

    helper = FormHelper()
    helper.form_tag = False
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Field('promo_code'),
        HTML('<div class="col s12" style="margin-top: 25px;margin-bottom: 25px;">'),
        Field('payment_type', template='payment_type.html'),
        Field('preferred_time', template='preferred_time.html'),
        HTML('</div><div class="ld-block--sm align-center">'),
        FormActions(Submit('save', u'Continuar', css_class='ld-btn-regular'), ),
        HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2<div></div>')
    )

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices', 'promo_code']

    def clean_promo_code(self):
        # TODO post release: write better documentation (can be here in a doctring) instead refer to a commit:
        # see 2bz2cT4R to disable the promo code
        promo_code = self.cleaned_data.get('promo_code')
        if promo_code and promo_code != getattr(settings, 'PROMO_CODE'):
            raise ValidationError(u'Código promocional incorrecto.')
        return promo_code


class SubscriptionPromoCodeCaptchaForm(SubscriptionPromoCodeForm):
    captcha = ReCaptchaField(label=u'')

    helper = FormHelper()
    helper.form_tag = False
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Field('promo_code'),
        HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 25px;">'),
        Field('payment_type', template='payment_type.html'),
        Field('preferred_time', template='preferred_time.html'),
        HTML(
            u'</div><div class="col s12" style="margin-top: 25px; margin-bottom: 25px;">'
            u'<strong>Comprobá que no sos un robot</strong>'),
        Field('captcha'),
        HTML('</div><div class="ld-block--sm align-center">'),
        FormActions(Submit('save', u'Continuar', css_class='ld-btn-regular'), ),
        HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2<div></div>')
    )


class GoogleSigninForm(ModelForm):
    """
    Ask for phone number when sign-in is made by Google social login
    """
    helper = FormHelper()
    helper.form_id = 'google_signin'
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        Fieldset(u'', 'phone'),
        FormActions(
            Submit('save', u'suscribite', css_class='ld-btn-regular')))

    class Meta:
        model = Subscriber
        exclude = (
            'costumer_id',
            'user',
            'name',
            'downloads',
            'profile_photo',
            'days',
            'address',
            'city',
            'province',
            'country',
            'newsletters',
            'category_newsletters',
            'allow_news',
            'allow_promotions',
            'allow_polls',
            'document',
            'pdf',
            'ruta',
            'lento_pdf',
        )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone.isdigit():
            raise ValidationError(u"Ingresá sólo números en el teléfono.")
        elif any(phone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLACKLIST', [])):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return phone


class GoogleSignupForm(GoogleSigninForm):
    """
    Child class to use the same form but without the submit button
    """
    helper = FormHelper()
    helper.form_tag = False
    helper.form_id = 'google_signin'
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        HTML(u'''<div class="ld-block--sm align-center">
            Para continuar completá los siguientes datos</div>'''),
        Fieldset(u'', 'phone'))

    def is_valid(self, arg=None):
        # wrapper to allow compatibility with calls with an argument
        return super(GoogleSignupForm, self).is_valid()


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
            Fieldset(u'', Field(
                'name_or_mail', id="name_or_email",
                title="Nombre de usuario o email.",
                template='materialize_css_forms/layout/email-login.html'),
            ),
            HTML('<div class="align-center form-group">'),
            Submit('save', u'Restablecer contraseña', css_class='ld-btn-default btn-dark'),
            HTML('</div">'))

        super(PasswordResetRequestForm, self).__init__(*args, **kwargs)

    def clean(self):
        nom = self.data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                user = User.objects.get(email__iexact=nom)
            except MultipleObjectsReturned:
                mail_managers("Multiple email in users", nom)
                raise ValidationError(u'Error, comunicate con nosotros.')
            except User.DoesNotExist:
                raise ValidationError(
                    u'No hay usuarios registrados con ese email.')
            if user.email is None:
                raise ValidationError(
                    u'Su usuario no está activado, si cree '
                    u'que esto es un error, comuníquese con nuestra oficina.')
            else:
                if not user.is_active:
                    raise ValidationError(
                        u'El suscriptor no está registrado en el sitio.')
        else:
            try:
                user = Subscriber.objects.get(name__iexact=nom).user
            except Exception:
                try:
                    nom = slugify(nom).replace("-", "_")
                    user = User.objects.get(username__iexact=nom)
                except Exception:
                    raise ValidationError(
                        u'No hay usuarios registrados con ese nombre.')
            if not user.is_active:
                raise ValidationError(
                    u'El suscriptor no está registrado en el sitio.')
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
    email = EmailField(label=u'Email', widget=EmailInput(attrs={'inputmode': 'email'}))

    helper = FormHelper()
    helper.form_id = 'confirm_email'
    helper.form_class = 'form-horizontal'
    helper.form_style = 'inline'
    helper.form_method = 'post'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.render_unmentioned_fields = False
    helper.layout = Layout(
        Fieldset(u'', Field('email')),
        HTML('<div class="align-center">'),
        FormActions(Submit('save', u'Enviar mensaje de activación', css_class='ld-btn-default btn-dark')),
        HTML('</div">'),
    )

    def clean(self):
        email = self.data.get('email').strip()
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except MultipleObjectsReturned:
                mail_managers("Multiple email in users", email)
                raise ValidationError(u'Error, comunicate con nosotros.')
            except User.DoesNotExist:
                raise ValidationError(
                    u'No hay usuarios registrados con ese email.')
            if user.is_active:
                raise ValidationError(
                    u'El usuario correspondiente a ese email ya está activo.')
        else:
            raise ValidationError(u'Tenés que ingresar un email válido')
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
        label=u'Nueva contraseña', widget=PasswordInput())
    new_password_2 = CharField(
        label=u'Repetir contraseña', widget=PasswordInput())

    def clean(self):
        p1 = self.data.get('new_password_1', '')
        p2 = self.data.get('new_password_2', '')
        if p1 and p2:
            if p1 != p2:
                raise ValidationError(u'Las contraseñas no coinciden.')
            if check_password_strength(p1):
                return self.data
        return self.data

    def get_password(self):
        return self.data.get('new_password_1')


class PasswordChangeForm(PasswordChangeBaseForm):
    old_password = CharField(
        label=u'Contraseña actual', widget=PasswordInput())

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'change_password'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'old_password', 'new_password_1', 'new_password_2',
            HTML('<div class="align-center">'),
            FormActions(
                Submit(
                    'save', u'Elegir contraseña', css_class='ld-btn-default btn-dark'),
            ),
             HTML('</div">'))

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
    new_password_1 = CharField(label=u'Contraseña', widget=PasswordInput())
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
            'new_password_1', 'new_password_2',
            Field('gonzo', type='hidden', value=initial['gonzo']),
            Field('hash', type='hidden', value=initial['gonzo']),
            FormActions(
                Submit(
                    'save', u'Elegir contraseña', css_class='ld-btn-default'),
            ))

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


# H40 forms
class H40UForm(Form):
    name = CharField(required=False, label='Nombre')
    h40 = CharField(max_length=140, widget=Textarea(attrs={'rows': 2}))


class H40Form(H40UForm):
    document = CharField(label='Documento', max_length=8)

    def clean_document(self):
        if Subscriber.objects.filter(document=self.cleaned_data['document']):
            return self.cleaned_data['document']
        else:
            raise ValidationError(
                u'No coinciden tus datos, ayuda: comunidad@ladiaria.com.uy')


# Poll: #TODO Apply DRY, this is much similar to the last one (H40 forms)
class PollUForm(Form):
    name = CharField(required=False, label='Nombre')
    option = ChoiceField(label='Voto por', choices=(
        ('', '-- Elija un candidato --'),
        ('couto', 'Couto, Daniela'),
        ('platero', 'Platero, Soledad'),
    ), help_text='Candidatos en orden alfabético')

    def clean_name(self):
        raise ValidationError('La votación ha finalizado')


class PollForm(PollUForm):
    document = CharField(
        label='Documento', max_length=13,
        help_text=u'Todos los números, sin puntos ni guiones')

    def clean_document(self):
        if Subscriber.objects.filter(document=self.cleaned_data['document']):
            return self.cleaned_data['document']
        else:
            raise ValidationError(
                u'No coinciden tus datos, ayuda: defensor@ladiaria.com.uy')
