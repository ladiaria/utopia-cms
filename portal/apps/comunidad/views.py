# -*- coding: utf-8 -*-
from hashids import Hashids
from crispy_forms.layout import Layout, Submit, HTML
from crispy_forms.bootstrap import FormActions

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.forms import HiddenInput
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, RedirectView, FormView
from django.views.decorators.http import require_POST

from libs.utils import decode_hashid
from decorators import render_response

from .models import SubscriberEvento, SubscriberArticle, TopUser, Beneficio, Socio, Registro
from .forms import ArticleForm, EventoForm, RegistroForm, ScanQRForm


to_response = render_response('comunidad/templates/')


@never_cache
@staff_member_required
def index(request):
    # TODO: subscriber articles and events features should be reviewed
    # articulos = SubscriberArticle.objects.all()[:20]
    # eventos = SubscriberEvento.objects.all()[:20]

    top_users_week = TopUser.objects.filter(type='WEEK').order_by('-date_created', '-points').select_related('user')
    top_users_month = TopUser.objects.filter(type='MONTH').order_by('-date_created', '-points').select_related('user')

    return render(
        request,
        'comunidad/index.html',
        {
            # 'articulos': articulos,
            # 'eventos': eventos,
            'top_users_week': top_users_week,
            'top_users_month': top_users_month,
        },
    )


@never_cache
def article_detail(request, slug):
    article = get_object_or_404(SubscriberArticle, slug=slug)
    return render(request, 'article/detail.html', {'article': article, 'is_comunidad': True, 'is_detail': True})


@never_cache
@permission_required('add_comunidad_article')
def add_article(request):
    form = ArticleForm(request.POST or None)
    if form.is_valid():
        article = form.save(commit=False)
        article.created_by = request.user
        article.save()
        msg = "Article saved successfully"
        messages.success(request, msg, fail_silently=True)
        return redirect(article)
    return render(request, 'comunidad/article_form.html', {'form': form})


@never_cache
@permission_required('edit_comunidad_article')
def edit_article(request, slug):
    article = get_object_or_404(SubscriberArticle, slug=slug)
    form = ArticleForm(request.POST or None, instance=article)
    if form.is_valid():
        article = form.save()
        msg = "Article updated successfully"
        messages.success(request, msg, fail_silently=True)
        return redirect(article)
    return render(request, 'comunidad/article_form.html', {'form': form, 'article': article})


@never_cache
def evento_detail(request, slug):
    evento = get_object_or_404(SubscriberEvento, slug=slug)
    return render(request, 'cartelera/evento_detail.html', {'evento': evento, 'is_comunidad': True})


@never_cache
@permission_required('add_comunidad_event')
def add_evento(request):
    form = EventoForm(request.POST or None)
    if form.is_valid():
        evento = form.save(commit=False)
        evento.created_by = request.user
        evento.save()
        msg = "Evento guardado exitosamente."
        messages.success(request, msg, fail_silently=True)
        return redirect(evento)
    return render(request, 'comunidad/evento_form.html', {'form': form})


@never_cache
@permission_required('edit_comunidad_event')
def edit_evento(request, slug):
    article = get_object_or_404(SubscriberEvento, slug=slug)
    form = EventoForm(request.POST or None, instance=article)
    if form.is_valid():
        evento = form.save()
        return redirect(evento)
    return render(request, 'comunidad/evento_form.html', {'form': form, 'article': article})


@never_cache
@login_required
@to_response
def profile(request):
    return 'comunidad/profile.html'


@never_cache
@login_required
def beneficios(request):
    """
    Register a benefit utilization
    """
    try:
        # filter form default benefits by circuit of user's socio
        form, success = (
            RegistroForm(
                Beneficio.objects.filter(circuit__in=request.user.socio.circuits.all()), request.POST or None
            ),
            False,
        )
        if form.is_valid():
            if request.POST.get('save'):
                Registro.objects.create(
                    subscriber=form.cleaned_data['subscriber'], benefit=form.cleaned_data['benefit']
                )
                success = True
            else:
                form.fields['document'].widget = HiddenInput()
                form.fields['benefit'].widget = HiddenInput()
                form.helper.layout = Layout(
                    HTML(u'¿Confirmar %(benefit)s para %(subscriber)s?' % form.cleaned_data),
                    FormActions(Submit('save', u'Confirmar')),
                )
        return render(request, 'comunidad/beneficios.html', {'form': form, 'is_comunidad': True, 'success': success})

    except Socio.DoesNotExist:
        # non socios cant access this view
        return redirect(reverse('comunidad'))


@never_cache
@to_response
def add_registro(request, beneficio_id, hashed_subscriber_id):
    decoded, error = decode_hashid(hashed_subscriber_id), None
    try:
        registro, created = Registro.objects.get_or_create(subscriber_id=decoded[0], benefit_id=beneficio_id)
        if not created:
            error = u'Su registro ya fue confirmado'
    except IndexError:
        raise Http404
    return 'comunidad/add_registro.html', {'error': error}


@method_decorator(never_cache, name='dispatch')
@method_decorator(permission_required("comunidad.verify_registro", raise_exception=True), name='dispatch')
class VerifyQRView(TemplateView):
    template_name = "comunidad/verify_registro.html"

    def get_registro(self, hashed_id):
        hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)
        original_id = hashids.decode(hashed_id)
        if not original_id:
            raise Registro.DoesNotExist
        return Registro.objects.get(id=original_id[0])

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is in the group "Verify QR". This needs to be created in the admin.
        if not request.user.groups.filter(name='Verify QR').exists():
            raise PermissionDenied
        try:
            self.registro = self.get_registro(kwargs['hashed_id'])
        except Registro.DoesNotExist:
            return render(request, self.template_name, {'message': 'Registro no encontrado'})
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if self.registro.is_fully_used():
            return self.render_error(request, self._fully_used_message())
        if self.registro.used_today():
            return self.render_error(request, self._used_today_message())
        self.registro.use_registro()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        remaining = self.registro.remaining_uses()
        msg = f'Registro para {self.registro.benefit.name} verificado con éxito'
        if remaining > 0:
            msg += f' (días restantes: {remaining})'
        context.update({"message": msg})
        return context

    def _fully_used_message(self):
        last_use = self.registro.uses.last()
        count = self.registro.uses.count()
        max_uses = self.registro.benefit.max_uses
        return (
            f"QR ya utilizado todos los días permitidos ({count}/{max_uses})."
            f" Último uso: {last_use.used_at.strftime('%d/%m/%Y a las %H:%M:%S')}"
            f" para: {self.registro.benefit.name}"
        )

    def _used_today_message(self):
        return (
            f"QR ya utilizado el día de hoy para: {self.registro.benefit.name}."
            f" Usos: {self.registro.uses.count()}/{self.registro.benefit.max_uses}"
        )

    def render_error(self, request, message):
        context = {'message': message}
        return render(request, self.template_name, context)


@method_decorator(never_cache, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class SendQRByEmailView(RedirectView):
    """
    View that sends a QR code by email. It's under development.
    Keyword arguments:
    registro_id -- the id of the registro to send the QR code by email
    """

    def get_redirect_url(self, *args, **kwargs):
        return reverse('admin:comunidad_registro_change', args=[self.kwargs['registro_id']])


@method_decorator(never_cache, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class SendQRByWhatsAppView(RedirectView):
    """
    View that sends the ticket URL via WhatsApp using the CRM API.
    Requires the Beneficio to have a whatsapp_template_name configured
    and the Registro to have a phone number.
    """

    def get_redirect_url(self, *args, **kwargs):
        return reverse('admin:comunidad_registro_change', args=[self.kwargs['registro_id']])

    def get(self, request, *args, **kwargs):
        import requests as http_requests
        from django.contrib.sites.models import Site

        registro = get_object_or_404(Registro, pk=self.kwargs['registro_id'])

        if not registro.phone:
            messages.error(request, "El registro no tiene número de teléfono.")
            return super().get(request, *args, **kwargs)

        benefit = registro.benefit
        if not benefit or not benefit.whatsapp_template_name:
            messages.error(request, "El beneficio no tiene plantilla de WhatsApp configurada.")
            return super().get(request, *args, **kwargs)

        hashed_id = registro.generate_hashed_id()
        domain = Site.objects.get_current().domain
        ticket_url = f"https://{domain}{reverse('gigantes-festival-entrada', kwargs={'hashed_id': hashed_id})}"

        phone = registro.phone.strip().replace(" ", "")
        if phone.startswith("0"):
            phone = "598" + phone[1:]
        if phone.startswith("+598"):
            phone = phone[1:]

        crm_api_uri = getattr(settings, 'CRM_SEND_WHATSAPP_API_URI', None)
        crm_api_key = getattr(settings, 'CRM_UPDATE_USER_API_KEY', None)

        if not crm_api_uri or not crm_api_key:
            messages.error(request, "La configuración de la API de WhatsApp no está disponible.")
            return super().get(request, *args, **kwargs)

        data = {
            "phone_number": phone,
            "template_name": benefit.whatsapp_template_name,
            "parameters": [{"message1": ticket_url}],
        }

        try:
            r = http_requests.post(
                crm_api_uri,
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Api-Key " + crm_api_key,
                },
            )
            r.raise_for_status()
            try:
                resp_data = r.json()
                if "error" in str(resp_data).lower():
                    messages.warning(request, f"WhatsApp enviado con advertencias: {resp_data}")
                else:
                    messages.success(request, f"WhatsApp enviado exitosamente a {phone}.")
            except ValueError:
                messages.success(request, f"WhatsApp enviado exitosamente a {phone}.")
        except http_requests.exceptions.HTTPError as e:
            messages.error(request, f"Error al enviar WhatsApp: {e}")
        except Exception as e:
            messages.error(request, f"Error al enviar WhatsApp: {e}")

        return super().get(request, *args, **kwargs)


@method_decorator(never_cache, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class ScanQRView(FormView):
    template_name = "comunidad/scan_qr.html"
    form_class = ScanQRForm

    def dispatch(self, request, *args, **kwargs):
        # Check if the user is in the group "Verify QR". This needs to be created in the admin.
        if not request.user.groups.filter(name='Verify QR').exists():
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["SITE_URL"] = settings.SITE_URL
        context.update({"message": "Escanear QR"})
        return context

    def form_valid(self, form):
        code = form.cleaned_data['code']
        hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)
        original_id = hashids.decode(code)
        try:
            registro = Registro.objects.get(id=original_id[0])
            if registro.is_fully_used():
                last_use = registro.uses.last()
                message = (
                    f'QR ya utilizado todos los días permitidos'
                    f' ({registro.uses.count()}/{registro.benefit.max_uses}).'
                    f' Último uso: {last_use.used_at.strftime("%d/%m/%Y %H:%M")}'
                )
                success = False
            elif registro.used_today():
                message = (
                    f'QR ya utilizado el día de hoy.'
                    f' Usos: {registro.uses.count()}/{registro.benefit.max_uses}'
                )
                success = False
            else:
                registro.use_registro()
                remaining = registro.remaining_uses()
                message = 'QR confirmado con éxito'
                if remaining > 0:
                    message += f' (días restantes: {remaining})'
                success = True
        except Registro.DoesNotExist:
            message = 'Registro no encontrado'
            success = False

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': success,
                'message': message
            })
        else:
            if success:
                messages.success(self.request, message)
            else:
                messages.error(self.request, message)

            return HttpResponseRedirect(reverse('scan_qr'))


@require_POST
def check_qr_code(request):
    code = request.POST.get('code')
    hashids = Hashids(salt=settings.SECRET_KEY, min_length=8)
    original_id = hashids.decode(code)

    if not original_id:
        return JsonResponse({"error": "Código QR inválido"}, status=400)
    try:
        registro = Registro.objects.get(id=original_id[0])
        if registro.is_fully_used():
            last_use = registro.uses.last()
            msg = (
                f"QR ya utilizado todos los días permitidos"
                f" ({registro.uses.count()}/{registro.benefit.max_uses})."
                f" Último uso: {last_use.used_at.strftime('%d/%m/%Y a las %H:%M:%S')}"
            )
            return JsonResponse(
                {"error": msg, "benefit": registro.benefit.name},
                status=400,
            )
        if registro.used_today():
            return JsonResponse(
                {
                    "error": f"QR ya utilizado el día de hoy."
                    f" Usos: {registro.uses.count()}/{registro.benefit.max_uses}",
                    "benefit": registro.benefit.name,
                },
                status=400,
            )
        return JsonResponse({
            "name": registro.benefit.name,
            "remaining_uses": registro.remaining_uses(),
        })
    except Registro.DoesNotExist:
        return JsonResponse({"error": "Código QR no encontrado"}, status=404)
