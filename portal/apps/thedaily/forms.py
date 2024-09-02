# -*- coding: utf-8 -*-

import re

from django_recaptcha.fields import ReCaptchaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, BaseInput, Field, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from crispy_forms.utils import get_template_pack

from django.conf import settings
from django.template.defaultfilters import slugify
from django.http import UnreadablePostError
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django.core.mail import mail_managers
from django.core.exceptions import MultipleObjectsReturned
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
from django.urls import reverse
from django.utils.timezone import now

from .models import Subscription, Subscriber, email_extra_validations
from .utils import get_all_newsletters
from .exceptions import EmailValidationError


CSS_CLASS = 'form-input1'
RE_ALPHANUM = re.compile('^[A-Za-z0-9ñüáéíóúÑÜÁÉÍÓÚ _\'.\-]*$')
SUBSCRIPTION_PHONE_TIME_CHOICES = (
    ('1', 'Cualquier hora (9:00 a 20:00)'),
    ('2', 'En la mañana (9:00 a 12:00)'),
    ('3', 'En la tarde (12:00 a 18:00)'),
    ('4', 'En la tarde-noche (18:00 a 20:00)'),
)
terms_and_conditions_field = BooleanField(label='Leí y acepto los <a>términos y condiciones</a>', required=False)
terms_and_conditions_layout_tuple = (
    (Field('terms_and_conds_accepted', css_class='filled-in'),)
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
    else ()
)
terms_and_conditions_prelogin = (
    settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
    and getattr(settings, "THEDAILY_TERMS_AND_CONDITIONS_PRELOGIN", True)
)


def check_password_strength(password):
    if len(password) < 6:
        return False
    else:
        return True


def clean_terms_and_conds(form):
    terms_and_conditions = form.cleaned_data.get("terms_and_conds_accepted")
    if terms_and_conditions:
        return terms_and_conditions
    else:
        form.add_error("terms_and_conds_accepted", ValidationError('Los términos y condiciones deben ser aceptados.'))


class Submit(BaseInput):
    """
    Use a custom submit because crispy's adds btn and btn-primary in the class attribute
    """

    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'submit submitButton' if get_template_pack() == 'uni_form' else ''
        super().__init__(*args, **kwargs)


class PhoneInput(TextInput):
    input_type = 'tel'


class EmailInput(TextInput):
    input_type = 'email'


class PreLoginForm(Form):
    email = CharField(label='Email', widget=TextInput(attrs={'class': CSS_CLASS}))
    if terms_and_conditions_prelogin:
        terms_and_conds_accepted = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.helper.layout = Layout(*self.layout_args())

    def layout_args(self):
        return (
            (Field('email', title="Ingresá tu email", template='materialize_css_forms/layout/email-login.html'),)
            + ((terms_and_conditions_layout_tuple) if terms_and_conditions_prelogin else ())
            + (
                Submit(
                    'submit',
                    'continuar',
                    css_class='payment-container__anonymous__subscribe ut-btn' + (
                        " topspaced" if not terms_and_conditions_prelogin else ""
                    ),
                ),
            )
        )

    def clean_email(self):
        email = self.cleaned_data.get('email', "").lower()
        error_msg, error_code = email_extra_validations(None, email)
        if error_msg:
            self.add_error("email", EmailValidationError(error_msg, code=error_code))
        else:
            return email

    if terms_and_conditions_prelogin:
        def clean_terms_and_conds_accepted(self):
            return clean_terms_and_conds(self)


class LoginForm(Form):
    name_or_mail = CharField(label='Email', widget=TextInput(attrs={'class': CSS_CLASS}))
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(attrs={'class': CSS_CLASS, 'autocomplete': 'current-password', 'autocapitalize': 'none'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'account_login'
        self.helper.form_style = 'inline'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
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


class BaseUserForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True

    def custom_clean(self, exclude_self=False, error_use_next=True):
        cleaned_data = super().clean()
        error_msg, error_code = email_extra_validations(
            self.instance.email,
            cleaned_data.get('email'),
            self.instance.id if exclude_self else None,
            error_use_next and (cleaned_data.get('next_page', '/') or "/"),
        )
        if error_msg:
            self._errors['email'] = self.error_class([error_msg])
            raise ValidationError(error_msg)
        else:
            self.instance.email_extra_validations_done = True  # useful flag for the pre_save signal
            return cleaned_data

    def clean(self):
        return self.custom_clean()

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

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {"last_name": "Apellido", "email": "Email"}


class UserForm(BaseUserForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.layout = Layout(Fieldset('Datos personales', 'first_name', 'last_name', 'email'))

    def clean(self):
        return self.custom_clean(True, False)

    class Meta(BaseUserForm.Meta):
        widgets = {
            'email': EmailInput(
                attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
            ),
        }


class SignupForm(BaseUserForm):
    """
    Formulario con campos para crear una instancia del modelo User
    """

    first_name = CharField(
        label='Nombre',
        widget=TextInput(
            attrs={
                'autocomplete': 'name', 'autocapitalize': 'sentences', 'spellcheck': 'false', 'placeholder': 'Nombre'
            }
        ),
    )
    email = EmailField(
        label='Email',
        widget=EmailInput(
            attrs={
                'inputmode': 'email',
                'autocomplete': 'email',
                'autocapitalize': 'none',
                'spellcheck': 'false',
                'placeholder': 'ejemplo@gmail.com',
            }
        ),
    )
    phone = CharField(
        label='Teléfono',
        widget=PhoneInput(attrs={'class': 'textinput textInput', 'autocomplete': 'tel', 'spellcheck': 'false'}),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = 'signup_form'
        self.helper.render_unmentioned_fields = False
        self.helper.form_tag = True
        self.helper.layout = Layout(
            *(
                'first_name',
                'email',
                'phone',
                Field(
                    'password', placeholder="Crear contraseña", template='materialize_css_forms/layout/password.html'
                )
            )
            + terms_and_conditions_layout_tuple
            + (
                'next_page',
                HTML('<div class="align-center">'),
                Submit('save', self.initial.get("save", "Crear cuenta"), css_class='ut-btn ut-btn-l'),
                HTML('</div">'),
            )
        )

    def clean_password(self):
        data = self.cleaned_data
        password = data.get('password')
        if check_password_strength(password):
            return password
        else:
            self._errors['password'] = self.error_class(['La contraseña debe tener 6 o más caracteres.'])
            return password

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)

    def create_user(self):
        DIGIT_RE = re.compile(r'^\+|\d')
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        user = User.objects.create_user(email, email, password)
        if not user.subscriber.phone:
            user.subscriber.phone = ''.join(DIGIT_RE.findall(self.cleaned_data.get('phone', '')))
        if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
            user.subscriber.terms_and_conds_accepted = self.cleaned_data.get('terms_and_conds_accepted')
        user.subscriber.save()
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_active = False
        user.save()
        return user

    class Meta(BaseUserForm.Meta):
        fields = ('first_name', 'email', 'password')
        widgets = {
            'password': PasswordInput(
                attrs={
                    'class': 'textinput textInput',
                    'autocomplete': 'new-password',
                    'autocapitalize': 'none',
                    'spellcheck': 'false',
                }
            )
        }


class SignupCaptchaForm(SignupForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *('first_name', 'email', 'phone', Field('password', template='materialize_css_forms/layout/password.html'))
            + terms_and_conditions_layout_tuple
            + (
                HTML('<strong>Comprobá que no sos un robot</strong>'),
                'captcha',
                'next_page',
                HTML('<div class="align-center">'),
                Submit('save', 'Crear cuenta', css_class='ut-btn ut-btn-l'),
                HTML('</div">'),
            )
        )


class PreLoginCaptchaForm(PreLoginForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout_args = self.layout_args()
        self.helper.layout = Layout(
            *layout_args[:-1] + (HTML('<strong>Comprobá que no sos un robot</strong>'), 'captcha', layout_args[-1])
        )


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
        Fieldset('Datos de suscriptor', 'document', 'phone'),
        Fieldset('Ubicación', 'country', 'province', 'city', 'address'),
    )

    class Meta:
        model = Subscriber
        fields = ('address', 'country', 'city', 'province', 'document', 'phone')


class ProfileExtraDataForm(ModelForm):
    helper = FormHelper()
    helper.form_tag = False
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-sm-2'
    helper.field_class = 'col-sm-8'
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.layout = Layout(
        HTML(
            '{%% include "%s" %%}' % getattr(settings, 'THEDAILY_SUBSCRIPTIONS_TEMPLATE', 'profile/suscripciones.html')
        ),
        # include push notifications section if it's configured
        HTML(
            '{%% if push_notifications_keys_set %%}{%% include "%s" %%}{%% endif %%}' % (
                "profile/push_notifications.html"
            )
        ),
        Field('newsletters', template='profile/newsletters.html'),
        HTML(
            '''
            <section id="ld-comunicaciones" class="scrollspy edit_profile_card">
              <div class="edit_profile_card__header"><h2 class="title">Comunicaciones</h2></div>
            '''
        ),
        Field('allow_news', template=getattr(settings, 'THEDAILY_ALLOW_NEWS_TEMPLATE', 'profile/allow_news.html')),
        Field('allow_promotions', template='profile/allow_promotions.html'),
        Field('allow_polls', template='profile/allow_polls.html'),
        HTML('</section>'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["newsletters"].choices = [(item.slug, item.name) for item in get_all_newsletters()]

    class Meta:
        model = Subscriber
        fields = ('allow_news', 'allow_promotions', 'allow_polls', "newsletters")


def phone_is_blocklisted(phone):
    return any(phone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLOCKLIST', []))


class SubscriberForm(ModelForm):
    first_name = CharField(
        label='Nombre',
        widget=TextInput(
            attrs={
                'autocomplete': 'name', 'autocapitalize': 'sentences', 'spellcheck': 'false', "placeholder": "Nombre"
            }
        ),
    )
    email = EmailField(
        label='Email',
        widget=EmailInput(
            attrs={
                'inputmode': 'email',
                'autocomplete': 'email',
                'autocapitalize': 'none',
                'spellcheck': 'false',
                "placeholder": "nombre@gmail.com",
            }
        ),
    )
    phone = CharField(
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
            Fieldset('Datos personales', Field('first_name'), Field('email', readonly=True), Field('phone')),
        )
        super().__init__(*args, **kwargs)

    class Meta:
        model = Subscriber
        fields = ('first_name', 'email', 'phone')

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            raise ValidationError(
                'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
            )
        return first_name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', "").replace(" ", "")
        if not re.match(r'^\+?\d+$', phone):
            raise ValidationError("Ingresá sólo números en el teléfono.")
        elif phone_is_blocklisted(phone):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return phone

    def clean_email(self):
        return self.cleaned_data.get('email').lower()

    def is_valid(self, subscription_type, payment_type='tel'):
        result = super().is_valid()
        print('result')
        print(result)
        print(self.cleaned_data.get('phone'))
        
        if result and payment_type == 'tel':
            # continue validation to check for repeated email and subsc. type, for "tel" subscriptions in same day:
            try:
                s = Subscription.objects.get(
                    email__iexact=self.cleaned_data.get('email'), date_created__date=now().date()
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
        super().__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            Field('first_name'),
            Field('email', readonly=True),
            Field('phone'),
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
        fields = ('first_name', 'email', 'phone', 'address', 'city', 'province')


class SubscriberSubmitForm(SubscriberForm):
    """ Adds a submit button to the SubscriberForm """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            Fieldset('Datos personales', 'first_name', 'email', 'phone'),
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
                'placeholder': 'Crear contraseña',
            }
        ),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.layout = Layout(
            'first_name',
            'email',
            'phone',
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
                    'phone': self.cleaned_data.get('phone'),
                    'password': self.cleaned_data.get('password'),
                    "terms_and_conds_accepted": self.cleaned_data.get("terms_and_conds_accepted"),
                    'next_page': self.cleaned_data.get('next_page'),
                }
            )
            signup_form_valid = signup_form.is_valid()
            result = signup_form_valid and (
                super().is_valid(subscription_type, payment_type)
                if payment_type
                else super().is_valid(subscription_type)
            )
            if result:
                self.signup_form = signup_form
            else:
                if not signup_form_valid:
                    self._errors = signup_form._errors
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
        terms_and_conds_accepted = terms_and_conditions_field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'first_name',
            'email',
            'phone',
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
                    'phone': self.cleaned_data.get('phone'),
                    'password': self.cleaned_data.get('password'),
                    "terms_and_conds_accepted": self.cleaned_data.get("terms_and_conds_accepted"),
                    'next_page': self.cleaned_data.get('next_page'),
                }
            )
            signup_form_valid = signup_form.is_valid()
            result = signup_form_valid and (
                super().is_valid(subscription_type, payment_type)
                if payment_type
                else super().is_valid(subscription_type)
            )
            if result:
                self.signup_form = signup_form
            else:
                if not signup_form_valid:
                    self._errors = signup_form._errors
        return result


class SubscriptionForm(ModelForm):
    subscription_type_prices = ChoiceField(choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, widget=HiddenInput())
    payment_type = ChoiceField(
        label='Elegí la forma de suscribirte', choices=(('tel', 'Telefónica (te llamamos)'),), initial='tel'
    )
    preferred_time = ChoiceField(
        label='Hora de contacto preferida', choices=SUBSCRIPTION_PHONE_TIME_CHOICES, initial='1'
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field

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
        )
        + terms_and_conditions_layout_tuple
        + (
            HTML('<div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
            HTML('<div class="ld-text-secondary align-center ld-subscription-step" style="display:none;">Paso 1 de 2'),
            Field('subscription_type_prices'),
        )
    )

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices']

    class Media:
        js = ('js/preferred_time.js',)


class SubscriptionPromoCodeForm(SubscriptionForm):
    promo_code = CharField(label='Código promocional (opcional)', required=False, max_length=8)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'promo_code',
            HTML('<div class="col s12" style="margin-top: 25px;margin-bottom: 25px;">'),
            Field('payment_type', template='payment_type.html'),
            Field('preferred_time', template='preferred_time.html'),
            HTML('</div><div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
            HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2'),
            Field('subscription_type_prices'),
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
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *(
                HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 25px;">'),
                Field('payment_type', template='payment_type.html'),
                Field('preferred_time', template='preferred_time.html'),
            )
            + terms_and_conditions_layout_tuple
            + (
                HTML(
                    '</div><div class="col s12" style="margin-top: 25px; margin-bottom: 25px;">'
                    '<strong>Comprobá que no sos un robot</strong>'
                ),
                'captcha',
                HTML('</div><div class="ld-block--sm align-center">'),
                FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
                HTML('<div class="ld-text-secondary align-center ld-subscription-step">Paso 1 de 2'),
                Field('subscription_type_prices'),
            )
        )


class SubscriptionPromoCodeCaptchaForm(SubscriptionPromoCodeForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            Field('subscription_type_prices'),
        )


class GoogleSigninForm(ModelForm):
    """
    Asks for possible missing data (phone or terms and conds acceptance) when sign-in is made by Google
    """
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        submit_label = 'crear cuenta' if kwargs.pop("is_new", None) else "continuar"
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'google_signin'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-8'
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            *('phone', "next_page")
            + terms_and_conditions_layout_tuple
            + (FormActions(Submit('save', submit_label, css_class='ut-btn ut-btn-l')),)
        )

    class Meta:
        model = Subscriber
        fields = ('phone',) + (
            ("terms_and_conds_accepted",) if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID else ()
        )
        widgets = {'phone': PhoneInput(attrs={'autocomplete': 'tel', 'spellcheck': 'false'})}

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', "").replace(" ", "")
        if not re.match(r'^\+?\d+$', phone):
            raise ValidationError("Ingresá sólo números en el teléfono.")
        elif phone_is_blocklisted(phone):
            # Raise error to minimize the info given to possible bot
            raise UnreadablePostError
        return phone

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)


class GoogleSignupForm(GoogleSigninForm):
    """ Child class to use the same form but without the submit button """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<div class="ld-block--sm align-center">Para continuar completá los siguientes datos</div>'), 'phone'
        )

    def is_valid(self, *args):
        # wrapper to allow compatibility with calls with arguments
        return super().is_valid()


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
        super().__init__(*args, **kwargs)
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
                template='materialize_css_forms/layout/email-login.html',
            ),
            HTML('<div class="align-center form-group">'),
            Submit('save', 'Restablecer contraseña', css_class='ut-btn ut-btn-l'),
            HTML('</div>'),
        )

        super().__init__(*args, **kwargs)

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

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'change_password'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field('new_password_1', template='materialize_css_forms/layout/password.html'),
            Field('new_password_2', template='materialize_css_forms/layout/password.html'),
            HTML('<div class="align-center">'),
            FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )
        super().__init__(*args, **kwargs)

    def clean(self):
        p1, p2 = self.data.get('new_password_1', ''), self.data.get('new_password_2', '')
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
        self.user = kwargs.get('user')
        if 'user' in kwargs:
            del kwargs['user']
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Field('old_password', template='materialize_css_forms/layout/password.html'),
            Field('new_password_1', template='materialize_css_forms/layout/password.html'),
            Field('new_password_2', template='materialize_css_forms/layout/password.html'),
            HTML('<div class="align-center">'),
            FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )

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
        del kwargs['hash']
        del kwargs['user']

        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Field('new_password_1', template='materialize_css_forms/layout/password.html'),
            Field('new_password_2', template='materialize_css_forms/layout/password.html'),
            Field('gonzo', type='hidden', value=initial['gonzo']),
            Field('hash', type='hidden', value=initial['gonzo']),
            HTML('<div class="align-center">'),
            FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )

    def gen_gonzo(self):
        from libs.utils import do_gonzo

        return do_gonzo(self.hash)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        password = self.get_password()
        if password:
            if self.data.get('gonzo') != self.gen_gonzo():
                raise ValidationError('Ocurrió un error interno.')
            user = get_object_or_404(User, id=self.user)
            if not default_token_generator.check_token(user, self.hash):
                raise ValidationError('Ocurrió un error interno.')
        return self.data
