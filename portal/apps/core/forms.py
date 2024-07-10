# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import traceback
from pydoc import locate
from email.utils import make_msgid
from emails.django import DjangoMessage as Message
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field
from crispy_forms.bootstrap import FormActions

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.forms import Form, CharField, HiddenInput, ValidationError, EmailField, Textarea
from django.utils.crypto import salted_hmac

from libs.utils import smtp_connect


class ArticleFeedbackForm(Form):
    article_token = CharField(widget=HiddenInput)  # prevents cross-entity posting
    message = CharField(label='Mensaje', widget=Textarea())

    def __init__(self, *args, **kwargs):
        article = kwargs.pop('article', None)
        if not article:
            raise ValidationError('Missing article')
        initial = {"article_token": self.gen_article_token(article)}
        if 'initial' in kwargs:
            kwargs['initial'].update(initial)
        else:
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def gen_article_token(self, article):
        return salted_hmac(settings.SECRET_KEY, f"{article.id}:{article.slug}").hexdigest()

    def is_valid(self, article):
        result = super().is_valid() and self.cleaned_data.get("article_token") == self.gen_article_token(article)
        if not result:
            self.add_error(None, ValidationError("los datos enviados no son correctos"))
        return result


def send_feedback(request, article):
    body = """
    Mensaje enviado desde el artículo "%(article)s":

    %(message)s

    URL del artículo: %(url)s
    """ % {
        'article': article.headline,
        'message': request.POST.get('message'),
        'url': settings.SITE_URL_SD + article.get_absolute_url(),
    }
    if request.user.is_authenticated:
        body += "\nUsuario: %s (ID %d)" % (request.user.email, request.user.id)

    prefix = "feedback_"
    re_prefix = re.compile(r"^%s" % prefix)
    if any(k.startswith(prefix) for k in request.POST.keys()):
        body += (
            "\n"
            + "\n".join(f"{re.sub(re_prefix, '', k)}: {v}" for k, v in request.POST.items() if k.startswith(prefix))
        )

    to_name_addr = getattr(
        settings,
        "CORE_ARTICLE_DETAIL_FEEDBACK_MAILTO",
        (settings.NOTIFICATIONS_TO_NAME, settings.NOTIFICATIONS_TO_ADDR),
    )
    message = Message(
        text=body,
        mail_to=to_name_addr,
        mail_from=getattr(settings, "CORE_ARTICLE_DETAIL_FEEDBACK_MAILFROM", settings.NOTIFICATIONS_FROM_ADDR1),
        subject='Feedback en artículo',
        headers={'Message-Id': make_msgid("feedbak." + str(article.id)), "Return-Path": settings.NOTIFICATIONS_FROM_MX}
    )
    smtp = smtp_connect()
    try:
        smtp.sendmail(settings.NOTIFICATIONS_FROM_MX, [to_name_addr[1]], message.as_string())
        if settings.DEBUG:
            print('DEBUG: an email was sent from send_confirmation_link function')
        smtp.quit()
    except Exception:
        if settings.DEBUG:
            print(traceback.format_exc())
        raise ValidationError('Error al enviar el mensaje')

    return HttpResponseRedirect(reverse('article_report_sent'))


feedback_module_path = getattr(settings, "CORE_ARTICLE_DETAIL_FEEDBACK_MODULE", None)
feedback_module = locate(feedback_module_path) if feedback_module_path else feedback_module_path


def feedback_allowed(request, article):
    if feedback_module is False:
        return False
    custom_allowed = getattr(feedback_module, "custom_feedback_allowed", None)
    if custom_allowed:
        return custom_allowed(request, article)
    else:
        return article.is_published and request.user.is_authenticated


def feedback_form(data=None, article=None, request=None):
    custom_form = getattr(feedback_module, "custom_feedback_form", None)
    return custom_form(data, article, request) if custom_form else ArticleFeedbackForm(data, article=article)


def feedback_view(request, article):
    custom_view = getattr(feedback_module, "custom_feedback_view", None)
    return custom_view(request, article) if custom_view else send_feedback(request, article)


class SendByEmailForm(Form):
    email = EmailField(label='Dirección email')
    message = CharField(label='Texto de mensaje (opcional)', required=False, widget=Textarea(attrs={'rows': 2}))

    article_id = CharField(widget=HiddenInput)

    # TODO: init method here
    helper = FormHelper()
    helper.form_id = 'send_by_email'
    helper.form_method = 'post'
    helper.form_action = reverse_lazy('send_by_email')
    helper.help_text_inline = True
    helper.error_text_inline = True
    helper.render_unmentioned_fields = False
    helper.form_error_title = 'Errores del formulario'
    helper.layout = Layout(
        'email',
        Field('message', rows="3", css_class='input-xlarge'),
        'article_id',
        FormActions(Submit('save', u'Enviar')),
    )
