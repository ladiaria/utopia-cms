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
        if self.registro.used:
            return self.render_used_registro(request)
        self.registro.use_registro()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"message": f'Registro para {self.registro.benefit.name} verificado con éxito'}
        )
        return context

    def render_used_registro(self, request):
        message = (
            f"QR utilizado el día {self.registro.used.strftime('%d/%m/%Y a las %H:%M:%S')}"
            f" para: {self.registro.benefit.name}"
        )
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
            registro.use_registro()
            message = f'QR confirmado con éxito'
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
        if registro.used:
            # QR utilizado a las 13:40
            # Cinemateca - sábado 12 de octubre - 14:00
            msg = f"QR utilizado el día {registro.used.strftime('%d/%m/%Y a las %H:%M:%S')}"
            return JsonResponse(
                {"error": msg, "benefit": registro.benefit.name},
                status=400,
            )
        return JsonResponse({"name": registro.benefit.name})
    except Registro.DoesNotExist:
        return JsonResponse({"error": "Código QR no encontrado"}, status=404)
