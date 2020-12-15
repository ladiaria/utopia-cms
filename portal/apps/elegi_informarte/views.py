import requests
from django.conf import settings
from django.db import IntegrityError
from django.views.decorators.cache import never_cache

from decorators import render_response
from core.models import Category
from thedaily.models import Subscriber, SubscriptionPrices
from elegi_informarte.forms import SuscripcionForm, SuscripcionEmailForm, AttributionForm, AttributionAmountForm
from elegi_informarte.models import Serie, Suscripcion

to_response = render_response('elegi_informarte/templates/')
try:
    ELECCIONES_CATEGORY = Category.objects.get(slug='elecciones')
except Exception:
    ELECCIONES_CATEGORY = None


@never_cache
@to_response
def suscripcion(request):
    try:
        sp = SubscriptionPrices.objects.get(subscription_type='DDIGM')
    except SubscriptionPrices.DoesNotExist:
        sp = None

    is_authenticated = request.user.is_authenticated()
    if is_authenticated:
        form_class = SuscripcionForm
    else:
        form_class = SuscripcionEmailForm

    if request.POST:

        sf = form_class(request.POST)
        if sf.is_valid():

            try:
                sf.save()
            except IntegrityError:
                # save the data in the session and associate it after the user creates his new account.
                request.session['ei_cleaned_data'] = sf.cleaned_data
            if is_authenticated:
                r = requests.post(settings.CRM_CREATE_CUSTOMER_URI, data={
                    'api_key': settings.CRM_UPDATE_USER_API_KEY, 'customer_email': request.user.email})
                try:
                    r.raise_for_status()
                    request.user.groups.add(sp.auth_group)
                    request.user.subscriber.costumer_id = r.json()['customer_id']
                    request.user.subscriber.days = u'12345'
                    if ELECCIONES_CATEGORY:
                        request.user.subscriber.category_newsletters.add(ELECCIONES_CATEGORY)
                    request.user.subscriber.save()
                    return 'suscripcion.html', {'ready': True}
                except Exception:
                    return 'suscripcion.html', {'form': sf, 'crm_error': 'error interno'}
            else:
                return 'suscripcion.html', {'almost': True, 'email': sf.cleaned_data.get('email')}

        elif len(sf.errors) == 1 and 'user_has_free_account' in sf.errors.get('email', ''):
            request.session['ei_cleaned_data'] = sf.data
            return 'suscripcion.html', {'user_has_free_account': True, 'name_or_mail': sf.data.get('email')}

    else:

        sf = form_class()
        ei_cleaned_data = request.session.pop('ei_cleaned_data', None)
        if ei_cleaned_data:

            email = ei_cleaned_data['email']

            try:
                if is_authenticated:
                    # check email in session with the user logged-in
                    assert email == request.user.email
                else:
                    # check email in session with account created in session
                    assert email == request.session.pop('created_email', None)
                subscriber = Subscriber.objects.get(user__email=email)
                credencial_serie = Serie.objects.get(serie=ei_cleaned_data['credencial_serie'])
                credencial_numero = ei_cleaned_data['credencial_numero']
                try:
                    s = Suscripcion.objects.get(subscriber=subscriber)
                    s.credencial_serie = credencial_serie
                    s.credencial_numero = credencial_numero
                    s.save()
                except Suscripcion.DoesNotExist:
                    Suscripcion.objects.create(
                        subscriber=subscriber, credencial_serie=credencial_serie, credencial_numero=credencial_numero)
                # TODO: handle MultipleObjectsReturned
            except (IntegrityError, AssertionError) as e:
                return 'suscripcion.html', {
                    'form': sf, 'crm_error': 'error interno' + (': %s' % e if settings.DEBUG else '')}

            r = requests.post(settings.CRM_CREATE_CUSTOMER_URI, data={
                'api_key': settings.CRM_UPDATE_USER_API_KEY, 'customer_email': email})

            try:
                r.raise_for_status()
                subscriber.user.groups.add(sp.auth_group)
                subscriber.costumer_id = r.json()['customer_id']
                subscriber.days = u'12345'
                if ELECCIONES_CATEGORY:
                    subscriber.category_newsletters.add(ELECCIONES_CATEGORY)
                subscriber.save()
                return 'suscripcion.html', {'ready': True, 'email': email}
            except Exception:
                return 'suscripcion.html', {'form': sf, 'crm_error': 'error interno'}

    return 'suscripcion.html', {'form': sf}


@never_cache
@to_response
def attribution(request):
    ready = False
    if request.POST:
        if 'step1' in request.POST:
            amount_form = AttributionAmountForm(request.POST)
            if amount_form.is_valid():
                amount = amount_form.cleaned_data.get('amount')
                if not amount:
                    amount = amount_form.cleaned_data.get('radioAmounts')
                form = AttributionForm(initial={'amount': amount})
            else:
                form = amount_form
        else:
            form = AttributionForm(request.POST)
            if form.is_valid():
                form.save()
                ready = True
    else:
        form = AttributionAmountForm()
    return 'colaborar.html', {'form': form, 'ready': ready}
