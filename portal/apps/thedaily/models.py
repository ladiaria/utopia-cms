# -*- coding: utf-8 -*-

import re
import json
import requests
import pymongo
from hashids import Hashids
from pymailcheck import split_email
from pyisemail import is_email

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.core.mail import mail_managers
from django.core.validators import RegexValidator, validate_email
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models import CASCADE
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    EmailField,
    ForeignKey,
    Model,
    OneToOneField,
    PositiveIntegerField,
    TextField,
    ImageField,
    PositiveSmallIntegerField,
    DecimalField,
    Manager,
    ManyToManyField,
)
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.db.utils import IntegrityError
from django.dispatch import receiver
from django.urls import reverse

from social_django.models import UserSocialAuth

from apps import mongo_db, bouncer_blocklisted, whitelisted_domains
from core.models import Edition, Publication, Category, ArticleViewedBy

from .exceptions import UpdateCrmEx, EmailValidationError


GA_CATEGORY_CHOICES = (('D', 'Digital'), ('P', 'Papel'))


class SubscriptionPrices(Model):
    subscription_type = CharField(
        'tipo', max_length=7, choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, unique=True, default='PAPYDIM'
    )
    price = DecimalField('Precio', max_digits=7, decimal_places=2)
    order = PositiveSmallIntegerField('Orden', null=True)
    paypal_button_id = CharField(max_length=13, null=True, blank=True)
    auth_group = ForeignKey(Group, on_delete=CASCADE, verbose_name='Grupo asociado al permiso', blank=True, null=True)
    publication = ForeignKey(Publication, on_delete=CASCADE, blank=True, null=True)
    ga_sku = CharField(max_length=10, blank=True, null=True)
    ga_name = CharField(max_length=64, blank=True, null=True)
    ga_category = CharField(max_length=1, choices=GA_CATEGORY_CHOICES, blank=True, null=True)

    def __str__(self):
        return "%s -- $ %s " % (self.get_subscription_type_display(), self.price)

    class Meta:
        verbose_name = 'Precio'
        verbose_name_plural = 'Precios'
        ordering = ['order']


alphanumeric = RegexValidator(
    '^[A-Za-z0-9ñüáéíóúÑÜÁÉÍÓÚ _\'.\-]*$',
    'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.',
)


class Subscriber(Model):
    """
    TODO:
     - Create an "extra" JSON field to save custom-bussiness-related subscriber data. (using plan_id for this now)
     - Many ladiaria custom fields like "lento_pdf" should be removed (ladiaria will be using them in "extra").
     - Keep newsletters M2M relations for those newsletters that were discontinued (their publication or category have
       changed its has_newsletter attr from True to False) now this M2M rows are removed when the subscriber is saved,
       for example in the admin or by the user itself using the edit profile page.
    """

    contact_id = PositiveIntegerField('CRM id', unique=True, editable=True, blank=True, null=True)
    user = OneToOneField(
        User, on_delete=CASCADE, verbose_name='usuario', related_name='subscriber', blank=True, null=True
    )

    # TODO: ver la posibilidad de eliminarlo ya que es el "first_name" del modelo django.contrib.auth.models.User
    name = CharField('nombre', max_length=255, validators=[alphanumeric])

    # agregamos estos campos para unificar la info de User y Subscriber
    address = CharField('dirección', max_length=255, blank=True, null=True)
    country = CharField('país', max_length=50, blank=True, null=True)
    city = CharField('ciudad', max_length=64, blank=True, null=True)
    province = CharField(
        'departamento', max_length=20, choices=settings.THEDAILY_PROVINCE_CHOICES, blank=True, null=True
    )

    profile_photo = ImageField(upload_to='perfiles', blank=True, null=True)
    document = CharField('documento de identidad', max_length=50, blank=True, null=True)
    phone = CharField('teléfono', max_length=20)

    date_created = DateTimeField('fecha de registro', auto_now_add=True, editable=False)
    downloads = PositiveIntegerField('descargas', default=0, blank=True, null=True)

    terms_and_conds_accepted = BooleanField(default=False)
    pdf = BooleanField(default=False)
    lento_pdf = BooleanField('pdf L.', default=False)
    ruta = PositiveSmallIntegerField(blank=True, null=True)
    plan_id = TextField(blank=True, null=True)
    ruta_lento = PositiveSmallIntegerField(blank=True, null=True)
    ruta_fs = PositiveSmallIntegerField(blank=True, null=True)
    newsletters = ManyToManyField(Publication, blank=True, limit_choices_to={'has_newsletter': True})
    category_newsletters = ManyToManyField(Category, blank=True, limit_choices_to={'has_newsletter': True})
    allow_news = BooleanField('acepta novedades', default=True)
    allow_promotions = BooleanField('acepta promociones', default=True)
    allow_polls = BooleanField('acepta encuestas', default=True)
    # TODO: explain the utility of this field or remove it.
    subscription_mode = CharField(max_length=1, null=True, blank=True, default=None)
    last_paid_subscription = DateTimeField('Ultima subscripcion comienzo', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.document:
            non_decimal = re.compile(r'[^\d]+')
            self.document = non_decimal.sub('', self.document)
        super(Subscriber, self).save(*args, **kwargs)

    def download(self, pdfinstance):
        try:
            download = SubscriberEditionDownloads.objects.get(subscriber=self, edition=pdfinstance)
            download.downloads += 1
        except SubscriberEditionDownloads.DoesNotExist:
            download = SubscriberEditionDownloads()
            download.subscriber = self
            download.edition = pdfinstance
            download.downloads = 1
        download.save()
        self.downloads += 1
        self.save()

    def is_subscriber(self, pub_slug=settings.DEFAULT_PUB, operation="get"):
        try:

            if self.user:

                if self.user.is_staff:
                    return True

                elif pub_slug in getattr(settings, 'THEDAILY_IS_SUBSCRIBER_CUSTOM_PUBLICATIONS', ()):
                    is_subscriber_custom = __import__(
                        settings.THEDAILY_IS_SUBSCRIBER_CUSTOM_MODULE, fromlist=['is_subscriber']
                    ).is_subscriber
                    return is_subscriber_custom(self, pub_slug, operation)

                else:
                    if operation == "get":
                        return self.user.has_perm('thedaily.es_suscriptor_%s' % pub_slug)
                    elif operation == "set":
                        self.user.user_permissions.add(Permission.objects.get(codename='es_suscriptor_' + pub_slug))
                        return True
                    else:
                        raise ValueError("Unknown operation")

        except User.DoesNotExist:
            # rare, but we saw once this exception happen
            pass

        return False

    def is_digital_only(self):
        """Returns True only if this subcriber is subscribed only to the "digital" edition"""
        # TODO 2nd release: implement
        return self.is_subscriber()

    def make_token(self):
        return TimestampSigner().sign(self.user.username)

    def check_token(self, token):
        try:
            key = '%s:%s' % (self.user.username, token)
            TimestampSigner().unsign(key, max_age=60 * 60 * 48)  # Valid 2 days
        except (BadSignature, SignatureExpired):
            return False
        return True

    def user_is_active(self):
        return self.user and self.user.is_active

    user_is_active.short_description = 'user act.'
    user_is_active.boolean = True

    def is_subscriber_any(self):
        return any(
            self.is_subscriber(pub_slug)
            for pub_slug in getattr(
                settings, 'THEDAILY_IS_SUBSCRIBER_ANY', Publication.objects.values_list('slug', flat=True)
            )
        )

    def get_publication_newsletters_ids(self, exclude_slugs=[]):
        return list(
            self.newsletters.filter(has_newsletter=True).exclude(slug__in=exclude_slugs).values_list('id', flat=True)
        )

    def get_category_newsletters_ids(self, exclude_slugs=[]):
        return list(
            self.category_newsletters.filter(has_newsletter=True)
            .exclude(slug__in=exclude_slugs)
            .values_list('id', flat=True)
        )

    def get_newsletters_slugs(self):
        return list(self.newsletters.values_list('slug', flat=True)) + list(
            self.category_newsletters.values_list('slug', flat=True)
        )

    def remove_newsletters(self):
        self.newsletters.clear()
        self.category_newsletters.clear()

    def get_newsletters(self):
        return ', '.join(self.get_newsletters_slugs())

    get_newsletters.short_description = 'newsletters'

    def updatecrmuser_publication_newsletters(self, exclude_slugs=[]):
        if self.contact_id:
            try:
                updatecrmuser(
                    self.contact_id, 'newsletters', json.dumps(self.get_publication_newsletters_ids(exclude_slugs))
                )
            except requests.exceptions.RequestException:
                pass

    def updatecrmuser_category_newsletters(self, exclude_slugs=[]):
        if self.contact_id:
            try:
                updatecrmuser(
                    self.contact_id, 'area_newsletters', json.dumps(self.get_category_newsletters_ids(exclude_slugs))
                )
            except requests.exceptions.RequestException:
                pass

    def get_downloads(self, edition=None):
        if not edition:
            return self.downloads
        else:
            qs = self.edition_downloads.filter(edition=edition)
            if qs.count() == 0:
                return 0
            else:
                return qs[0].downloads

    def __str__(self):
        return self.name or self.get_full_name()

    def get_full_name(self):
        if not self.user.first_name and not self.user.last_name:
            return "Usuario sin nombre"
        else:
            return self.user.get_full_name()

    def get_latest_article_visited(self):
        """
        Returns info about the latest visit to an article from this subscriber.
        """
        # Search in mongodb first, if none found then search in db-table
        mdb = mongo_db.core_articleviewedby.find({'user': self.user.id}).sort('viewed_at', pymongo.DESCENDING)
        if mdb.count():
            latest = mdb[0]
            return (latest.get('article'), latest.get('viewed_at'))
        else:
            try:
                latest = self.user.articleviewedby_set.latest('viewed_at')
            except ArticleViewedBy.DoesNotExist:
                pass
            else:
                return (latest.article_id, latest.viewed_at)

    @property
    def user_email(self):
        return self.user.email if self.user else None

    def email_is_bouncer(self):
        return self.user_email in bouncer_blocklisted

    def get_absolute_url(self):
        return reverse('admin:thedaily_subscriber_change', args=[self.id])

    def hashed_id(self):
        return Hashids(settings.HASHIDS_SALT, 32).encode(int(self.id))

    class Meta:
        verbose_name = 'suscriptor'
        verbose_name_plural = "suscriptores"


def put_data_to_crm(api_url, data):
    """
    Performs an PUT request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    """
    api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
        res = requests.put(api_url, headers={'Authorization': 'Api-Key ' + api_key}, data=data)
        res.raise_for_status()
        res.json()


def post_data_to_crm(api_url, data):
    """
    Performs an POST request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    return request response
    """
    api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
        res = requests.post(api_url, headers={'Authorization': 'Api-Key ' + api_key}, data=data)
        res.raise_for_status()
        return res.json()


def delete_data_from_crm(api_url, data):
    """
    Performs an DELETE request to the CRM app
    api_url is the request url and data is the request body data
    If there are missing data for do the request; return None
    @param api_url: target url in str format
    @param data: request body data
    """
    api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key)):
        payload = json.dumps(data)
        headers = {
            'Authorization': 'Api-Key ' + api_key,
            'Content-Type': 'application/json'
        }
        res = requests.delete(api_url, headers=headers, data=payload)
        res.raise_for_status()
        res.json()


def updatecrmuser(contact_id, field, value):
    # TODO: next lines can be encapsulated in a new function (DRY), then call also from this module lines ~ 451
    api_url = settings.CRM_API_UPDATE_USER_URI
    data = {"contact_id": contact_id, "field": field, "value": value}
    put_data_to_crm(api_url, data)


def createcrmuser(name, email):
    api_url = settings.CRM_API_UPDATE_USER_URI
    return post_data_to_crm(api_url=api_url, data={"name": name, "email": email})


def deletecrmuser(email):
    api_url = settings.CRM_API_UPDATE_USER_URI
    return delete_data_from_crm(api_url, {"email": email})


def email_extra_validations(old_email, email, instance_id=None, next_page=None, allow_blank=False):
    msg, error_msg_prefix, error_code = None, "El email ingresado ", None
    error_msg_invalid = error_msg_prefix + 'no es un email válido.'
    error_msg_exists = error_msg_prefix + "ya posee una cuenta de usuario"
    error_msg_next = ("?next=" + next_page) if next_page else ""
    exclude_kwargs_user = {'id': instance_id} if instance_id else {}
    exclude_kwargs_user_sa = {'user_id': instance_id} if instance_id else {}

    if not email:
        if not allow_blank:
            msg, error_code = error_msg_invalid, EmailValidationError.INVALID

    else:
        email = email.lower()
        if old_email:
            old_email = old_email.lower()

        # 1. check if this email (only "on change") is included in our bouncers list
        if old_email != email and email in bouncer_blocklisted:
            msg = error_msg_prefix + "registra exceso de rebotes, no se permite su utilización."
            error_code = EmailValidationError.INVALID
        else:

            # 2. Django email validation
            try:
                validate_email(email)
            except ValidationError as ve:
                msg, error_code = ve.message, EmailValidationError.INVALID
            else:

                # 3. Domain validation + already used validation
                if (
                    not split_email(email)["domain"] in whitelisted_domains()
                    and not is_email(email, check_dns=getattr(settings, "THEDAILY_VALIDATE_EMAIL_CHECK_MX", True))
                ):
                    msg, error_code = error_msg_invalid, EmailValidationError.INVALID

                elif User.objects.filter(email__iexact=email).exclude(**exclude_kwargs_user).exists():
                    # TODO: use "reverse" to build the url
                    msg = '%s. <a href="/usuarios/entrar/%s">Ingresar</a>.' % (error_msg_exists, error_msg_next)

                elif UserSocialAuth.objects.filter(uid=email).exclude(**exclude_kwargs_user_sa).exists():
                    # TODO: use "reverse" to build the url
                    msg = '%s asociada a Google. <a href="/login/google-oauth2/%s">Ingresar con Google</a>.' % (
                        error_msg_exists, error_msg_next
                    )

                elif User.objects.filter(username__iexact=email).exclude(**exclude_kwargs_user).exists():
                    mail_managers("Multiple username in users", email)
                    msg = error_msg_prefix + 'no puede ser utilizado.'

    return msg, error_code


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    email_extra_validations_done, error_msg = getattr(instance, "email_extra_validations_done", False), None
    if email_extra_validations_done:
        # remove flag
        del instance.email_extra_validations_done

    try:
        update_fields, bypass = kwargs.get("update_fields"), False
        if update_fields:
            bypass = len(update_fields) == 1 and any(field in update_fields for field in ("last_login", "password"))
        actualusr = sender.objects.get(pk=instance.id)
        if not bypass and not email_extra_validations_done:
            # email extra validations on user modification (login and password change actions are not considered).
            error_msg, error_code = email_extra_validations(
                actualusr.email, instance.email, instance.id, allow_blank=True
            )
    except User.DoesNotExist:
        if not email_extra_validations_done:
            # email extra validations (user creation)
            error_msg, error_code = email_extra_validations(None, instance.email, allow_blank=True)
        actualusr = instance

    # raise if email extra validations returned something
    if error_msg:
        raise IntegrityError(error_msg)

    if not settings.CRM_UPDATE_USER_ENABLED or getattr(instance, "updatefromcrm", False):
        return True  # TODO: why True and not just "return"?

    # sync email if changed
    api_url = settings.CRM_API_UPDATE_USER_URI
    api_key = getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
    if all((settings.CRM_UPDATE_USER_ENABLED, api_url, api_key, actualusr.email != instance.email)):
        err_msg = "No se ha podido actualizar tu email, contactate con nosotros"
        try:
            contact_id = instance.subscriber.contact_id if instance.subscriber else None
            requests.put(
                api_url,
                headers={'Authorization': 'Api-Key ' + api_key},
                data={'contact_id': contact_id, 'email': actualusr.email, 'newemail': instance.email}
            ).raise_for_status()
        except requests.exceptions.RequestException:
            raise UpdateCrmEx(err_msg)


@receiver(pre_save, sender=Subscriber, dispatch_uid="subscriber_pre_save")
def subscriber_pre_save(sender, instance, **kwargs):
    if getattr(settings, 'THEDAILY_DEBUG_SIGNALS', False):
        print('DEBUG: subscriber_pre_save signal called')
    if not settings.CRM_UPDATE_USER_ENABLED or getattr(instance, "updatefromcrm", False):
        return True
    try:
        actual_sub = sender.objects.get(pk=instance.id)
        # TODO: change this 1-field-per-request approach to a new 1-request-only approach with all chanmges
        for crm_field, f in list(settings.CRM_UPDATE_SUBSCRIBER_FIELDS.items()):
            if getattr(actual_sub, f) != getattr(instance, f):
                try:
                    updatecrmuser(instance.contact_id, crm_field, getattr(instance, f))
                except requests.exceptions.RequestException:
                    raise UpdateCrmEx("No se ha podido actualizar tu perfil, contactate con nosotros")
    except Subscriber.DoesNotExist:
        # this happens only on creation
        pass


@receiver(m2m_changed, sender=Subscriber.newsletters.through, dispatch_uid="subscriber_newsletters_changed")
@receiver(
    m2m_changed, sender=Subscriber.category_newsletters.through, dispatch_uid="subscriber_area_newsletters_changed"
)
def subscriber_newsletters_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if settings.DEBUG:
        print(
            'DEBUG: thedaily.models.subscriber_newsletters_changed called with action=%s, pk_set=%s' % (action, pk_set)
        )
    if getattr(instance, "updatefromcrm", False):
        return True
    if instance.contact_id and action.startswith('post_'):
        # post_add with empty pk_set means "unchanged", do not sync in such scenario
        if action != 'post_add' or pk_set:
            try:
                updatecrmuser(
                    instance.contact_id,
                    ('area_' if model is Category else '')
                    + 'newsletters'
                    + ('_remove' if action == 'post_remove' else ''),
                    json.dumps(list(pk_set)) if pk_set else None,
                )
            except requests.exceptions.RequestException:
                # TODO: write to error log, then this errors can be monitored someway
                pass


@receiver(post_save, sender=User, dispatch_uid="createUserProfile")
def createUserProfile(sender, instance, created, **kwargs):
    """
    Creates a UserProfile object each time a User is created.
    Also keep sync the email field on Subscriptions.
    """
    subscriber, created = Subscriber.objects.get_or_create(user=instance)
    if instance.email:
        if created and settings.CRM_UPDATE_USER_CREATE_CONTACT:
            # TODO: handle exception or error return code
            res = createcrmuser(instance.get_full_name(), instance.email)
            contact_id = res.get('contact_id') if res else None
            print(contact_id)
            if not subscriber.contact_id:
                subscriber.contact_id = contact_id
                subscriber.save()
        try:
            instance.suscripciones.exclude(email=instance.email).update(email=instance.email)
        except Exception:
            pass


class OAuthState(Model):
    """
    Store partial social_auth OAuth state associated to the user being created
    to ask then for extra fields, such as the telephone number.
    @see libs.social_auth_pipeline
    """

    user = OneToOneField(User, on_delete=CASCADE)
    state = CharField(max_length=32, unique=True)
    fullname = CharField(max_length=255, blank=True, null=True)


class WebSubscriber(Subscriber):
    referrer = ForeignKey(
        Subscriber, on_delete=CASCADE, related_name='referred', verbose_name='referido', blank=True, null=True
    )


class SubscriberEditionDownloads(Model):
    subscriber = ForeignKey(Subscriber, on_delete=CASCADE, related_name='edition_downloads', verbose_name='suscriptor')
    edition = ForeignKey(Edition, on_delete=CASCADE, related_name='subscribers_downloads', verbose_name='edición')
    downloads = PositiveIntegerField('descargas', default=0)

    def __str__(self):
        return '%s - %s: %i' % (self.subscriber, self.edition, self.downloads)

    def save(self, *args, **kwargs):
        super(SubscriberEditionDownloads, self).save(*args, **kwargs)
        download = EditionDownload(subscriber=self)
        download.save()

    class Meta:
        ordering = ('-edition', '-downloads', 'subscriber')
        unique_together = ('subscriber', 'edition')
        verbose_name = 'descargas de edición'
        verbose_name_plural = 'descargas de ediciones'


class SentMail(Model):
    subscriber = ForeignKey(Subscriber, on_delete=CASCADE)
    subject = CharField('asunto', max_length=150)
    date_sent = DateTimeField('fecha de envio', auto_now_add=True, editable=False)


class SubscriberEvent(Model):
    subscriber = ForeignKey(Subscriber, on_delete=CASCADE)
    description = CharField('descripcion', max_length=150)
    date_occurred = DateTimeField(auto_now_add=True, editable=False)


class EditionDownload(Model):
    subscriber = ForeignKey(
        SubscriberEditionDownloads, on_delete=CASCADE, related_name='subscriber_downloads', verbose_name='suscriptor'
    )
    incomplete = BooleanField(default=True)
    download_date = DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'download_date'
        unique_together = ('subscriber', 'download_date')
        verbose_name = 'descarga de edición'
        verbose_name_plural = 'descargas de edición'


class Subscription(Model):
    SUBSCRIPTION_CHOICES = (
        ('PAP', 'Edición papel + Digital'),
        ('DIG', 'Digital (Edición web)'),
    )
    MONTHLY = 'MO'
    QUARTERLY = 'Q'
    BIANNUAL = 'BA'
    ANNUAL = 'AN'
    SUBSCRIPTION_PLAN_CHOICES = (
        (MONTHLY, 'Mensual'),
        (QUARTERLY, 'Trimestral'),
        (BIANNUAL, 'Semestral'),
        (ANNUAL, 'Anual'),
    )

    subscriber = ForeignKey(
        User, on_delete=CASCADE, related_name='suscripciones', verbose_name='usuario', null=True, blank=True
    )
    first_name = CharField('nombres', max_length=150)
    last_name = CharField('apellidos', max_length=150)
    document = CharField('documento', max_length=11, blank=False, null=True)
    telephone = CharField('teléfono', max_length=20, blank=False, null=False)
    email = EmailField('email')
    address = CharField('dirección', max_length=255, blank=True, null=True)
    country = CharField('país', max_length=50)
    city = CharField('ciudad', max_length=64, blank=True, null=True)
    province = CharField(
        'departamento', max_length=20, choices=settings.THEDAILY_PROVINCE_CHOICES, blank=True, null=True
    )

    observations = TextField('observaciones para la entrega', blank=True, null=True)
    subscription_type = CharField('suscripción', max_length=3, choices=SUBSCRIPTION_CHOICES, default='DIG')
    subscription_plan = CharField('plan', max_length=2, choices=SUBSCRIPTION_PLAN_CHOICES)
    subscription_end = DateTimeField('última fecha de suscripción', auto_now_add=True, editable=False)
    friend1_name = CharField('nombre', max_length=150, blank=True, null=True)
    friend1_email = CharField('email', max_length=150, blank=True, null=True)
    friend1_telephone = CharField('teléfono', max_length=20, blank=True, null=True)
    friend2_name = CharField('nombre', max_length=150, blank=True, null=True)
    friend2_email = CharField('email', max_length=150, blank=True, null=True)
    friend2_telephone = CharField('teléfono', max_length=20, blank=True, null=True)
    friend3_name = CharField('nombre', max_length=150, blank=True, null=True)
    friend3_email = CharField('email', max_length=150, blank=True, null=True)
    friend3_telephone = CharField('teléfono', max_length=20, blank=True, null=True)
    date_created = DateTimeField('fecha de creación', auto_now_add=True, editable=False)

    public_profile = BooleanField('perfíl comunidad', default=True)

    subscription_type_prices = ManyToManyField(SubscriptionPrices, verbose_name='tipo de subscripcion', blank=True)
    promo_code = CharField(max_length=8, blank=True, null=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        if not self.first_name and not self.last_name:
            return "Usuario sin nombre"
        else:
            return '%s %s' % (self.first_name, self.last_name)

    def get_subscription_type_prices(self):
        return ', '.join('%s' % stp for stp in self.subscription_type_prices.all())

    def get_absolute_url(self):
        return '/admin/thedaily/subscription/%i/' % self.id

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('-date_created', 'first_name', 'last_name')
        verbose_name = 'suscripción'
        verbose_name_plural = 'suscripciones'


# This model can be used if unique promo codes required:
# class PromoCode(Model):
#    code = CharField(max_length=8, unique=True)
#    subscription = ForeignKey(Subscription, unique=True, blank=True, null=True)


class ExteriorSubscriptionManager(Manager):
    def get_queryset(self):
        return (
            super(ExteriorSubscriptionManager, self)
            .get_queryset()
            .filter(subscriber__in=Group.objects.get(name='exterior_subscribers').user_set.all())
        )


class ExteriorSubscription(Subscription):
    objects = ExteriorSubscriptionManager()

    class Meta:
        proxy = True


class PollAnswer(Model):
    """
    General purpose document-answer for polls
    """
    document = CharField('documento', max_length=50, unique=True)
    answer = CharField('respuesta', max_length=16)


class UsersApiSession(Model):
    """
    This model is used to register the logins from the users API, when a
    request comes to the API an optional device ID can be sent, we can use this
    value to allow only a certain number of requests per-user with a different
    user device id (udid), for ex. 3. No clean-session policy is defined yet.
    """
    user = ForeignKey(User, on_delete=CASCADE, related_name='api_sessions', verbose_name='usuario')
    udid = CharField(max_length=16)


class RemainingContent(Model):
    """
    Stores the content to be rendered in signupwall HTML components depending on the user's remaining "credits"
    """
    remaining_articles = PositiveSmallIntegerField(unique=True)
    template_content = TextField(null=True, blank=True)

    class Meta:
        verbose_name = "remaining content"
        verbose_name_plural = "remaining contents"

    def __str__(self):
        return "content for %d credits remaining" % self.remaining_articles


class MailtrainList(Model):
    """
    Exposes a Mailtrain (https://github.com/Mailtrain-org/mailtrain) list as a Newsletter, then users can subscribe or
    unsubscribe to the list in their utopia-cms profiles, generating ajax requests to utopia-crm who acts as gateway
    between the Mailtrain's API to perform the action needed. The delivering of this newsletters is exclusively
    responsability of the Mailtrain deployment associated to utopia-crm, not ours.
    WARN: You shouldn't mark "on_signup" without inform to the new user that you will do this.
    """
    list_cid = CharField(max_length=16, unique=True)
    newsletter_name = CharField(max_length=64)
    newsletter_tagline = CharField(max_length=128, blank=True, null=True)
    newsletter_periodicity = CharField(max_length=64, blank=True, null=True)
    on_signup = BooleanField('Activada para nuevas cuentas', default=False)  # TODO: implement when True
    newsletter_new_pill = BooleanField('pill de "nuevo" para la newsletter en el perfil de usuario', default=False)

    def __str__(self):
        return self.newsletter_name
