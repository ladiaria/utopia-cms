from datetime import timedelta
import qrcode
import base64
from io import BytesIO
from hashids import Hashids
from updown.fields import RatingField

from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models.fields import DateTimeField
from django.db.models.fields.related import ForeignKey
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from cartelera.models import EventoBase
from core.models import Article, ArticleBase
from thedaily.models import Subscriber


class SubscriberArticle(ArticleBase):
    rating = RatingField(can_change_vote=True)
    is_suscriber_article = True

    @staticmethod
    def top_articles():
        desde = timezone.now() - timedelta(days=15)
        return SubscriberArticle.objects.get_queryset().filter(date_published__gt=desde)[:3]

    def __str__(self):
        return self.headline + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        self.type = settings.CORE_COMUNIDAD_ARTICLE
        if not self.slug:
            self.slug = slugify(self.headline)
        super(SubscriberArticle, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('comunidad_article_detail', kwargs={'slug': self.slug})


class SubscriberEvento(EventoBase):
    date_created = DateTimeField('fecha de creación', auto_now_add=True)
    created_by = ForeignKey(
        User,
        verbose_name='creado por',
        related_name='eventos_creados',
        editable=False,
        blank=False,
        null=True,
        on_delete=models.CASCADE,
    )

    is_suscriber_evento = True

    def __str__(self):
        return self.title + ' ( por ' + str(self.created_by) + ' )'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(SubscriberEvento, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('comunidad_evento_detail', kwargs={'slug': self.slug})


class TopUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField()
    date_created = DateTimeField('fecha de calculo', auto_now_add=True)
    type = models.CharField(max_length=20, choices=[('WEEK', 'WEEK'), ('MONTH', 'MONTH'), ('YEAR', 'YEAR')])


class Circuito(models.Model):
    name = models.CharField('nombre', max_length=64)
    description = models.TextField('descripcion', null=True, blank=True)
    general_quota = models.PositiveIntegerField('cupo general por suscriptor', null=True, blank=True)

    def __str__(self):
        return self.name


class Socio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='usuario', related_name='socio')
    circuits = models.ManyToManyField(Circuito, verbose_name='circuitos')

    def __str__(self):
        return self.user.username


class Beneficio(models.Model):
    name = models.CharField('nombre', max_length=255)
    circuit = models.ForeignKey(Circuito, on_delete=models.CASCADE, verbose_name='circuito', related_name='beneficios')
    limit = models.PositiveIntegerField('cupo general', null=True, blank=True)
    quota = models.PositiveIntegerField('cupo por suscriptor', default=1)
    slug = models.SlugField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'circuit')

    def get_available_quota(self, subscriber):
        subscriber_benefit_count = Registro.objects.filter(subscriber=subscriber, benefit=self).count()
        benefit_remaining = max(0, self.quota - subscriber_benefit_count)

        if self.circuit.general_quota is not None:
            subscriber_circuit_count = Registro.objects.filter(
                subscriber=subscriber, benefit__circuit=self.circuit
            ).count()
            circuit_remaining = max(0, self.circuit.general_quota - subscriber_circuit_count)
            benefit_remaining = min(benefit_remaining, circuit_remaining)

        if self.limit is not None:
            total_benefit_count = Registro.objects.filter(benefit=self).count()
            limit_remaining = max(0, self.limit - total_benefit_count)
            benefit_remaining = min(benefit_remaining, limit_remaining)

        return benefit_remaining

    @transaction.atomic
    def create_registros(self, subscriber, quantity=1):
        available_quota = self.get_available_quota(subscriber)

        if quantity > available_quota:
            raise ValidationError(f"Requested quantity ({quantity}) exceeds available quota ({available_quota}).")

        registros = []
        for _variable in range(quantity):
            registro = Registro(subscriber=subscriber, benefit=self)
            registros.append(registro)

        for registro in registros:
            registro.save()
        return registros

    def get_remaining_tickets(self):
        exchanged_tickets = Registro.objects.filter(benefit=self).count()
        return self.limit - exchanged_tickets


class Registro(models.Model):
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, verbose_name='suscriptor')
    benefit = models.ForeignKey(Beneficio, on_delete=models.CASCADE, verbose_name='beneficio')
    issued = models.DateTimeField(auto_now_add=True, verbose_name='creado')
    used = models.DateTimeField(null=True, blank=True, verbose_name='utilizado')

    class Meta:
        permissions = [
            ('verify_registro', 'Can verify registro'),
        ]

    def subscriber_email(self):
        return self.subscriber.user.email

    def clean(self):
        # Skip checks if we're just marking the registro as used
        if not self.used:
            # Check subscriber quota for this specific benefit
            subscriber_benefit_registros = Registro.objects.filter(
                subscriber=self.subscriber, benefit=self.benefit
            ).count()
            if subscriber_benefit_registros >= self.benefit.quota:
                raise ValidationError(f"Subscriber has reached the quota for this benefit ({self.benefit.quota}).")

            # Check subscriber's general quota for the circuit
            subscriber_circuit_registros = Registro.objects.filter(
                subscriber=self.subscriber, benefit__circuit=self.benefit.circuit
            ).count()
            if (
                self.benefit.circuit.general_quota is not None
                and subscriber_circuit_registros >= self.benefit.circuit.general_quota
            ):
                raise ValidationError(
                    f"Subscriber has reached the general quota for this circuit ({self.benefit.circuit.general_quota})."
                )

            # Check benefit's overall limit
            if self.benefit.limit is not None:
                total_benefit_registros = Registro.objects.filter(benefit=self.benefit).count()
                if total_benefit_registros >= self.benefit.limit:
                    raise ValidationError(f"The benefit has reached its overall limit ({self.benefit.limit}).")

    def use_registro(self):
        self.used = timezone.now()
        self.save(skip_clean=True)

    def save(self, *args, **kwargs):
        skip_clean = kwargs.pop('skip_clean', False)
        if not skip_clean:
            self.clean()
        super().save(*args, **kwargs)

    def generate_hashed_id(self):
        hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)
        return hashids.encode(self.id)

    def get_qr_url(self):
        hashed_id = self.generate_hashed_id()
        relative_url = reverse('verify_registro', kwargs={'hashed_id': hashed_id})
        domain = Site.objects.get_current().domain
        protocol = 'https://'
        return f"{protocol}{domain}{relative_url}"

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.get_qr_url())
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def qr_code_image(self, size=50):
        qr_image = self.generate_qr_code()
        qr_base64 = base64.b64encode(qr_image).decode('utf-8')
        return mark_safe(
            f'<img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width:{size}px; height:{size}px;">'
        )

    qr_code_image.short_description = 'QR Code'

    def __str__(self):
        return f"{self.subscriber.user.username} - {self.benefit.name}"


class Url(models.Model):
    url = models.URLField(unique=True)

    def __str__(self):
        return self.url


class Recommendation(models.Model):
    """
    Primary useful for a chrome extension
    """

    name = models.CharField('nombre', max_length=128, unique=True)
    urls = models.ManyToManyField(Url)
    comment = models.TextField('comentario')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=True, blank=True)

    def url_list(self):
        return mark_safe('<br>'.join(self.urls.values_list('url', flat=True)))
