# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field
from crispy_forms.bootstrap import FormActions

from django.urls import reverse_lazy
from django.forms import Form, CharField, HiddenInput, ValidationError, EmailField, Textarea

from libs.utils import do_gonzo


def gen_gonzo(form, aslug='', aid=''):
    if not aslug:
        aslug = form.article.slug
    if not aid:
        aid = form.article.id
    return do_gonzo(aslug, aid)


class ArticleForm(Form):
    # TODO: check if this class is needed
    article = CharField(widget=HiddenInput)
    gonzo = CharField(widget=HiddenInput)

    def __init__(self, *args, **kwargs):
        initial = {}
        if 'article' in kwargs:
            self.article = kwargs.get('article')
            initial['article'] = self.article.slug
            del kwargs['article']
        else:
            raise ValidationError('Missing article')
        initial['gonzo'] = gen_gonzo(self)
        if 'initial' in kwargs:
            kwargs['initial'].update(initial)
        else:
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data
        gonzo = data.get('gonzo', '')
        if gonzo != gen_gonzo(self, data.get('article', ''), self.article.id):
            raise ValidationError('Ha ocurrido un error interno.')
        return data


class ReportErrorArticleForm(ArticleForm):
    error = CharField(label='Reportá un error')


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
