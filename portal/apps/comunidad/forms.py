# -*- coding: utf-8 -*-
from django import forms

from comunidad.models import SubscriberEvento, SubscriberArticle, Registro
from thedaily.models import Subscriber

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Button, Field, Fieldset, HTML, MultiField
from crispy_forms.bootstrap import FormActions

class ArticleForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'articulo'
        # self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        # self.helper.form_action = reverse( 'community-article' )
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.render_unmentioned_fields = False
        self.helper.layout = Layout(
            Field('sections'),
            Field('headline'),
            Field('deck'),
            Field('body'),
            FormActions(
                Submit('save', u'Publicar'),
            )
        )

        super(ArticleForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SubscriberArticle
        fields = ['headline' , 'deck', 'body']

class EventoForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'evento'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_style = 'inline'
        self.helper.form_method = 'post'
        # self.helper.form_action = reverse( 'community-event' )
        self.helper.help_text_inline = True
        self.helper.error_text_inline = True
        self.helper.render_unmentioned_fields = True
        self.helper.layout = Layout(
            Field('categoria'),
            Field('title'),
            Field('description'),
            Field('start', css_class="datepicker", readonly=True),
            Field('end', css_class="datepicker", readonly=True),
            Field('precio'),
            Field('poster'),
            FormActions(
                Submit('save', u'Publicar'),
            )
        )

        super(EventoForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SubscriberEvento
        fields = ['categoria' , 
                    'title', 
                    'description', 
                    'start', 
                    'end', 
                    'precio', 
                    'poster']


class RegistroForm(forms.ModelForm):
    """ Registro de la utilizacion de un beneficio """
    document = forms.CharField(max_length=50, required=False,
        label='Documento', help_text=u'Número de cédula sin puntos ni guiones '
        'u otro documento registrado en la diaria.')

    def __init__(self, benefit_qs, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('document'), Field('benefit'),
            FormActions(Submit('', u'Consultar')))
        super(RegistroForm, self).__init__(*args, **kwargs)
        self.fields['benefit'].queryset = benefit_qs
        self.fields['benefit'].label = 'Beneficio'

    def clean(self):
        cleaned_data = super(RegistroForm, self).clean()
        # first check for the benefit's limit left
        benefit, cupo_restante = cleaned_data.get("benefit"), None
        if benefit:
            if benefit.limit:
                cupo_restante = benefit.limit - len(benefit.registro_set.all())
                if cupo_restante <= 0:
                    raise forms.ValidationError("No hay cupo")
        # second: identify the subscriber and check the per subscriber quota
        document = cleaned_data.get("document")
        if document:
            try:
                subscriber = Subscriber.objects.get(document=document)
                if not subscriber.is_subscriber():
                    raise forms.ValidationError("No es suscriptor activo")
                else:
                    cleaned_data['subscriber'] = subscriber
                if benefit and benefit.quota and benefit.quota - len(
                        subscriber.registro_set.filter(benefit=benefit)) <= 0:
                    raise forms.ValidationError("Ya utilizó el beneficio")
            except Subscriber.DoesNotExist:
                raise forms.ValidationError("Documento no encontrado")
            except Subscriber.MultipleObjectsReturned:
                raise forms.ValidationError("Muchos suscriptores encontrados")
        elif benefit:
            raise forms.ValidationError("Cupo restante: %s" % (cupo_restante \
                if benefit.limit else 'ilimitado'))
        return cleaned_data

    class Meta:
        model = Registro
        fields = ['document', 'benefit']