# -*- coding: utf-8 -*-
import re
from pydoc import locate

from django.conf import settings
from django.http import UnreadablePostError
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password, get_password_validators
from django.contrib.auth.tokens import default_token_generator
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
from django.urls import reverse
from django.utils.timezone import now
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_recaptcha.fields import ReCaptchaField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, BaseInput, Field, Fieldset, HTML
from crispy_forms.bootstrap import FormActions
from crispy_forms.utils import get_template_pack
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import RegionalPhoneNumberWidget

from .models import Subscription, Subscriber, email_extra_validations, email_i18n, ALPHANUM_STR
from .utils import get_all_newsletters
from .exceptions import EmailValidationError
from . import get_app_template


CSS_CLASS = 'form-input1'
RE_ALPHANUM = re.compile(ALPHANUM_STR)
SUBSCRIPTION_PHONE_TIME_CHOICES = (
    ('1', 'Cualquier hora (9:00 a 20:00)'),
    ('2', 'En la mañana (9:00 a 12:00)'),
    ('3', 'En la tarde (12:00 a 18:00)'),
    ('4', 'En la tarde-noche (18:00 a 20:00)'),
)
TEMPLATE_PACK = get_template_pack()

# password validators
PASSWORD_MIN_LENGTH, PASSWORD_VALIDATORS = None, getattr(settings, 'AUTH_PASSWORD_VALIDATORS', None)
min_len_found = False
if PASSWORD_VALIDATORS:
    for validator in PASSWORD_VALIDATORS:
        for key, value in validator.items():
            if key == "NAME" and value == "django.contrib.auth.password_validation.MinimumLengthValidator":
                PASSWORD_MIN_LENGTH, min_len_found = validator.get("OPTIONS", {}).get("min_length"), True
                break
        if min_len_found:
            break
PASSWORD_MIN_LENGTH = PASSWORD_MIN_LENGTH or 8
custom_forms_module = getattr(settings, "THEDAILY_FORMS_MODULE", None)


def get_default_province():
    return getattr(settings, 'THEDAILY_PROVINCE_CHOICES_INITIAL', None)


def custom_layout(form_id, *args, **kwargs):
    """
    Maybe this feature can be better migrated to a third party module which override the forms or directly redefine
    them. And make a function to be called from the views to get the customized forms, if any, and default to the ones
    defined here.
    """
    if custom_forms_module:
        layout_function = locate(f"{custom_forms_module}.{form_id}")
        if callable(layout_function):
            try:
                return layout_function(*args, **kwargs)
            except Exception as exc:
                if settings.DEBUG:
                    print(f"Error calling the custom layout function for '{form_id}' form: {exc}")


def terms_and_conditions_field(label="Leí y acepto los <a>términos y condiciones</a>", required=False):
    return BooleanField(label=mark_safe(label), required=required)


def terms_and_conds_accepted_field(**extra_kwargs):
    return Field('terms_and_conds_accepted', css_class='filled-in', **extra_kwargs)


def terms_and_conditions_layout_tuple(**extra_kwargs):
    return (
        terms_and_conds_accepted_field(**extra_kwargs),
    ) if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID or extra_kwargs.get('required', False) else ()


terms_and_conditions_prelogin = (
    settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
    and getattr(settings, "THEDAILY_TERMS_AND_CONDITIONS_PRELOGIN", True)
)


def check_password_strength(password, user=None):
    return validate_password(
        password, user, get_password_validators(PASSWORD_VALIDATORS) if PASSWORD_VALIDATORS else None
    )


def clean_terms_and_conds(form):
    terms_and_conditions = form.cleaned_data.get("terms_and_conds_accepted")
    if terms_and_conditions:
        return terms_and_conditions
    else:
        form.add_error("terms_and_conds_accepted", ValidationError('Los términos y condiciones deben ser aceptados.'))


def phone_is_blocklisted(phone):
    return any(phone.startswith(t) for t in getattr(settings, 'TELEPHONES_BLOCKLIST', []))


def clean_phone_field(form):
    phone = getattr(form.cleaned_data.get('phone', ""), "as_e164", "")
    if phone and phone_is_blocklisted(phone):
        # Raise error to minimize the info given to possible bot
        raise UnreadablePostError
    else:
        return phone


class Submit(BaseInput):
    """
    Use a custom submit because crispy's adds btn and btn-primary in the class attribute
    """
    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'submit submitButton' if TEMPLATE_PACK == 'uni_form' else ''
        super().__init__(*args, **kwargs)


class EmailInput(TextInput):
    input_type = 'email'


class CrispyFormHelper(FormHelper):
    form_style = 'inline'
    form_class = 'form-horizontal'
    help_text_inline = True
    form_tag = False


class CrispyModelFormHelper(CrispyFormHelper):
    label_class = 'col-sm-2'
    field_class = 'col-sm-8'


custom_helper_class = getattr(settings, "THEDAILY_FORMS_HELPER_CLASS", None)


class CrispyForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = (locate(custom_helper_class) if custom_helper_class else CrispyFormHelper)()


class CrispyModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = (locate(custom_helper_class) if custom_helper_class else CrispyModelFormHelper)()


class PreLoginForm(CrispyForm):
    email = CharField(label=_('Email'), widget=TextInput(attrs={'class': CSS_CLASS}))
    if terms_and_conditions_prelogin:
        terms_and_conds_accepted = terms_and_conditions_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = 'account_login'
        self.helper.form_action = reverse('account-login')
        self.helper.layout = Layout(*self.layout_args())

    def layout_args(self):
        return (
            (Field('email', title="Ingresá tu email", template='materialize_css_forms/layout/email-login.html'),)
            + ((terms_and_conditions_layout_tuple()) if terms_and_conditions_prelogin else ())
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


class LoginForm(CrispyForm):
    name_or_mail = CharField(label='Email', widget=TextInput(attrs={'class': CSS_CLASS}))
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(attrs={'class': CSS_CLASS, 'autocomplete': 'current-password', 'autocapitalize': 'none'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = 'account_login'
        self.helper.layout = (
            custom_layout(self.helper.form_id, self)
            or Layout(
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
        )

    def clean(self):
        data, result = self.data, None
        USER_PASS_ERROR, nom = 'Email y/o contraseña incorrectos.', data.get('name_or_mail', '').strip()
        if '@' in nom:
            try:
                self.username = User.objects.get(email__iexact=nom).username
            except Exception:
                self.add_error(None, ValidationError(USER_PASS_ERROR))
            else:
                result = data
        else:
            try:
                self.username = Subscriber.objects.get(name__iexact=nom).user.username
            except Exception:
                if User.objects.filter(username__iexact=nom).count():
                    self.username = nom
                    result = data
                else:
                    self.add_error(None, ValidationError(USER_PASS_ERROR))
            else:
                result = data
        return result


class BaseUserForm(CrispyModelForm):

    def custom_clean(self, exclude_self=False, error_use_next=True):
        cleaned_data = super().clean()
        error_msg, error_code = email_extra_validations(
            self.instance.email,
            cleaned_data.get('email'),
            self.instance.id if exclude_self else None,
            error_use_next and (cleaned_data.get('next_page', '/') or "/"),
        )
        if error_msg:
            self.add_error('email', ValidationError(error_msg))
        else:
            self.instance.email_extra_validations_done = True  # useful flag for the pre_save signal
            return cleaned_data

    def clean(self):
        return self.custom_clean()

    def clean_first_name(self):
        # TODO: sync with django-admin validations because for ex. "@" is allowed there and not here
        first_name = self.cleaned_data.get('first_name')
        if not RE_ALPHANUM.match(first_name):
            self.add_error(
                'first_name',
                ValidationError(
                    'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
                ),
            )
        else:
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
        self.helper.form_id = 'user_form'
        self.helper.layout = (
            custom_layout(self.helper.form_id)
            or Layout(Fieldset('Datos personales', 'first_name', 'last_name', 'email'))
        )

    def clean(self):
        return self.custom_clean(True, False)

    class Meta(BaseUserForm.Meta):
        widgets = {
            'email': EmailInput(
                attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
            ),
        }


def first_name_field():
    return CharField(
        label='Nombre',
        widget=TextInput(attrs={'autocomplete': 'given-name', 'autocapitalize': 'sentences', 'spellcheck': 'false'}),
    )


def last_name_field():
    return CharField(
        label='Apellido',
        widget=TextInput(attrs={'autocomplete': 'family-name', 'autocapitalize': 'sentences', 'spellcheck': 'false'}),
    )


def email_field():
    return EmailField(
        label=_('Email'),
        widget=EmailInput(
            attrs={'inputmode': 'email', 'autocomplete': 'email', 'autocapitalize': 'none', 'spellcheck': 'false'}
        ),
    )


def phone_field():
    return PhoneNumberField(
        label='Teléfono',
        required=False,
        widget=RegionalPhoneNumberWidget(
            attrs={'class': 'textinput textInput', 'autocomplete': 'tel', 'spellcheck': 'false'}
        ),
    )


class SignupForm(BaseUserForm):
    """
    Formulario con campos para crear una instancia del modelo User
    """
    first_name = first_name_field()
    last_name = last_name_field()
    email = email_field()
    phone = phone_field()
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field()
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = 'signup_form'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            *(
                'first_name',
                'last_name',
                'email',
                Field(
                    'password',
                    minlength=str(PASSWORD_MIN_LENGTH),
                    template='materialize_css_forms/layout/password.html',
                ),
                'phone',
            )
            + terms_and_conditions_layout_tuple()
            + (
                'next_page',
                HTML('<div class="align-center">'),
                Submit('save', self.initial.get("save", "Crear cuenta"), css_class='ut-btn ut-btn-l'),
                HTML('</div>'),
            )
        )
        # uncomment next lines to test error rendering without interaction
        # self.cleaned_data = {}
        # self.add_error(None, ValidationError(mark_safe("this is a global error <em>test</em> one")))
        # self.add_error(None, ValidationError(mark_safe("this is a global error <em>test</em> two")))
        # self.add_error("first_name", ValidationError(mark_safe("this is a <em>test</em> error for field")))
        # self.add_error("last_name", ValidationError(mark_safe("this is a <em>test</em> error for field")))
        # self.add_error("email", ValidationError(mark_safe("this is a <em>test</em> error for field")))
        # self.add_error("password", ValidationError(mark_safe("this is a <em>test</em> error for field")))
        # self.add_error("terms_and_conds_accepted", ValidationError(mark_safe("im a <em>test</em> error for field")))

    def clean_password(self):
        data = self.cleaned_data
        password = data.get('password')
        return check_password_strength(password) or password

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)

    def create_user(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        user = User.objects.create_user(email, email, password)
        if not getattr(user, 'subscriber', None):
            user.subscriber, created = Subscriber.objects.get_or_create_deferred(user=user)
        if not user.subscriber.phone:
            user.subscriber.phone = self.cleaned_data.get('phone', '')
        if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
            user.subscriber.terms_and_conds_accepted = self.cleaned_data.get('terms_and_conds_accepted')
        user.subscriber.save()
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.is_active = False
        user.save()
        return user

    class Meta(BaseUserForm.Meta):
        fields = ('first_name', 'last_name', 'email', 'password')
        widgets = {
            'password': PasswordInput(
                attrs={
                    'class': 'textinput textInput',
                    'autocomplete': 'new-password',
                    'autocapitalize': 'none',
                    'spellcheck': 'false',
                    "minlength": PASSWORD_MIN_LENGTH,
                }
            )
        }


class SignupCaptchaForm(SignupForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *(
                'first_name',
                'last_name',
                'email',
                Field('password', template='materialize_css_forms/layout/password.html'),
                'phone',
            )
            + terms_and_conditions_layout_tuple()
            + (
                HTML('<strong>Comprobá que no sos un robot</strong>'),
                'captcha',
                'next_page',
                HTML('<div class="align-center">'),
                Submit('save', 'Crear cuenta', css_class='ut-btn ut-btn-l'),
                HTML('</div>'),
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


class ProfileForm(CrispyModelForm):
    phone = phone_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "profile_form"
        self.helper.layout = Layout(
            Fieldset('Datos de suscriptor', 'document_type', 'document', 'phone'),
            Fieldset('Ubicación', 'country', 'province', 'city', 'address'),
        )

    class Meta:
        model = Subscriber
        fields = ('address', 'country', 'city', 'province', "document_type", 'document', 'phone')


class ProfileExtraDataForm(CrispyModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["newsletters"].choices = [(item.slug, item.name) for item in get_all_newsletters()]
        self.helper.layout = Layout(
            HTML('{%% include "%s" %%}' % get_app_template('profile/suscripciones.html')),
            # include push notifications section if it's configured
            HTML(
                '{%% if push_notifications_keys_set %%}{%% include "%s" %%}{%% endif %%}' % (
                    "profile/push_notifications.html"
                )
            ),
            Field('newsletters', template=get_app_template('profile/newsletters.html')),
            HTML('{%% include "%s" %%}' % get_app_template('profile/communications_start_section.html')),
            Field('allow_news', template=get_app_template('profile/allow_news.html')),
            Field('allow_promotions', template=get_app_template('profile/allow_promotions.html')),
            Field('allow_polls', template=get_app_template('profile/allow_polls.html')),
            HTML('</section>'),
        )

    class Meta:
        model = Subscriber
        fields = ('allow_news', 'allow_promotions', 'allow_polls', "newsletters")


# NOTE: first and last name fields are used in the subscriber form, but allways to fill its related User object because
#       the subscriber object has no name fields (it uses the User's instead).

class SubscriberForm(CrispyModelForm):
    first_name = first_name_field()
    last_name = last_name_field()
    email = email_field()
    phone = phone_field()
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Fieldset(
                'Datos personales',
                Field('first_name'),
                Field('last_name'),
                Field('email', readonly=True),
                Field('phone'),
            )
        )

    class Meta:
        model = Subscriber
        fields = ('first_name', 'last_name', 'email', 'phone')

    def clean_namefield(self, field_name):
        field_value = self.cleaned_data.get(field_name)
        if not RE_ALPHANUM.match(field_value):
            self.add_error(
                field_name,
                ValidationError(
                    'El nombre/apellido sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
                ),
            )
        return field_value

    def clean_first_name(self):
        return self.clean_namefield('first_name')

    def clean_last_name(self):
        return self.clean_namefield('last_name')

    def clean_phone(self):
        return clean_phone_field(self)

    def clean_email(self):
        return self.cleaned_data.get('email').lower()

    def is_valid(self, subscription_type, payment_type='tel'):
        result = super().is_valid()

        if result and payment_type == 'tel':
            # continue validation to check for repeated email and subsc. type, for "tel" subscriptions in same day:
            try:
                s = Subscription.objects.get(
                    billing_email__iexact=self.cleaned_data.get('email'), date_created__date=now().date()
                )
                if subscription_type in s.subscription_type_prices.values_list('subscription_type', flat=True):
                    self.add_error('email', ValidationError(f"Su {email_i18n} ya posee una suscripción en proceso."))
                    result = False
            except Subscription.MultipleObjectsReturned:
                # TODO: this can be relaxed using the same "if" above and only invalidate when all objects found
                #       evaluates the "if" to True, and also the view should be changed to be aware of this.
                self.add_error(
                    'email', ValidationError(f"Su {email_i18n} ya posee más de una suscripción en proceso.")
                )
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
        label='Departamento', choices=settings.THEDAILY_PROVINCE_CHOICES, initial=get_default_province()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Field('first_name'),
            Field('last_name'),
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
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'city', 'province')


class SubscriberSubmitForm(SubscriberForm):
    """
    Adds a submit button to the SubscriberForm
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Fieldset('Datos personales', 'first_name', 'last_name', 'email', 'phone'),
            FormActions(Submit('save', 'Enviar suscripción')),
        )


class SubscriberSignupForm(SubscriberForm):
    """
    Adds a password to the SubscriberForm to also signup
    """
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(
            attrs={
                'class': 'textinput textInput',
                'autocomplete': 'new-password',
                'autocapitalize': 'none',
                'spellcheck': 'false',
                'minlength': PASSWORD_MIN_LENGTH,
            }
        ),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = custom_layout("subscriber_signup_form") or Layout(
            'first_name',
            'last_name',
            'email',
            Field('password', template='materialize_css_forms/layout/password.html'),
            'phone',
            'next_page',
        )

    def is_valid(self, subscription_type, payment_type=None):
        # call is_valid first with the parent class, only to fill the cleaned_data
        result = super(SubscriberForm, self).is_valid()
        if result:
            # validate signup first
            signup_form = SignupForm(
                {
                    'first_name': self.cleaned_data.get('first_name'),
                    'last_name': self.cleaned_data.get('last_name'),
                    'email': self.cleaned_data.get('email'),
                    'password': self.cleaned_data.get('password'),
                    'phone': self.cleaned_data.get('phone'),
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
    """
    Adds password (like SubscriberSignupForm) and address
    """
    password = CharField(
        label='Contraseña',
        widget=PasswordInput(
            attrs={
                'class': 'textinput textInput',
                'autocomplete': 'new-password',
                'autocapitalize': 'none',
                'spellcheck': 'false',
                'minlength': PASSWORD_MIN_LENGTH,
            }
        ),
    )
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            'first_name',
            'last_name',
            'email',
            Field('password', template='materialize_css_forms/layout/password.html'),
            'phone',
            'next_page',
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
                    'last_name': self.cleaned_data.get('last_name'),
                    'email': self.cleaned_data.get('email'),
                    'password': self.cleaned_data.get('password'),
                    'phone': self.cleaned_data.get('phone'),
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


def preferred_time_field():
    return ChoiceField(label='Hora de contacto preferida', choices=SUBSCRIPTION_PHONE_TIME_CHOICES, initial='1')


class PhoneSubscriptionForm(CrispyForm):
    full_name = CharField(
        label='Nombre completo',
        widget=TextInput(
            attrs={
                "class": "textinput textInput",
                'autocomplete': 'given-name',
                'autocapitalize': 'sentences',
                'spellcheck': 'false',
            }
        ),
    )
    phone = phone_field()
    preferred_time = preferred_time_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = True
        self.helper.form_id = 'phone_subscription_form'
        self.helper.layout = Layout(
            HTML('<h3 class="small">Tus datos</h3>'),
            "full_name",
            "phone",
            HTML('<div class="row">'),  # next field will close this div tag
            Field('preferred_time', template='preferred_time_visible.html'),
            HTML('<div class="ld-block--sm align-center">'),
            FormActions(Submit('save', 'Enviar', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )


class WebSubscriptionForm(CrispyModelForm):
    subscription_type_prices = ChoiceField(choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, widget=HiddenInput())
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *terms_and_conditions_layout_tuple()
            + (
                HTML('<div class="ld-block--sm align-center">'),
                FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
                HTML(
                    '<div class="ld-text-secondary align-center ld-subscription-step" style="display:none;">'
                    'Paso 1 de 2'
                ),
                Field('subscription_type_prices'),
            )
        )

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)

    class Meta:
        model = Subscription
        fields = ['subscription_type_prices']


class WebSubscriptionPromoCodeForm(WebSubscriptionForm):
    promo_code = CharField(label='Código promocional (opcional)', required=False, max_length=8)


class WebSubscriptionCaptchaForm(WebSubscriptionForm):
    captcha = ReCaptchaField(label='')


class WebSubscriptionPromoCodeCaptchaForm(WebSubscriptionPromoCodeForm):
    captcha = ReCaptchaField(label='')


class SubscriptionForm(WebSubscriptionForm):
    payment_type = ChoiceField(
        label='Elegí la forma de suscribirte', choices=(('tel', 'Telefónica (te llamamos)'),), initial='tel'
    )
    preferred_time = preferred_time_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            *(
                HTML('<div class="col s12" style="margin-top: 30px; margin-bottom: 50px;">'),
                Field('payment_type', template='payment_type.html'),
                Field('preferred_time', template='preferred_time.html'),
                HTML('</div>'),
            )
            + terms_and_conditions_layout_tuple()
            + (
                HTML('<div class="ld-block--sm align-center">'),
                FormActions(Submit('save', 'Continuar', css_class='ut-btn ut-btn-l')),
                HTML(
                    '<div class="ld-text-secondary align-center ld-subscription-step" style="display:none;">'
                    'Paso 1 de 2'
                ),
                Field('subscription_type_prices'),
            )
        )

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
            self.add_error("promo_code", ValidationError('Código promocional incorrecto.'))
        else:
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
            + terms_and_conditions_layout_tuple()
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


class GoogleSigninForm(CrispyModelForm):
    """
    Asks for possible missing data (phone or terms and conds acceptance) when sign-in is made by Google
    """
    phone = phone_field()
    if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID:
        terms_and_conds_accepted = terms_and_conditions_field()
    next_page = CharField(required=False, widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        submit_label = 'crear cuenta' if kwargs.pop("is_new", None) else "continuar"
        assume_tnc_accepted = kwargs.pop("assume_tnc_accepted", False)
        super().__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.form_id = 'google_signin'
        self.helper.layout = Layout(
            *('phone', "next_page")
            + terms_and_conditions_layout_tuple(**({"type": "hidden"} if assume_tnc_accepted else {}))
            + (FormActions(Submit('save', submit_label, css_class='ut-btn ut-btn-l')),)
        )

    class Meta:
        model = Subscriber
        fields = ('phone',) + (
            ("terms_and_conds_accepted",) if settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID else ()
        )
        widgets = {'phone': RegionalPhoneNumberWidget(attrs={'autocomplete': 'tel', 'spellcheck': 'false'})}

    def clean_phone(self):
        return clean_phone_field(self)

    def clean_terms_and_conds_accepted(self):
        return clean_terms_and_conds(self)


class GoogleSignupForm(GoogleSigninForm):
    """
    Child class to use the same form but without the submit button
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            HTML('<div class="align-center">Para continuar completá los siguientes datos</div>'), 'phone'
        )

    def is_valid(self, *args):
        # wrapper to allow compatibility with calls with arguments
        return super().is_valid()


class GoogleSignupAddressForm(GoogleSignupForm):
    """
    Child class to not exclude address info (address, city and province)
    """
    address = CharField(
        label='Dirección',
        widget=TextInput(
            attrs={'autocomplete': 'street-address', 'autocapitalize': 'sentences', 'spellcheck': 'false'}
        ),
    )
    city = CharField(label='Ciudad')
    province = ChoiceField(
        label='Departamento', choices=settings.THEDAILY_PROVINCE_CHOICES, initial=get_default_province()
    )

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
        widgets = {'phone': RegionalPhoneNumberWidget(attrs={'autocomplete': 'tel', 'spellcheck': 'false'})}


class PasswordResetRequestForm(CrispyForm):
    username_or_email = CharField(label='Email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.form_id = 'reset_password'
        self.helper.form_action = reverse('account-password_reset')
        self.helper.layout = (
            custom_layout(self.helper.form_id, self)
            or Layout(
                Field(
                    'username_or_email',
                    id="username_or_email",
                    title="Nombre de usuario o email.",
                    template='materialize_css_forms/layout/email-login.html',
                ),
                HTML('<div class="align-center form-group">'),
                FormActions(Submit('save', 'Restablecer contraseña', css_class='ut-btn ut-btn-l')),
                HTML('</div>'),
            )
        )

    def clean_username_or_email(self):
        nom = self.cleaned_data.get('username_or_email', "").strip()
        if "@" in nom:
            try:
                user = User.objects.get(email__iexact=nom)
                self.cleaned_data["user"] = user
            except User.MultipleObjectsReturned:
                mail_managers("Multiple email in users", nom)
                self.add_error(None, ValidationError("undisclosed"))
            except User.DoesNotExist:
                self.add_error(None, ValidationError("undisclosed"))
        else:
            try:
                user = User.objects.get(username=nom)
                self.cleaned_data["user"] = user
            except User.DoesNotExist:
                self.add_error(None, ValidationError("undisclosed"))
        return nom


class ConfirmEmailRequestForm(CrispyForm):
    username_or_email = CharField(label='Email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.form_id = 'confirm_email'
        self.helper.layout = Layout(
            Field(
                'username_or_email',
                id="username_or_email",
                title="Nombre de usuario o email.",
                template='materialize_css_forms/layout/email-login.html',
            ),
            HTML('<div class="align-center form-group">'),
            FormActions(Submit('save', 'Enviar mensaje de activación', css_class='ut-btn ut-btn-l')),
            HTML('</div>'),
        )

    def clean_username_or_email(self):
        nom = self.cleaned_data.get('username_or_email', "").strip()
        inactive_users = User.objects.filter(is_active=False)
        if "@" in nom:
            try:
                user = inactive_users.get(email__iexact=nom)
                self.cleaned_data["user"] = user
            except User.MultipleObjectsReturned:
                mail_managers("Multiple email in users", nom)
                self.add_error(None, ValidationError("undisclosed"))
            except User.DoesNotExist:
                self.add_error(None, ValidationError("undisclosed"))
        else:
            try:
                user = inactive_users.get(username=nom)
                self.cleaned_data["user"] = user
            except User.DoesNotExist:
                self.add_error(None, ValidationError("undisclosed"))
        return nom


class PasswordChangeBaseForm(CrispyForm):
    new_password_1 = CharField(
        label='Nueva contraseña',
        widget=PasswordInput(
            attrs={
                "autocomplete": "new-password",
                'autocapitalize': 'none',
                'spellcheck': 'false',
                "minlength": PASSWORD_MIN_LENGTH,
            }
        ),
    )
    new_password_2 = CharField(
        label='Repetir contraseña',
        widget=PasswordInput(attrs={"autocomplete": "new-password", 'autocapitalize': 'none', 'spellcheck': 'false'}),
    )

    def __init__(self, *args, **kwargs):
        if 'user' in kwargs:
            self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.form_id = 'change_password'
        self.helper.layout = (
            custom_layout(self.helper.form_id, False)
            or Layout(
                Field('new_password_1', template='materialize_css_forms/layout/password.html'),
                Field('new_password_2', template='materialize_css_forms/layout/password.html'),
                HTML('<div class="align-center">'),
                FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
                HTML('</div>'),
            )
        )

    def clean(self):
        p1, p2 = self.data.get('new_password_1', ''), self.data.get('new_password_2', '')
        if p1 and p2:
            if p1 != p2:
                self.add_error('new_password_1', ValidationError('Las contraseñas no coinciden.'))
            elif not check_password_strength(p1, getattr(self, 'user', None)):
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
        super().__init__(*args, **kwargs)
        self.helper.layout = (
            custom_layout(self.helper.form_id)
            or Layout(
                Field('old_password', template='materialize_css_forms/layout/password.html'),
                Field('new_password_1', template='materialize_css_forms/layout/password.html'),
                Field('new_password_2', template='materialize_css_forms/layout/password.html'),
                HTML('<div class="align-center">'),
                FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
                HTML('</div>'),
            )
        )

    def clean_old_password(self):
        from django.contrib.auth import authenticate

        password = self.cleaned_data.get('old_password', '')
        if authenticate(username=self.user.username, password=password):
            return password
        else:
            self.add_error("old_password", ValidationError('Contraseña incorrecta.'))


class PasswordResetForm(PasswordChangeBaseForm):
    new_password_1 = CharField(
        label='Contraseña',
        widget=PasswordInput(
            attrs={
                "autocomplete": "new-password",
                'autocapitalize': 'none',
                'spellcheck': 'false',
                "minlength": PASSWORD_MIN_LENGTH,
            }
        ),
    )
    hash = CharField(widget=HiddenInput())
    gonzo = CharField(widget=HiddenInput())

    def __init__(self, *args, **kwargs):
        if 'hash' not in kwargs:
            raise AttributeError('Missing hash')
        self.hash = kwargs.pop('hash')
        initial = {'hash': self.hash}
        initial['gonzo'] = self.gen_gonzo()
        kwargs['initial'] = initial

        super().__init__(*args, **kwargs)

        self.helper.layout = (
            custom_layout(self.helper.form_id, False, initial['gonzo'])
            or Layout(
                Field('new_password_1', template='materialize_css_forms/layout/password.html'),
                Field('new_password_2', template='materialize_css_forms/layout/password.html'),
                Field('gonzo', value=initial['gonzo']),
                Field('hash', value=initial['gonzo']),
                HTML('<div class="align-center">'),
                FormActions(Submit('save', 'Elegir contraseña', css_class='ut-btn ut-btn-l')),
                HTML('</div>'),
            )
        )

    def gen_gonzo(self):
        from libs.utils import do_gonzo

        return do_gonzo(self.hash)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        password, err_msg = self.get_password(), "Ocurrió un error interno."
        if password:
            if self.data.get('gonzo') != self.gen_gonzo():
                self.add_error(None, ValidationError(err_msg))
            else:
                if not default_token_generator.check_token(self.user, self.hash):
                    self.add_error(None, ValidationError(err_msg))
                else:
                    return self.data
