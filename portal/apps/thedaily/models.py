# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import re
import json
import requests
import pymongo
from hashids import Hashids

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.validators import RegexValidator
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
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
    permalink,
    ImageField,
    PositiveSmallIntegerField,
    DecimalField,
    Manager,
    ManyToManyField,
)
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver

from apps import mongo_db
from core.models import Edition, Publication, Category, ArticleViewedBy
from .exceptions import UpdateCrmEx


GA_CATEGORY_CHOICES = (('D', 'Digital'), ('P', 'Papel'))


class SubscriptionPrices(Model):
    subscription_type = CharField(
        u'tipo', max_length=7, choices=settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES, unique=True, default='PAPYDIM'
    )
    price = DecimalField(u'Precio', max_digits=7, decimal_places=2)
    order = PositiveSmallIntegerField(u'Orden', null=True)
    paypal_button_id = CharField(max_length=13, null=True, blank=True)
    auth_group = ForeignKey(Group, verbose_name=u'Grupo asociado al permiso', blank=True, null=True)
    publication = ForeignKey(Publication, blank=True, null=True)
    ga_sku = CharField(max_length=10, blank=True, null=True)
    ga_name = CharField(max_length=64, blank=True, null=True)
    ga_category = CharField(max_length=1, choices=GA_CATEGORY_CHOICES, blank=True, null=True)

    def __str__(self):
        return u"%s -- $ %s " % (self.get_subscription_type_display(), self.price)

    class Meta:
        verbose_name = u'Precio'
        verbose_name_plural = u'Precios'
        ordering = ['order']


alphanumeric = RegexValidator(
    u'^[A-Za-z0-9ñüáéíóúÑÜÁÉÍÓÚ _\'.\-]*$',
    u'El nombre sólo admite caracteres alfanuméricos, apóstrofes, espacios, guiones y puntos.'
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
    contact_id = PositiveIntegerField(u'CRM id', unique=True, editable=True, blank=True, null=True)
    user = OneToOneField(User, verbose_name=u'usuario', related_name='subscriber', blank=True, null=True)

    # TODO: ver la posibilidad de eliminarlo ya que es el "first_name" del modelo django.contrib.auth.models.User
    name = CharField(u'nombre', max_length=255, validators=[alphanumeric])

    # agregamos estos campos para unificar la info de User y Subscriber
    address = CharField(u'dirección', max_length=255, blank=True, null=True)
    country = CharField(u'país', max_length=50, blank=True, null=True)
    city = CharField(u'ciudad', max_length=64, blank=True, null=True)
    province = CharField(
        u'departamento', max_length=20, choices=settings.THEDAILY_PROVINCE_CHOICES, blank=True, null=True
    )

    profile_photo = ImageField(upload_to='perfiles', blank=True, null=True)
    document = CharField(u'documento', max_length=50, blank=True, null=True)
    phone = CharField(u'teléfono', max_length=20)

    date_created = DateTimeField(u'fecha de registro', auto_now_add=True, editable=False)
    downloads = PositiveIntegerField(u'descargas', default=0, blank=True, null=True)

    pdf = BooleanField(default=False)
    lento_pdf = BooleanField(u'pdf L.', default=False)
    ruta = PositiveSmallIntegerField(blank=True, null=True)
    plan_id = TextField(blank=True, null=True)
    ruta_lento = PositiveSmallIntegerField(blank=True, null=True)
    ruta_fs = PositiveSmallIntegerField(blank=True, null=True)
    newsletters = ManyToManyField(Publication, blank=True, limit_choices_to={'has_newsletter': True})
    category_newsletters = ManyToManyField(Category, blank=True, limit_choices_to={'has_newsletter': True})
    allow_news = BooleanField(u'acepta novedades', default=True)
    allow_promotions = BooleanField(u'acepta promociones', default=True)
    allow_polls = BooleanField(u'acepta encuestas', default=True)
    # TODO: explain the utility of this field or remove it.
    subscription_mode = CharField(max_length=1, null=True, blank=True, default=None)
    last_paid_subscription = DateTimeField(u'Ultima subscripcion comienzo', null=True, blank=True)

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

    def is_subscriber(self, pub_slug=settings.DEFAULT_PUB):
        try:

            if self.user:

                if self.user.is_staff:
                    return True

                elif pub_slug in getattr(settings, 'THEDAILY_IS_SUBSCRIBER_CUSTOM_PUBLICATIONS', ()):
                    is_subscriber_custom = __import__(
                        settings.THEDAILY_IS_SUBSCRIBER_CUSTOM_MODULE, fromlist=['is_subscriber']
                    ).is_subscriber
                    return is_subscriber_custom(self, pub_slug)

                else:
                    return self.user.has_perm('thedaily.es_suscriptor_%s' % pub_slug)

        except User.DoesNotExist:
            # rare, but we saw once this exception happen
            pass

        return False

    def is_digital_only(self):
        """ Returns True only if this subcriber is subscribed only to the "digital" edition """
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
    user_is_active.short_description = u'user act.'
    user_is_active.boolean = True

    def is_subscriber_any(self):
        return any(
            self.is_subscriber(pub_slug) for pub_slug in getattr(
                settings, 'THEDAILY_IS_SUBSCRIBER_ANY', Publication.objects.values_list('slug', flat=True)))

    def get_publication_newsletters_ids(self, exclude_slugs=[]):
        return list(
            self.newsletters.filter(
                has_newsletter=True
            ).exclude(slug__in=exclude_slugs).values_list('id', flat=True)
        )

    def get_category_newsletters_ids(self, exclude_slugs=[]):
        return list(
            self.category_newsletters.filter(
                has_newsletter=True
            ).exclude(slug__in=exclude_slugs).values_list('id', flat=True)
        )

    def get_newsletters_slugs(self):
        return list(self.newsletters.values_list('slug', flat=True)) + \
            list(self.category_newsletters.values_list('slug', flat=True))

    def get_newsletters(self):
        return ', '.join(self.get_newsletters_slugs())
    get_newsletters.short_description = u'newsletters'

    def updatecrmuser_publication_newsletters(self, exclude_slugs=[]):
        if self.contact_id:
            try:
                updatecrmuser(
                    self.contact_id, u'newsletters', json.dumps(self.get_publication_newsletters_ids(exclude_slugs))
                )
            except requests.exceptions.RequestException:
                pass

    def updatecrmuser_category_newsletters(self, exclude_slugs=[]):
        if self.contact_id:
            try:
                updatecrmuser(
                    self.contact_id, u'area_newsletters', json.dumps(self.get_category_newsletters_ids(exclude_slugs))
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
            return u"Usuario sin nombre"
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

    @permalink
    def get_absolute_url(self):
        return '/admin/thedaily/subscriber/%i/' % self.id

    def hashed_id(self):
        return Hashids(settings.HASHIDS_SALT, 32).encode(int(self.id))

    class Meta:
        verbose_name = u'suscriptor'
        permissions = (("es_suscriptor_%s" % settings.DEFAULT_PUB, "Es suscriptor actualmente"), )


def updatecrmuser(contact_id, field, value):
    data = {"contact_id": contact_id, "field": field, "value": value}
    if settings.CRM_UPDATE_USER_ENABLED:
        r = requests.post(settings.CRM_UPDATE_USER_URI, data=data)
        r.raise_for_status()


@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):

    if not settings.CRM_UPDATE_USER_ENABLED or getattr(instance, "updatefromcrm", False):
        return True
    try:
        actualusr = sender.objects.get(pk=instance.id)
    except User.DoesNotExist:
        actualusr = instance

    # sync email if changed
    if actualusr.email != instance.email:
        try:
            contact_id = instance.subscriber.contact_id if instance.subscriber else None
            requests.post(
                settings.CRM_UPDATE_USER_URI, data={
                    'contact_id': contact_id, 'email': actualusr.email,
                    'newemail': instance.email}).raise_for_status()
        except requests.exceptions.RequestException:
            raise UpdateCrmEx(u"No se ha podido actualizar tu email, contactate con nosotros")


@receiver(pre_save, sender=Subscriber, dispatch_uid="subscriber_pre_save")
def subscriber_pre_save(sender, instance, **kwargs):
    if getattr(settings, 'THEDAILY_DEBUG_SIGNALS', False):
        print('DEBUG: subscriber_pre_save signal called')
    if not settings.CRM_UPDATE_USER_ENABLED or getattr(instance, "updatefromcrm", False):
        return True
    try:
        actual_sub = sender.objects.get(pk=instance.id)
        for f in list(settings.CRM_UPDATE_SUBSCRIBER_FIELDS.values()):
            if getattr(actual_sub, f) != getattr(instance, f):
                try:
                    updatecrmuser(instance.contact_id, f, getattr(instance, f))
                except requests.exceptions.RequestException:
                    raise UpdateCrmEx(u"No se ha podido actualizar tu perfil, contactate con nosotros")
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
    if (getattr(instance, "updatefromcrm", False)):
        return True
    if instance.contact_id and action.startswith('post_'):
        # post_add with empty pk_set means "unchanged", do not sync in such scenario
        if action != 'post_add' or pk_set:
            try:
                updatecrmuser(
                    instance.contact_id,
                    (u'area_' if model is Category else u'') + u'newsletters'
                    + (u'_remove' if action == 'post_remove' else u''),
                    json.dumps(list(pk_set)) if pk_set else None,
                )
            except requests.exceptions.RequestException:
                # TODO: write to error log, then this errors can be monitored someway
                pass


@receiver(post_save, sender=User, dispatch_uid="createUserProfile")
def createUserProfile(sender, instance, **kwargs):
    """
    Create a UserProfile object each time a User is created ; and link it.
    """
    Subscriber.objects.get_or_create(user=instance)


class OAuthState(Model):
    """
    Store partial social_auth OAuth state associated to the user being created
    to ask then for extra fields, such as the telephone number.
    @see libs.social_auth_pipeline
    """
    user = OneToOneField(User)
    state = CharField(max_length=32, unique=True)
    fullname = CharField(max_length=255, blank=True, null=True)


class WebSubscriber(Subscriber):
    referrer = ForeignKey(Subscriber, related_name='referred', verbose_name=u'referido', blank=True, null=True)


class SubscriberEditionDownloads(Model):
    subscriber = ForeignKey(Subscriber, related_name='edition_downloads', verbose_name=u'suscriptor')
    edition = ForeignKey(Edition, related_name='subscribers_downloads', verbose_name=u'edición')
    downloads = PositiveIntegerField(u'descargas', default=0)

    def __str__(self):
        return u'%s - %s: %i' % (self.subscriber, self.edition, self.downloads)

    def save(self, *args, **kwargs):
        super(SubscriberEditionDownloads, self).save(*args, **kwargs)
        download = EditionDownload(subscriber=self)
        download.save()

    class Meta:
        ordering = ('-edition', '-downloads', 'subscriber')
        unique_together = ('subscriber', 'edition')
        verbose_name = u'descargas de edición'
        verbose_name_plural = u'descargas de ediciones'


class SentMail(Model):
    subscriber = ForeignKey(Subscriber)
    subject = CharField(u'asunto', max_length=150)
    date_sent = DateTimeField(u'fecha de envio', auto_now_add=True, editable=False)


class SubscriberEvent(Model):
    subscriber = ForeignKey(Subscriber)
    description = CharField(u'descripcion', max_length=150)
    date_occurred = DateTimeField(auto_now_add=True, editable=False)


class EditionDownload(Model):
    subscriber = ForeignKey(
        SubscriberEditionDownloads, related_name='subscriber_downloads', verbose_name=u'suscriptor'
    )
    incomplete = BooleanField(default=True)
    download_date = DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'download_date'
        unique_together = ('subscriber', 'download_date')
        verbose_name = u'descarga de edición'
        verbose_name_plural = u'descargas de edición'


class Subscription(Model):
    SUBSCRIPTION_CHOICES = (
        ('PAP', u'Edición papel + Digital'),
        ('DIG', u'Digital (Edición web)'),
    )
    MONTHLY = u'MO'
    QUARTERLY = u'QU'
    BIANNUAL = u'BA'
    ANNUAL = u'AN'
    SUBSCRIPTION_PLAN_CHOICES = (
        (MONTHLY, u'Mensual'),
        (QUARTERLY, u'Trimestral'),
        (BIANNUAL, u'Semestral'),
        (ANNUAL, u'Anual'),
    )

    subscriber = ForeignKey(User, related_name='suscripciones', verbose_name=u'usuario', null=True, blank=True)
    first_name = CharField(u'nombres', max_length=150)
    last_name = CharField(u'apellidos', max_length=150)
    document = CharField(u'documento', max_length=11, blank=False, null=True)
    telephone = CharField(u'teléfono', max_length=20, blank=False, null=False)
    email = EmailField(u'email')
    address = CharField(u'dirección', max_length=255, blank=True, null=True)
    country = CharField(u'país', max_length=50)
    city = CharField(u'ciudad', max_length=64, blank=True, null=True)
    province = CharField(
        u'departamento', max_length=20, choices=settings.THEDAILY_PROVINCE_CHOICES, blank=True, null=True
    )

    observations = TextField(u'observaciones para la entrega', blank=True, null=True)
    subscription_type = CharField(u'suscripción', max_length=3, choices=SUBSCRIPTION_CHOICES, default='DIG')
    subscription_plan = CharField(u'plan', max_length=2, choices=SUBSCRIPTION_PLAN_CHOICES)
    subscription_end = DateTimeField(u'última fecha de suscripción', auto_now_add=True, editable=False)
    friend1_name = CharField(u'nombre', max_length=150, blank=True, null=True)
    friend1_email = CharField(u'email', max_length=150, blank=True, null=True)
    friend1_telephone = CharField(u'teléfono', max_length=20, blank=True, null=True)
    friend2_name = CharField(u'nombre', max_length=150, blank=True, null=True)
    friend2_email = CharField(u'email', max_length=150, blank=True, null=True)
    friend2_telephone = CharField(u'teléfono', max_length=20, blank=True, null=True)
    friend3_name = CharField(u'nombre', max_length=150, blank=True, null=True)
    friend3_email = CharField(u'email', max_length=150, blank=True, null=True)
    friend3_telephone = CharField(u'teléfono', max_length=20, blank=True, null=True)
    date_created = DateTimeField(u'fecha de creación', auto_now_add=True, editable=False)

    public_profile = BooleanField(u'perfíl comunidad', default=True)

    subscription_type_prices = ManyToManyField(SubscriptionPrices, verbose_name=u'tipo de subscripcion', blank=True)
    promo_code = CharField(max_length=8, blank=True, null=True)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        if not self.first_name and not self.last_name:
            return "Usuario sin nombre"
        else:
            return u'%s %s' % (self.first_name, self.last_name)

    def get_subscription_type_prices(self):
        return u', '.join(u'%s' % stp for stp in self.subscription_type_prices.all())

    def get_absolute_url(self):
        return '/admin/thedaily/subscription/%i/' % self.id

    class Meta:
        get_latest_by = 'date_created'
        ordering = ('-date_created', 'first_name', 'last_name')
        verbose_name = u'suscripción'
        verbose_name_plural = u'suscripciones'


# This model can be used if unique promo codes required:
# class PromoCode(Model):
#    code = CharField(max_length=8, unique=True)
#    subscription = ForeignKey(Subscription, unique=True, blank=True, null=True)


class ExteriorSubscriptionManager(Manager):
    def get_queryset(self):
        return super(
            ExteriorSubscriptionManager, self).get_queryset().filter(
                subscriber__in=Group.objects.get(name='exterior_subscribers').user_set.all())


class ExteriorSubscription(Subscription):
    objects = ExteriorSubscriptionManager()

    class Meta:
        proxy = True


class PollAnswer(Model):
    """ General purpose document-answer for polls """
    document = CharField(u'documento', max_length=50, unique=True)
    answer = CharField(u'respuesta', max_length=16)


class UsersApiSession(Model):
    """
    This model is used to register the logins from the users API, when a
    request comes to the API an optional device ID can be sent, we can use this
    value to allow only a certain number of requests per-user with a different
    user device id (udid), for ex. 3. No clean-session policy is defined yet.
    """
    user = ForeignKey(User, related_name='api_sessions', verbose_name=u'usuario')
    udid = CharField(max_length=16)
