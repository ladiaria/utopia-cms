# -*- coding: utf-8 -*-
import os
import json
import requests
import pymongo
from datetime import datetime
from urllib import pathname2url
from urlparse import urljoin, urlparse
from hashids import Hashids
from smtplib import SMTPRecipientsRefused
from social_django.models import UserSocialAuth
from emails.django import DjangoMessage as Message

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.core.mail import send_mail, mail_admins, mail_managers
from django.core.urlresolvers import reverse
from django.core.exceptions import MultipleObjectsReturned
from django.http import (
    HttpResponseRedirect,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseServerError,
    HttpResponseNotAllowed,
)
from django.forms.utils import ErrorList
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as do_login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache, cache_control
from django.template import TemplateDoesNotExist

from actstream import actions
from actstream.models import following
from favit.models import Favorite

from libs.utils import set_amp_cors_headers
from libs.tokens.email_confirmation import default_token_generator, get_signup_validation_url, send_validation_email

from apps import core_articleviewedby_mdb, core_articlevisits_mdb, signupwall_visitor_mdb
from core.models import Publication, Category, Article, ArticleUrlHistory
from thedaily.models import Subscriber, Subscription, SubscriptionPrices, UsersApiSession, OAuthState
from thedaily.forms import (
    LoginForm,
    SignupForm,
    SubscriberForm,
    SubscriberAddressForm,
    GoogleSigninForm,
    PasswordResetForm,
    SubscriptionForm,
    SubscriptionPromoCodeForm,
    SubscriptionCaptchaForm,
    SubscriptionPromoCodeCaptchaForm,
    PasswordResetRequestForm,
    PasswordChangeForm,
    GoogleSignupForm,
    SubscriberSignupForm,
    SubscriberSignupAddressForm,
    ConfirmEmailRequestForm,
)
from thedaily.forms.subscriber import ProfileForm, UserForm
from thedaily.utils import recent_following, add_default_category_newsletters
from thedaily.email_logic import limited_free_article_mail
from signupwall.middleware import get_article_by_url_path, get_session_key, get_or_create_visitor

from decorators import render_response
from exceptions import UpdateCrmEx
from tasks import send_notification, notify_digital, notify_paper


to_response = render_response('thedaily/templates/')


def notify_new_subscription(subscription_url, extra_subject=u''):
    subject = settings.SUBSCRIPTION_EMAIL_SUBJECT + extra_subject
    rcv = settings.SUBSCRIPTION_EMAIL_TO
    from_mail = getattr(settings, 'DEFAULT_FROM_EMAIL')
    send_mail(subject, settings.SITE_URL + subscription_url, from_mail, rcv, fail_silently=True)


@never_cache
def nl_subscribe(request, publication_slug=None, hashed_id=None):
    if publication_slug and hashed_id:
        # 1click subscription
        publication = get_object_or_404(Publication, slug=publication_slug, has_newsletter=True)
        ctx = {
            'publication': publication,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        decoded = Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)
        # TODO: if authenticated => assert same logged in user (also for other 1-click views in this module)
        if decoded:
            subscriber = get_object_or_404(Subscriber, id=decoded[0])
            if not subscriber.user:
                raise Http404
            try:
                subscriber.newsletters.add(publication)
            except Exception as e:
                # for some reason UpdateCrmEx does not work in test (Python ver?)
                ctx['error'] = e.displaymessage
            return render(request, 'nlsubscribe.html', ctx)
        else:
            raise Http404
    # default behavour: go to profile or login
    next_page = reverse('edit-profile') + '#id_newsletters_wrapper'
    if request.user.is_authenticated():
        return HttpResponseRedirect(next_page)
    else:
        request.session['next'] = next_page
        return HttpResponseRedirect(reverse('account-login'))


@never_cache
@to_response
def nl_category_subscribe(request, slug, hashed_id=None):
    """
    if hashed id is given, this view will do the things than nl_subscribe with a category instead of a publication
    """
    if hashed_id:
        # 1click subscription
        category = get_object_or_404(Category, slug=slug, has_newsletter=True)
        ctx = {
            'category': category,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        decoded = Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)
        if decoded:
            subscriber = get_object_or_404(Subscriber, id=decoded[0])
            if not subscriber.user:
                raise Http404
            try:
                subscriber.category_newsletters.add(category)
            except Exception as e:
                # for some reason UpdateCrmEx does not work in test (Python ver?)
                ctx['error'] = e.displaymessage
            return 'nlsubscribe.html', ctx
        else:
            raise Http404
    else:
        # next page is the first category NL anchor in edit profile page
        next_page = reverse('edit-profile') + '#category-newsletter-' + slug
        if request.user.is_authenticated():
            return HttpResponseRedirect(next_page)
        else:
            request.session['next'] = next_page
            return HttpResponseRedirect(reverse('account-login'))


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login(request):
    next_page = request.session.get('next', request.GET.get('next', '/'))

    if request.user.is_authenticated():
        return HttpResponseRedirect(next_page)

    initial, name_or_mail = {}, request.GET.get('name_or_mail')
    if name_or_mail:
        initial['name_or_mail'] = name_or_mail
    response, login_form, login_error = None, LoginForm(initial=initial), None
    if request.method == 'POST':
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            user = authenticate(username=login_form.username, password=request.POST.get('password'))
            if user is not None:
                if user.is_active:
                    do_login(request, user)
                    request.session.pop('next', None)
                    response = HttpResponseRedirect(next_page)
                else:
                    response = HttpResponseRedirect(reverse('account-confirm_email'))
            else:
                login_error = u'Usuario y/o contraseña incorrectos.'
        else:
            # alert admins if is a user with duplicated email.
            email = login_form.data.get('name_or_mail')
            if email and User.objects.filter(email=email).count() > 1:
                mail_managers("Multiple email in users", email)
        if login_error:
            if '__all__' in login_form.errors:
                login_form.errors['__all__'].append(login_error)
            else:
                login_form.errors['__all__'] = [login_error]
    if not response:
        response = render(
            request,
            getattr(settings, 'THEDAILY_LOGIN_TEMPLATE', 'login.html'),
            {'login_form': login_form, 'next_page': next_page, 'next': pathname2url(next_page)},
        )
    response['Expires'], response['Pragma'] = 0, 'no-cache'
    return response


@never_cache
@to_response
def signup(request):
    initial, next_page = {}, request.GET.get('next')
    if next_page:
        initial['next_page'] = next_page
    email = request.GET.get('email')
    if email:
        initial['email'] = email
    signup_form = SignupForm(initial=initial)
    if request.method == 'POST':
        post = request.POST.copy()
        signup_form = SignupForm(post)
        if signup_form.is_valid():
            user = signup_form.create_user()
            add_default_category_newsletters(user.subscriber)
            # TODO: check if request is needed
            # TODO: handle smtp errors
            send_validation_email(
                u'Verificá tu cuenta',
                user,
                'notifications/account_signup.html',
                get_signup_validation_url,
                {'request': request},
            )
            next_page = signup_form.cleaned_data.get('next_page')
            if next_page:
                return HttpResponseRedirect(next_page)
            else:
                return 'welcome.html', {'signup_mail': user.email}
    return 'signup.html', {'signup_form': signup_form, 'errors': signup_form.errors.get('__all__')}


@never_cache
def welcome(request, signup=False, subscribed=False):
    """
    welcome page, will be rendered only if welcome in session has a value, otherwise will be redirected to home.
    """
    if request.session.get('welcome'):
        request.session.pop('welcome')
        return render(request, settings.THEDAILY_WELCOME_TEMPLATE, {'signup': signup, 'subscribed': subscribed})
    else:
        return HttpResponseRedirect(reverse('home'))


@never_cache
@to_response
def google_phone(request):
    # if planslug in session this came from a new subscription attemp and we should continue it
    planslug = request.session.get('planslug')
    if planslug:
        request.session.pop('planslug')
        if request.GET.get('is_new') == u'1':
            # default category newsletters are not added here because some subscriptions may not add the default
            # category newsletters. TODO: Add a M2M relation from subscriptionprices(planslug) to Category
            pass
        return HttpResponseRedirect(reverse('subscribe', kwargs={'planslug': planslug}))
    try:
        oas = OAuthState.objects.get(state=request.session.get('google-oauth2_state'))
    except OAuthState.DoesNotExist:
        raise Http404
    profile = get_or_create_user_profile(oas.user)
    google_signin_form = GoogleSigninForm(instance=profile)
    if request.method == 'POST':
        google_signin_form = GoogleSigninForm(request.POST, instance=profile)
        if google_signin_form.is_valid():
            google_signin_form.save()
            send_notification(oas.user, 'notifications/signup.html', u'¡Te damos la bienvenida!')
            oas.delete()
            request.session['welcome'] = True
            return HttpResponseRedirect('%s?next=%s' % (
                reverse('social:begin', kwargs={'backend': 'google-oauth2'}), reverse('account-welcome')))
    else:
        # if is a new user add the default category newsletters (reached only from "free" subscriptions)
        if request.GET.get('is_new') == u'1':
            add_default_category_newsletters(profile)
    return 'google_signup.html', {'google_signin_form': google_signin_form}


@never_cache
@to_response
def subscribe(request, planslug, category_slug=None):
    """
    This view handles the plan subscriptions.
    """
    custom_module = getattr(settings, 'THEDAILY_VIEWS_CUSTOM_MODULE', None)
    if custom_module:
        subscribe_custom = __import__(custom_module, fromlist=['subscribe']).subscribe
        return subscribe_custom(request, planslug, category_slug)
    else:
        # category_slug is allowed only if custom_module is defined
        if category_slug:
            raise Http404
        auth = request.GET.get('auth')
        if auth:
            request.session['planslug'] = planslug
            return HttpResponseRedirect('%s?next=%s' % (
                reverse("social:begin", kwargs={'backend': auth}),
                reverse('subscribe', kwargs={'planslug': planslug})))

        oauth2_state = request.session.get('google-oauth2_state')
        if oauth2_state:
            try:
                oas = OAuthState.objects.get(state=oauth2_state)
            except OAuthState.DoesNotExist:
                request.session.pop('google-oauth2_state')
                return HttpResponseRedirect(request.path)

        product = get_object_or_404(Publication, slug=settings.DEFAULT_PUB)
        # TODO post release: Usage guide should describe when 404 is raised here
        subscription_price = get_object_or_404(SubscriptionPrices, subscription_type=planslug)
        oauth2_button = True
        subscription_in_process = False

        if request.user.is_authenticated():

            is_subscriber = request.user.subscriber.is_subscriber()

            initial = {
                'email': request.user.email,
                'first_name': request.user.subscriber.name or ' '.join(
                    [request.user.first_name, request.user.last_name]).strip()
            }
            if request.user.subscriber.phone:
                initial['telephone'] = request.user.subscriber.phone

            subscriber_form = SubscriberForm(initial=initial)

            # do not show oauth button if this user is already associated
            if request.user.social_auth.filter(provider='google-oauth2').exists():
                oauth2_button = False

        else:
            # not authenticated
            is_subscriber = False
            if oauth2_state:
                oauth2_button = False
                profile = get_or_create_user_profile(oas.user)
                subscriber_form = GoogleSignupForm(instance=profile)
            else:
                subscriber_form = \
                    SubscriberSignupForm() if subscription_price.ga_category == 'D' else SubscriberSignupAddressForm()
            # check session and if a new user was created, encourage login
            if request.method == 'GET':
                subscription = request.session.get('subscription')
                subscription_in_process = subscription and subscription.subscriber

        PROMOCODE_ENABLED = getattr(settings, 'THEDAILY_PROMOCODE_ENABLED', False)
        # TODO post release: do not asume CF for getting the country (do it like signupwall gets the ip_address)
        ipcountry = request.META.get('HTTP_CF_IPCOUNTRY', settings.SUBSCRIPTION_CAPTCHA_DEFAULT_COUNTRY)
        subscription_formclass = (SubscriptionPromoCodeForm if PROMOCODE_ENABLED else SubscriptionForm) \
            if ipcountry in settings.SUBSCRIPTION_CAPTCHA_COUNTRIES_IGNORED \
            else (SubscriptionPromoCodeCaptchaForm if PROMOCODE_ENABLED else SubscriptionCaptchaForm)

        initial = {'subscription_type_prices': planslug}
        subscription_form = subscription_formclass(initial=initial) \
            if subscription_price.ga_category == 'D' else SubscriptionForm(initial=initial)

        if not is_subscriber and request.method == 'POST':
            post = request.POST.copy()
            if request.user.is_authenticated():
                subscription = request.session.get('subscription')
                subscription_type = request.session.get('subscription_type')
                if subscription and subscription_type:
                    # delete possible in-process subscription
                    subscription.subscription_type_prices.remove(subscription_type)
                subscriber_form_v = SubscriberForm(post) \
                    if subscription_price.ga_category == 'D' else SubscriberAddressForm(post)
            elif oauth2_state:
                profile = get_or_create_user_profile(oas.user)
                subscriber_form_v = GoogleSignupForm(post, instance=profile)
            else:
                subscriber_form_v = SubscriberSignupForm(post) \
                    if subscription_price.ga_category == 'D' else SubscriberSignupAddressForm(post)
            subscription_form_v = subscription_formclass(post) \
                if subscription_price.ga_category == 'D' else SubscriptionForm(post)

            if subscriber_form_v.is_valid(planslug) and subscription_form_v.is_valid():
                subscription = Subscription.objects.create(email=oas.user.email if oauth2_state else post['email'])
                sp = SubscriptionPrices.objects.get(subscription_type=post['subscription_type_prices'])
                subscription.subscription_type_prices.add(sp)
                if oauth2_state:
                    subscriber_form_v.save()
                    subscription.telephone = post.get('phone', post.get('telephone'))
                    subscription.promo_code = post.get('promo_code')
                else:
                    subscription.first_name = post['first_name']
                    subscription.telephone = post['telephone']
                    subscription.address = post.get('address')
                    subscription.city = post.get('city')
                    subscription.province = post.get('province')
                    subscription.promo_code = post.get('promo_code')
                if request.user.is_authenticated():
                    subscription.subscriber = request.user
                else:
                    if oauth2_state:
                        user = oas.user
                    else:
                        user = subscriber_form_v.signup_form.create_user()
                        try:
                            send_validation_email(
                                u'Verificá tu cuenta de la diaria', user, 'notifications/account_signup.html',
                                get_signup_validation_url)
                        except Exception as smtp_exc:
                            subscription.delete()
                            errors = subscriber_form_v._errors.setdefault("email", ErrorList())
                            errors.append(
                                u'No se pudo enviar el email de verificación al crear tu cuenta, ' + (
                                    u'¿lo escribiste correctamente?' if type(smtp_exc) is SMTPRecipientsRefused else
                                    u'intentá <a class="ld-link-low" href="%s">pedirlo nuevamente</a>.'
                                    % reverse('account-confirm_email')
                                )
                            )
                            return 'subscribe.html', {
                                'subscriber_form': subscriber_form_v, 'subscription_form': subscription_form_v}
                    subscription.subscriber = user

                subscription.save()

                # we should save the subscription and its type in the session
                request.session['subscription'] = subscription
                request.session['subscription_type'] = sp
                if oauth2_state:
                    request.session['notify_phone_subscription'] = True
                    request.session['preferred_time'] = post.get('preferred_time')
                    return HttpResponseRedirect('%s?next=%s' % (
                        reverse('social:begin', kwargs={'backend': 'google-oauth2'}), reverse('phone-subscription')))
                else:
                    request.session['notify_phone_subscription'] = True
                    request.session['preferred_time'] = post.get('preferred_time')
                    return HttpResponseRedirect(reverse('phone-subscription'))

            else:
                return 'subscribe.html', {
                    'subscriber_form': subscriber_form_v, 'subscription_form': subscription_form_v,
                    'oauth2_button': oauth2_button}

        return 'subscribe.html', {
            'subscriber_form': subscriber_form, 'oauth2_button': oauth2_button, 'subscription_form': subscription_form,
            'is_already_subscribed': is_subscriber, 'product': product, 'planslug': planslug,
            'subscription_price': SubscriptionPrices.objects.get(subscription_type=planslug),
            'subscription_in_process': subscription_in_process}


@never_cache
@login_required
@to_response
def edit_subscription(request):
    user = request.user
    subscription_form = SubscriptionForm()

    if request.method == 'POST':  # If the form has been submitted...
        subscription_form = SubscriptionForm(request.POST, instance=user)

        if subscription_form.is_valid():  # All validation rules pass
            subscription_form.save()
            messages.success(request, u'Suscripción Actualizada.')
        else:
            subscription_form = SubscriptionForm(instance=user)

    return 'edit_subscription.html', {'subscription_form': subscription_form}


def hash_validate(user_id, hash):
    user = get_object_or_404(User, id=user_id)
    if not default_token_generator.check_token(user, hash):
        raise Http404(u'Invalid token.')
    return user


def get_or_create_user_profile(user):
    try:
        profile = user.subscriber
    except Subscriber.DoesNotExist:
        profile = Subscriber.objects.create(user=user)
    return profile


def get_password_validation_url(user):
    return reverse(
        'account-password_change-hash',
        kwargs={'user_id': str(user.id), 'hash': default_token_generator.make_token(user)})


@never_cache
@to_response
def complete_signup(request, user_id, hash):
    """ This view is executed when the user clicks account activation button in his/her email. """
    user = hash_validate(user_id, hash)
    user.is_active = True
    if user.username != user.email:
        user.username = user.email
    user.save()
    subscriber = get_or_create_user_profile(user)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    do_login(request, user)

    # send notification to admins and a custom welcome email to the user for some types of subscriptions but only if
    # welcome val not in session (to avoid duplicate sending)
    send_default_welcome = 'welcome' not in request.session

    if send_default_welcome:
        mail_admins('New user', u'%i - %s' % (user.id, user.get_full_name()))

    # If a delayed email is required, this code can schedule a task for that:
    # task = notify_user(user.id) #(from tasks import notify_user)
    # Need to remove the "apps." at the beggining of the task name
    # task.task_name = re.sub(r'^apps\.', '', task.task_name) #(import re)
    # task.save()

    is_subscriber_any = subscriber.is_subscriber_any()

    if send_default_welcome and is_subscriber_any and user.suscripciones.count() == 1:
        st = user.suscripciones.all()[0].subscription_type_prices
        if st.count() == 1:
            subscription_type = st.all()[0].subscription_type
            if subscription_type == u'DDIGM':
                send_default_welcome = False
                notify_digital(user)
            elif subscription_type == u'PAPYDIM':
                send_default_welcome = False
                notify_paper(user)

    if send_default_welcome:
        send_notification(user, 'notifications/signup.html', u'Tu suscripción digital gratuita está activa')

    request.session['welcome'] = 'account-welcome' + ('-s' if is_subscriber_any else '')

    if not user.has_usable_password():
        # email is valid, so, generate pass token and redirect to change form
        return HttpResponseRedirect(get_password_validation_url(user))

    if is_subscriber_any:
        return HttpResponseRedirect(reverse('account-welcome-s'))
    else:
        return HttpResponseRedirect(reverse('account-welcome'))


@never_cache
@to_response
def password_reset(request, user_id=None, hash=None):
    if user_id and hash:
        return password_change(request, user_id, hash)
    reset_form = PasswordResetRequestForm()
    if request.method == 'POST':
        # TODO: we should also check for telephone number as google_auth
        post = request.POST.copy()
        reset_form = PasswordResetRequestForm(post)
        if reset_form.is_valid():
            if reset_form.user:
                # TODO: handle smtp errors
                send_validation_email(
                    u'Recuperación de contraseña',
                    reset_form.user,
                    'notifications/password_reset_body.html',
                    get_password_validation_url,
                )
            return HttpResponseRedirect(reverse('account-password_reset-mail_sent'))
    return 'password_reset.html', {'form': reset_form}


@never_cache
@to_response
def confirm_email(request):
    confirm_email_form = ConfirmEmailRequestForm()
    if request.method == 'POST':
        confirm_email_form = ConfirmEmailRequestForm(request.POST)
        if confirm_email_form.is_valid():
            # TODO: handle smtp errors
            send_validation_email(
                u'Verificá tu cuenta',
                confirm_email_form.user,
                'notifications/account_signup.html',
                get_signup_validation_url,
            )
            return 'confirm_email.html', {'sent': True, 'email': confirm_email_form.cleaned_data['email']}
    return 'confirm_email.html', {'form': confirm_email_form}


@never_cache
def session_refresh(request):
    """
    This view was created with the only purpose to delete subscription and
    subscription_type session variables for an in-process subscription.
    """
    subscription = request.session.pop('subscription', None)
    subscription_type = request.session.pop('subscription_type', None)
    if subscription and subscription_type:
        subscription.subscription_type_prices.remove(subscription_type)
    referer = request.META.get('HTTP_REFERER')
    return HttpResponseRedirect(
        referer if referer and referer != request.path else '/')


@never_cache
@to_response
def password_change(request, user_id=None, hash=None):
    password_change_form = PasswordChangeForm()
    if user_id and hash:
        password_change_form = PasswordResetForm(user=user_id, hash=hash)
        user = get_object_or_404(User, id=user_id)
    else:
        if not request.user.is_authenticated():
            raise Http404(u'Unauthorized access.')
        user = request.user
    if request.method == 'POST':
        post = request.POST.copy()
        password_change_form = PasswordChangeForm(post, user=request.user)
        if user_id and hash:
            password_change_form = PasswordResetForm(post, user=user_id, hash=hash)
        if password_change_form.is_valid():
            user.set_password(password_change_form.get_password())
            user.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            do_login(request, user)
            return HttpResponseRedirect(reverse(request.session.get('welcome') or 'account-password_change-done'))
    return 'password_change.html', {'form': password_change_form, 'user_id': user_id, 'hash': hash}


@never_cache
@to_response
@login_required
def edit_profile(request, user=None):
    user = user or request.user
    profile = get_or_create_user_profile(user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, instance=profile)

        old_email = user.email
        if user_form.is_valid() and profile_form.is_valid():
            try:
                user_form.save()
                profile_form.save()
                if old_email != user.email:
                    user.is_active = False
                    user.save()
                    # TODO: handle smtp errors
                    send_validation_email(
                        u'Verificá tu cuenta', user, 'notifications/account_signup.html', get_signup_validation_url
                    )
                    messages.success(
                        request, u'Perfil actualizado, revisá tu email para verificar el cambio de email.')
                    logout(request)
                    return HttpResponseRedirect(reverse('account-logout'))
                else:
                    messages.success(request, u'Perfil Actualizado.')
            except UpdateCrmEx as e:
                messages.warning(request, e.displaymessage)
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    try:
        oauth2_assoc = UserSocialAuth.objects.get(user=user, provider=u'google-oauth2')
    except UserSocialAuth.DoesNotExist:
        oauth2_assoc = None

    return 'edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'is_subscriber_digital': user.subscriber.is_digital_only(),
        'google_oauth2_assoc': oauth2_assoc,
        'google_oauth2_allow_disconnect': oauth2_assoc and (user.email != oauth2_assoc.uid),
        'publication_newsletters': Publication.objects.filter(has_newsletter=True),
        'category_newsletters': Category.objects.filter(has_newsletter=True),
    }


@never_cache
@to_response
@login_required
def lista_lectura_leer_despues(request):
    followings = recent_following(request.user, Article)
    followings_count = len(followings)
    if request.is_ajax():
        return HttpResponse(followings_count)

    # paginator for leer_despues
    page = request.GET.get('pagina', 1)
    paginator_leer_despues = Paginator(followings, 10)
    try:
        followings = paginator_leer_despues.page(page)
    except PageNotAnInteger:
        followings = paginator_leer_despues.page(1)
    except EmptyPage:
        followings = paginator_leer_despues.page(paginator_leer_despues.num_pages)
    # end paginator for leer_despues

    return 'lista-lectura.html', {'leer_despues': followings, 'leer_despues_count': followings_count}


@never_cache
@to_response
@login_required
def lista_lectura_favoritos(request):
    user = request.user
    favoritos = [favorito.target for favorito in Favorite.objects.for_user(user)]
    favoritos_count = len(favoritos)
    if request.is_ajax():
        return HttpResponse(favoritos_count)

    # paginator for favoritos
    page = request.GET.get('pagina', 1)
    paginator_favoritos = Paginator(favoritos, 10)
    try:
        favoritos = paginator_favoritos.page(page)
    except PageNotAnInteger:
        favoritos = paginator_favoritos.page(1)
    except EmptyPage:
        favoritos = paginator_favoritos.page(paginator_favoritos.num_pages)
    # end paginator for favoritos

    return 'lista-lectura.html', {'favoritos': favoritos, 'favoritos_count': favoritos_count}


@never_cache
@login_required
def fav_add_or_remove(request):
    """
    Cloned from favit.views and modified only the response with content_type arg to make it run in Django 1.11+.
    """
    if not request.is_ajax():
        return HttpResponseNotAllowed()

    user = request.user

    try:
        app_model = request.POST["target_model"]
        obj_id = int(request.POST["target_object_id"])
    except (KeyError, ValueError):
        return HttpResponseBadRequest()

    fav = Favorite.objects.get_favorite(user, obj_id, model=app_model)

    if fav is None:
        Favorite.objects.create(user, obj_id, app_model)
        status = 'added'
    else:
        fav.delete()
        status = 'deleted'

    response = {
        'status': status,
        'fav_count': Favorite.objects.for_object(obj_id, app_model).count()
    }

    return HttpResponse(
        json.dumps(response, ensure_ascii=False),
        content_type='application/json'
    )


@never_cache
@to_response
@login_required
def lista_lectura_historial(request):
    """
    Returns a paginated view of all articles viewed by the user, ordered by recently viewewd.
    They are the ones in mongodb that have not been synced yet, union the ones already sinced saved in the model used
    for this purpose.
    """
    # start the result set with mongo because these are the most recent viewed.
    historial, mids = [], []
    if core_articleviewedby_mdb:
        for a in core_articleviewedby_mdb.posts.find({'user': request.user.id}).sort('viewed_at', pymongo.DESCENDING):
            try:
                article_id = a['article']
                historial.append(Article.objects.get(id=article_id))
                mids.append(article_id)
            except Article.DoesNotExist:
                # the article could be removed
                pass
    # perform the union with the ones in the model
    historial += [
        avb.article for avb in request.user.articleviewedby_set.exclude(article_id__in=mids).order_by('-viewed_at')]
    historial_count = len(historial)
    if request.is_ajax():
        return HttpResponse(historial_count)

    page = request.GET.get('pagina', 1)
    paginator_historial = Paginator(historial, 10)
    try:
        historial = paginator_historial.page(page)
    except PageNotAnInteger:
        historial = paginator_historial.page(1)
    except EmptyPage:
        historial = paginator_historial.page(paginator_historial.num_pages)

    return 'lista-lectura.html', {'historial': historial, 'historial_count': historial_count}


@never_cache
@csrf_exempt
@require_POST
def lista_lectura_toggle(request, event, article_id):

    if not hasattr(request.user, 'subscriber'):
        return HttpResponseForbidden()

    subscriber_id = request.user.subscriber.id

    try:
        user, article = Subscriber.objects.get(id=subscriber_id).user, Article.objects.get(id=article_id)
    except Exception:
        return HttpResponseServerError()

    if event == 'add':
        actions.follow(user, article)
    elif event == 'remove':
        actions.unfollow(user, article)
    elif event == 'favToggle':
        fav = Favorite.objects.get_favorite(user, article.id, model='core.Article')
        if fav is None:
            Favorite.objects.create(user, article.id, model='core.Article')
        else:
            fav.delete()

    return HttpResponse()


@never_cache
@staff_member_required
def user_profile(request, user_id):
    try:
        assert request.user.is_superuser
        user = User.objects.get(id=int(user_id))
    except AssertionError:
        return HttpResponseForbidden()
    except User.DoesNotExist:
        raise Http404
    return edit_profile(request, user)


@never_cache
@csrf_exempt
def update_user_from_crm(request):
    """
    Update User or Subscriber from CRM.
    updatefromcrm flag must be set to avoid ws loop.
    User is updated when the field to change is "email"
    Subscriber is updated when the field is other (a field mapping between CRM
    fields and Subscriber's field should be provided somewhere)
    """
    def changeuseremail(user, email, newemail):
        if user.email == user.username:
            user.username = newemail
        user.email = newemail

    def changesubscriberfield(s, field, v):
        mfield = settings.CRM_UPDATE_SUBSCRIBER_FIELDS[field]
        # eval the value before saving if type field is bool
        setattr(s, mfield, eval(v) if type(getattr(s, mfield)) is bool else v)

    if request.method == 'POST':
        try:
            contact_id = request.POST[u'contact_id']
            email = request.POST.get(u'email')
            newemail = request.POST.get(u'newemail')
            field = request.POST.get(u'field')
            value = request.POST.get(u'value')
            if request.POST[u'ldsocial_api_key'] != settings.CRM_UPDATE_USER_API_KEY:
                return HttpResponseForbidden()
        except KeyError:
            return HttpResponseBadRequest()
        try:
            s = Subscriber.objects.get(contact_id=contact_id)
            if field == u'email':
                check_user = User.objects.filter(email=newemail)
                if check_user.exists():
                    if check_user.count() == 1:
                        check_user = check_user[0]
                    else:
                        msg = u'Multiple email in users'
                        mail_managers(msg, email)
                        return HttpResponseServerError()
                if check_user and check_user != s.user:
                    return HttpResponseBadRequest('El email ya existe en otro usuario de la web')
                changeuseremail(s.user, email, newemail)
                s.user.updatefromcrm = True
                s.user.save()
            elif field == u'newsletters':
                # we remove the Subscriber's newsletters (whose pub has_newsletter) and name not in json, and then add
                # all the ones in the value JSON list that are missing.
                s.updatefromcrm, pub_names = True, json.loads(value)
                for pub in s.newsletters.filter(has_newsletter=True):
                    if pub.name in pub_names:
                        pub_names.remove(pub.name)
                    else:
                        s.newsletters.remove(pub)
                for pub_name in pub_names:
                    try:
                        s.newsletters.add(Publication.objects.get(name=pub_name))
                    except Publication.DoesNotExist:
                        pass
            elif field == u'area_newsletters':
                # the same as above but for category newsletters
                s.updatefromcrm, cat_names = True, json.loads(value)
                for cat in s.category_newsletters.filter(has_newsletter=True):
                    if cat.name in cat_names:
                        cat_names.remove(cat.name)
                    else:
                        s.category_newsletters.remove(cat)
                for category_name in cat_names:
                    try:
                        s.category_newsletters.add(Category.objects.get(name=category_name))
                    except Category.DoesNotExist:
                        pass
            else:
                changesubscriberfield(s, field, value)
                s.updatefromcrm = True
                s.save()
        except Subscriber.DoesNotExist:
            if email and field == 'email':
                try:
                    u = User.objects.get(email__exact=email)
                    changeuseremail(u, email, newemail)
                    u.updatefromcrm = True
                    u.save()
                except User.DoesNotExist:
                    # This user should be created automatically tomorrow
                    pass
                except MultipleObjectsReturned:
                    msg = u'Multiple email in users'
                    mail_managers(msg, email)
                    return HttpResponseServerError()
                except IntegrityError as ie:
                    mail_managers(u'IntegrityError saving user', str(ie))
                    return HttpResponseServerError()
        except IntegrityError as ie:
            mail_managers(u'IntegrityError saving user', str(ie))
            return HttpResponseServerError()
        except KeyError:
            pass
        return HttpResponse("OK", content_type="application/json")
    raise Http404


@never_cache
def amp_access_authorization(request):
    """
    Este endpoint obtiene la cantidad de visitas que posee el usuario y lo devuelve incrementado en uno para contar la
    visita que se está haciendo en este momento.
    El registro de dicha visita se hace en el endpoint de pingback (siguiente funcion).
    Return 'access' True if signupwall middleware is not enabled.
    TODO: translate all this docstring to english.
    """
    try:
        url = request.GET['url']
    except KeyError:
        return HttpResponseBadRequest()

    path = urlparse(url).path
    authenticated = request.user.is_authenticated()
    result, has_subscriber = {'authenticated': authenticated}, hasattr(request.user, 'subscriber')
    subscriber_any = authenticated and has_subscriber and request.user.subscriber.is_subscriber_any()
    result['subscriber_any'] = subscriber_any

    if path == '/' or not settings.SIGNUPWALL_ENABLED:

        result.update({'subscriber': subscriber_any, 'access': True, 'signupwall_enabled': False})

    else:

        try:
            article = get_article_by_url_path(path)
        except Article.DoesNotExist:
            # search in url history
            article = get_object_or_404(ArticleUrlHistory, absolute_url=path).article

        result.update({'signupwall_enabled': True, 'article_restricted': article.is_restricted()})

        # TODO: update logic using the "restricted" information
        if authenticated:

            if has_subscriber:
                is_subscriber = (
                    request.user.subscriber.is_subscriber()
                    or any(request.user.subscriber.is_subscriber(p.slug) for p in article.publications())
                    or any(request.user.subscriber.is_subscriber(p.slug) for p in article.additional_access.all())
                )
                # newsletters
                result.update([('nl_' + slug, True) for slug in request.user.subscriber.get_newsletters_slugs()])
            else:
                is_subscriber = False

            result.update(
                {
                    'subscriber': is_subscriber,
                    'article_allowed': is_subscriber or article.is_public(),
                    'followed': article in following(request.user, Article),
                    'favourited': article in [f.target for f in Favorite.objects.for_user(request.user)],
                }
            )

            if is_subscriber:

                result.update({'access': True, 'edit': request.user.has_perm('core.change_article')})

            else:

                MAX_CREDITS = 10

                # Find up to MAX_CREDITS + 2 articles (more than that makes no difference in this logic)
                articles_visited = set() if article.is_public() else set([article.id])
                articles_visited_count = len(articles_visited)

                if core_articleviewedby_mdb:
                    for x in core_articleviewedby_mdb.posts.find({'user': request.user.id, 'allowed': None}):
                        articles_visited.add(x['article'])
                        articles_visited_count = len(articles_visited)
                        if articles_visited_count >= MAX_CREDITS + 2:
                            break

                signupwall_limit_reach = not article.is_public() and (articles_visited_count == MAX_CREDITS + 1)
                if signupwall_limit_reach:
                    # this code is also in signupwall/middleware
                    limited_free_article_mail(request.user)

                credits = MAX_CREDITS - articles_visited_count
                result['access'] = article.is_public() or (credits >= 0)
                result['credits'] = credits if credits > 0 else False

        else:

            # anon users, they will face the signupwall.
            result['subscriber'] = False
            result['access'] = article.is_public()
            result['credits'] = False
            if settings.AMP_DEBUG:
                print('AMP DEBUG: session_key=%s, authorization_result=%s' % (get_session_key(request), result))

    response = HttpResponse(json.dumps(result), content_type="application/json")
    return set_amp_cors_headers(request, response)


@never_cache
@csrf_exempt
def amp_access_pingback(request):
    """
    Registers an article view in AMP
    """

    # only do something if log views is enabled
    if settings.CORE_LOG_ARTICLE_VIEWS:

        url = request.GET['url']
        path = urlparse(url).path

        # when path is '/' treat it as a public article
        if path != '/':
            try:
                article = get_article_by_url_path(path)
            except Article.DoesNotExist:
                # Search in url history
                article = get_object_or_404(ArticleUrlHistory, absolute_url=path).article

            article_allowed = request.GET.get('article_allowed') == 'true'
            blocked = not article_allowed and request.GET.get('article_restricted') == 'true'

            if request.user.is_authenticated():

                if core_articleviewedby_mdb and not blocked:

                    set_values = {'viewed_at': datetime.now()}
                    if article_allowed:
                        set_values['allowed'] = True
                    core_articleviewedby_mdb.posts.update_one(
                        {'user': request.user.id, 'article': article.id}, {'$set': set_values}, upsert=True
                    )

            elif not article.is_public() and not blocked:
                # only spend a credit if the article is not public and was not blocked

                visitor = get_or_create_visitor(request)

                if visitor and signupwall_visitor_mdb:
                    signupwall_visitor_mdb.posts.update_one(
                        {'_id': visitor.get('_id')}, {'$set': {'path_visited': path}}
                    )

            # inc this article visits if not blocked
            if not blocked and core_articlevisits_mdb:
                core_articlevisits_mdb.posts.update_one({'article': article.id}, {'$inc': {'views': 1}}, upsert=True)

    response = HttpResponse()
    return set_amp_cors_headers(request, response)


@never_cache
@csrf_exempt
def users_api(request):
    max_device_msg = u'Ha superado la cantidad de dispositivos permitidos'
    if request.method == 'POST':
        try:
            email = request.POST['email']
            if not email or request.POST['ldsocial_users_api_key'] != settings.LDSOCIAL_USERS_API_KEY:
                return HttpResponseForbidden()
            password = request.POST['password']
            udid = request.POST.get('UDID')
            user = User.objects.get(email=email)
            user = authenticate(username=user.username, password=password)
            if user is not None:
                if udid:
                    sessions = UsersApiSession.objects.filter(user=user)
                    if sessions.count() < settings.MAX_USERS_API_SESSIONS:
                        UsersApiSession.objects.get_or_create(user=user, udid=udid)
                    elif not sessions.filter(udid=udid):
                        return HttpResponseBadRequest(max_device_msg)
                try:
                    is_subscriber = user.subscriber.is_subscriber()
                    uuid = user.subscriber.id
                except Subscriber.DoesNotExist:
                    is_subscriber, uuid = False, None
            else:
                is_subscriber, uuid = False, None
            return render(
                request,
                'users_api.xml',
                {'response': str(is_subscriber).lower(), 'uuid': uuid},
                content_type='text/xml',
            )
        except KeyError:
            msg = u'Parameter missing'
        except User.DoesNotExist:
            msg = u'User does not exist'
        except MultipleObjectsReturned:
            msg = u'Multiple email in users'
            mail_managers(msg, email)
        return HttpResponseBadRequest(msg)
    raise Http404


@never_cache
@csrf_exempt
@require_POST
def email_check_api(request):
    """
    Takes contact_id and email from POST to check if there is any other user
    with the requested email. If it doesn't exist, it returns OK. Then, if it
    exists, it checks if it's the same user that should have that email.
    If it's not, it returns an error message.
    """
    try:

        email = request.POST['email']
        contact_id = int(request.POST['contact_id'])

        if not email or not contact_id or request.POST['ldsocial_api_key'] != settings.CRM_UPDATE_USER_API_KEY:
            return HttpResponseForbidden()

        subscriber_from_crm = Subscriber.objects.filter(contact_id=contact_id)

        if not subscriber_from_crm.exists():
            return HttpResponse('OK')

        user = User.objects.select_related('subscriber').get(email=email)

        user_contact_id = getattr(user.subscriber, 'contact_id', None)

        if (user_contact_id and user_contact_id != contact_id) or (user_contact_id is None):
            msg = u'Ya existe otro usuario en la web con ese email'
        else:
            msg = u'OK'

    except KeyError:
        msg = u'Parameter missing'
    except ValueError:
        msg = u'Wrong values'
    except User.DoesNotExist:
        msg = u'OK'
    except MultipleObjectsReturned:
        msg = u'Hay más de un usuario con ese email en la web'
    except Subscriber.DoesNotExist:
        msg = u'No hay suscriptor asociado al usuario web'

    return HttpResponse(msg)


@never_cache
@csrf_exempt
@require_POST
def user_comments_api(request):
    result = {u'error': None}
    try:
        email = request.POST['email']
        if not email or request.POST['ldsocial_api_key'] != settings.CRM_UPDATE_USER_API_KEY:
            return HttpResponseForbidden()
        talk_url = getattr(settings, 'TALK_URL', None)
        if talk_url:
            result.update(requests.post(
                talk_url + 'api/graphql',
                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN},
                data='{"query":"query user($id:ID!){user(id:$id){comments{nodes{story{url,metadata{title}},body}}}}",'
                     '"variables":{"id":%d},"operationName":"user"}' % User.objects.get(email__iexact=email).id
            ).json()['data']['user']['comments'])
        else:
            result[u'error'] = u'Sistema de comentarios temporalmente fuera de servicio'
    except KeyError:
        result[u'error'] = u'Parameter missing'
    except TypeError:
        result[u'error'] = u'No hay comentarios en la web asociados al usuario con ese email'
    except ValueError:
        result[u'error'] = u'Wrong values'
    except User.DoesNotExist:
        result[u'error'] = u'No existe usuario en la web con ese email'
    except MultipleObjectsReturned:
        result[u'error'] = u'Hay más de un usuario en la web con ese email'

    return HttpResponse(json.dumps(result), content_type="application/json")


@never_cache
@csrf_exempt
def custom_api(request):
    if request.method == 'POST':
        msg = u''
        try:
            operation = request.POST['operation']
            if not operation or request.POST['ldsocial_users_api_key'] != \
                    settings.LDSOCIAL_USERS_API_KEY:
                return HttpResponseForbidden()
            os.system(settings.LDSOCIAL_CUSTOM_API_CMD[operation])
        except KeyError:
            msg = u'Parameter or setting missing'
        return HttpResponseBadRequest(msg)
    raise Http404


@never_cache
@to_response
def referrals(request, hashed_id):
    decoded, user = Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id), None
    if decoded:
        sub = get_object_or_404(Subscriber, contact_id=int(decoded[0]))
        user = sub.user
    if not (decoded or user):
        raise Http404
    if request.method == 'POST':
        if user.suscripciones.all():
            subscription = user.suscripciones.all()[0]
        else:
            subscription = Subscription()
            subscription.first_name = user.first_name
            subscription.email = user.email
            subscription.subscriber = user
        subscription.friend1_name = request.POST['ref1_name']
        subscription.friend1_telephone = request.POST['ref1_tel']
        subscription.friend2_name = request.POST['ref2_name']
        subscription.friend2_telephone = request.POST['ref2_tel']
        subscription.friend3_name = request.POST['ref3_name']
        subscription.friend3_telephone = request.POST['ref3_tel']
        subscription.save()
        # se envía un correo alertando de los nuevos referidos
        subject = "Un usuario ha enviado referidos"
        rcv = settings.SUBSCRIPTION_EMAIL_TO
        from_mail = getattr(settings, 'DEFAULT_FROM_EMAIL')
        send_mail(
            subject,
            urljoin(settings.SITE_URL, subscription.get_absolute_url()),
            from_mail, rcv, fail_silently=True)
        return 'referrals_thankyou.html'
    else:
        return 'form_referral.html'


@never_cache
@to_response
def nlunsubscribe(request, publication_slug, hashed_id):
    publication = get_object_or_404(Publication, slug=publication_slug)
    try:
        subscriber_id = Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)[0]
        ctx = {
            'publication': publication,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        # subscriber_id can be 0 (test from /custom_email in allowed hosts)
        if subscriber_id:
            subscriber = get_object_or_404(Subscriber, id=subscriber_id)
            if not subscriber.user:
                raise Http404
            email = subscriber.user.email
            try:
                subscriber.newsletters.remove(publication)
            except Exception as e:
                # for some reason UpdateCrmEx does not work in test (Python ver?)
                ctx['error'] = e.displaymessage
        else:
            email = u'anonymous_user@localhost'
        ctx['email'] = email
        return 'nlunsubscribe.html', ctx
    except IndexError:
        raise Http404


@never_cache
@to_response
def nl_category_unsubscribe(request, category_slug, hashed_id):
    category = get_object_or_404(Category, slug=category_slug)
    try:
        subscriber_id = Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)[0]
        ctx = {
            'publication': category,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        # subscriber_id can be 0 (test from /custom_email in allowed hosts)
        if subscriber_id:
            subscriber = get_object_or_404(Subscriber, id=subscriber_id)
            if not subscriber.user:
                raise Http404
            email = subscriber.user.email
            try:
                subscriber.category_newsletters.remove(category)
            except Exception as e:
                # for some reason UpdateCrmEx does not work in test (Python ver?)
                ctx['error'] = e.displaymessage
        else:
            email = u'anonymous_user@localhost'
        ctx['email'] = email
        return 'nlunsubscribe.html', ctx
    except IndexError:
        raise Http404


@never_cache
@to_response
def disable_profile_property(request, property_id, hashed_id):
    """ Disables the profile bool property_id related to the subscriber matching the hashed_id argument given """
    try:
        subscriber = get_object_or_404(Subscriber, id=Hashids(settings.HASHIDS_SALT, 32).decode(hashed_id)[0])
        if not subscriber.user:
            raise Http404
        setattr(subscriber, property_id, False)
        ctx = {
            'property_name': {
                'allow_news': u'Novedades', 'allow_promotions': u'Promociones', 'allow_polls': u'Encuestas'
            }.get(property_id),
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        try:
            subscriber.save()
        except Exception as e:
            # for some reason UpdateCrmEx does not work in test (Python ver?)
            ctx['error'] = e.displaymessage
        return 'disable_profile_property.html', ctx
    except IndexError:
        raise Http404


@never_cache
@staff_member_required
def notification_preview(request, template, days=False):
    """
    TODO: template override by app is a "work in progress".
          When finished, this should be change and no extra setting should be required.
    """
    result = HttpResponseBadRequest()
    try:
        seller_fullname = request.GET.get('seller_fullname')
        ctx = {
            'logo_url': settings.HOMEV3_SECONDARY_LOGO,
            'days': days,
            'seller_fullname': u'Seller Fullname' if seller_fullname is None else seller_fullname,
        }
        dir_prefix = getattr(settings, 'THEDAILY_NOTIFICATIONS_TEMPLATE_PREFIX', '')
        result = render(request, dir_prefix + ('notifications/%s.html' % template), ctx)
    except TemplateDoesNotExist:
        if dir_prefix:
            try:
                result = render(request, 'notifications/%s.html' % template, ctx)
            except TemplateDoesNotExist:
                raise Http404
        else:
            raise Http404
    return result


@never_cache
@to_response
def phone_subscription(request):
    if request.POST:
        form = request.POST
        subject = u"Nueva solicitud de suscripción por teléfono"
        rcv = settings.SUBSCRIPTION_BY_PHONE_EMAIL_TO
        from_mail = getattr(settings, 'DEFAULT_FROM_EMAIL')
        text = u"Nombre: %s\nTeléfono: %s\nContactar: %s" % (
            form.get('full_name'), form.get('phone'), form.get('time'))
        send_mail(subject, text, from_mail, rcv, fail_silently=True)
        return 'phone_subscription_thankyou.html'
    elif request.session.get('notify_phone_subscription'):
        is_authenticated = request.user.is_authenticated()
        subscription = request.session.get('subscription')
        if is_authenticated:
            user = request.user
        else:
            user = subscription.subscriber
        user.subscriber.address = subscription.address
        user.subscriber.city = subscription.city
        user.subscriber.province = subscription.province
        user.subscriber.save()
        preferred_time = request.session.get('preferred_time')
        subject, body = telephone_subscription_msg(user, preferred_time)
        message = Message(
            text=body, mail_to=settings.SUBSCRIPTION_BY_PHONE_EMAIL_TO,
            mail_from=getattr(settings, 'DEFAULT_FROM_EMAIL'), subject=subject)
        message.send()
        request.session.pop('notify_phone_subscription')
        is_google = request.session.get('google-oauth2_state')
        display = not is_google and not is_authenticated
        return 'phone_subscription_thankyou.html', {'display': display, 'email': user.email}
    return 'phone_subscription_form.html'


# TODO post release: unhardcode subscription_type and preferred_time
def telephone_subscription_msg(user, preferred_time):
    """ Returns a tuple with (subject, body) """
    name = user.get_full_name() or user.subscriber.name
    subject = u'Nueva suscripción telefónica para %s' % (name)
    st = user.suscripciones.all()[0].subscription_type_prices
    subscription_type = st.all()[0].subscription_type
    st_text = '-'
    if subscription_type == u'DDIGM':
        st_text = 'digital ilimitada'
    elif subscription_type == u'DDIGMFS':
        st_text = 'digital recargada'
    elif subscription_type == u'PAPYDIM':
        st_text = 'papel lunes a viernes'
    elif subscription_type == u'PAPYLAS':
        st_text = 'papel lunes a sabado'
    elif subscription_type == u'LDFS':
        st_text = 'papel fin de semana'
    elif subscription_type == u'LENM':
        st_text = 'Revista Lento'
    pt_text = '-'
    if preferred_time == '1':
        pt_text = u'Cualquier hora (9:00 a 20:00)'
    elif preferred_time == '2':
        pt_text = u'En la mañana (9:00 a 12:00)'
    elif preferred_time == '3':
        pt_text = u'En la tarde (12:00 a 18:00)'
    elif preferred_time == '4':
        pt_text = u'En la tarde-noche (18:00 a 20:00)'
    body = (u'Nombre: %s\nTipo suscripción: %s\nEmail: %s\n'
            u'Teléfono: %s\nHorario preferido: %s\nDirección: %s\n'
            u'Ciudad: %s\nDepartamento: %s\n') % (
                name,
                st_text,
                user.email,
                user.subscriber.phone,
                pt_text, user.subscriber.address, user.subscriber.city,
                user.subscriber.province)
    return subject, body
