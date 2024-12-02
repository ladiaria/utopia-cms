# -*- coding: utf-8 -*-
from future import standard_library
from builtins import str
import os
from pydoc import locate
import json
import requests
import pymongo
from functools import wraps
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from urllib.request import pathname2url
from urllib.parse import urljoin, urlparse, urlencode
from uuid import uuid4
from smtplib import SMTPRecipientsRefused
from PIL import Image
from ga4mp import GtagMP

from social_django.models import UserSocialAuth
from emails.django import DjangoMessage as Message
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_api_key.permissions import HasAPIKey
from actstream import actions
from actstream.models import following
from favit.models import Favorite
from favit.utils import is_xhr
from django_amp_readerid.decorators import readerid_assoc
from django_amp_readerid.utils import amp_login_param, get_related_user

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import IntegrityError
from django.db.models import Count
from django.db.models.query_utils import Q
from django.db.models.deletion import Collector
from django.core.mail import send_mail, mail_admins, mail_managers
from django.urls import reverse, resolve
from django.core.exceptions import MultipleObjectsReturned
from django.http import (
    HttpResponseRedirect,
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseServerError,
    JsonResponse,
)
from django.forms import ValidationError
from django.forms.utils import ErrorList
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as do_login
from django.contrib.auth.models import User
from django.contrib.auth.views import LogoutView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.cache import never_cache, cache_control, cache_page
from django.template import Engine, TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from apps import mongo_db, bouncer_blocklisted
from libs.utils import set_amp_cors_headers, decode_hashid, crm_rest_api_kwargs
from libs.tokens.email_confirmation import get_signup_validation_url, send_validation_email
from utils.error_log import error_log
from decorators import render_response

from core.models import Publication, Category, Article, ArticleUrlHistory
from core.forms import feedback_allowed
from signupwall.middleware import (
    get_article_by_url_path, get_session_key, get_or_create_visitor, subscriber_access, number_to_words
)
from signupwall.templatetags.signupwall_tags import remaining_articles_content

from .models import (
    Subscriber,
    Subscription,
    SubscriptionPrices,
    UsersApiSession,
    OAuthState,
    MailtrainList,
    deletecrmuser,
)
from .forms import (
    __name__ as forms_module_name,
    LoginForm,
    SubscriberForm,
    SubscriberAddressForm,
    GoogleSigninForm,
    PasswordResetForm,
    WebSubscriptionForm,
    WebSubscriptionPromoCodeForm,
    WebSubscriptionCaptchaForm,
    WebSubscriptionPromoCodeCaptchaForm,
    SubscriptionForm,
    SubscriptionPromoCodeForm,
    SubscriptionCaptchaForm,
    SubscriptionPromoCodeCaptchaForm,
    PasswordResetRequestForm,
    PasswordChangeBaseForm,
    PasswordChangeForm,
    GoogleSignupForm,
    GoogleSignupAddressForm,
    SubscriberSignupForm,
    SubscriberSignupAddressForm,
    ConfirmEmailRequestForm,
    ProfileForm,
    ProfileExtraDataForm,
    UserForm,
    PhoneSubscriptionForm,
    phone_is_blocklisted,
    SUBSCRIPTION_PHONE_TIME_CHOICES,
    get_default_province,
)
from .utils import (
    get_or_create_user_profile,
    recent_following,
    add_default_newsletters,
    get_profile_newsletters_ordered,
    google_phone_next_page,
    product_checkout_template,
    qparamstr,
    collector_analysis,
    get_app_template,
    subscribe_log,
)
from .email_logic import limited_free_article_mail
from .exceptions import UpdateCrmEx, EmailValidationError
from .tasks import send_notification, notify_subscription, send_notification_message


standard_library.install_aliases()
to_response = render_response('thedaily/templates/')
delivery_err = "Error interno, intentá de nuevo más tarde."
site_name = Site.objects.get_current().name


def no_op_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# Endpoints must be decorated with no auth classes if the deployment is under http basic auth, when no basic auth is
# set, the decorator is no_op_decorator, which does nothing and let the endpoint acts as if it was not decorated.
api_view_auth_decorator = (
    authentication_classes([]) if getattr(settings, 'ENV_HTTP_BASIC_AUTH', False) else no_op_decorator
)


def notify_new_subscription(subscription_url, extra_subject=''):
    subject = settings.SUBSCRIPTION_EMAIL_SUBJECT + extra_subject
    rcv = settings.SUBSCRIPTION_EMAIL_TO
    from_mail = getattr(settings, 'DEFAULT_FROM_EMAIL')
    send_mail(subject, settings.SITE_URL + subscription_url, from_mail, rcv, fail_silently=True)


def no_captcha(request):
    # captcha when enabled and not ignored => nocaptcha = not(enabled and not ignored) = not enabled or ignored
    # TODO: do not asume CF for getting the country (do it like signupwall gets the ip_address)
    return not getattr(settings, 'THEDAILY_SUBSCRIPTION_CAPTCHA_ENABLED', True) or request.headers.get(
        'cf-ipcountry', settings.THEDAILY_SUBSCRIPTION_CAPTCHA_DEFAULT_COUNTRY
    ) in getattr(settings, 'THEDAILY_SUBSCRIPTION_CAPTCHA_COUNTRIES_IGNORED', [])


def get_formclass(request, formclass_prefix):
    return locate(
        "%s.%s%s%s" % (forms_module_name, formclass_prefix, "" if no_captcha(request) else "Captcha", "Form")
    )


def hard_paywall_template():
    template_dir = getattr(settings, 'CORE_ARTICLE_DETAIL_TEMPLATE_DIR', "")
    template = "hard_paywall.html"
    template_engine, template_try = Engine.get_default(), os.path.join(template_dir, template)
    try:
        template_engine.get_template(template_try)
    except TemplateDoesNotExist:
        pass
    else:
        template = template_try
    return template


@never_cache
@require_http_methods(["GET"])
def mailtrain_lists(request):
    """
    Calls CRM api to retrieve the lists that this auth user has subscribed to.
    """
    user = request.user
    try:
        assert user.email and user.email not in bouncer_blocklisted
        api_uri, api_key = settings.CRM_API_BASE_URI, getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
        assert api_uri and api_key, "CRM api not configured"
        r = requests.post(api_uri + "mailtrain_lists/", **crm_rest_api_kwargs(api_key, {"email": user.email}))
        r.raise_for_status()
    except Exception as exc:
        if settings.DEBUG:
            print("ERROR: mailtrain_lists exception: %s" % exc)
        return HttpResponseBadRequest()
    else:
        return JsonResponse(r.json())


@never_cache
@csrf_exempt
def nl_auth_subscribe(request, nltype, nlslug):
    """
    nl subscription or unsubscription for authenticated users (by ajax or POST)
    """
    from_amp = request.GET.get("__amp_source_origin")
    user = get_related_user(request) if from_amp else request.user
    if not user.is_anonymous and (request.method == 'POST' or is_xhr(request)):
        nl_subscribe_activated = getattr(request, request.method, {}).get("nl_subscribe", "true") == "true"
        try:
            if nl_subscribe_activated:
                assert user.email and user.email not in bouncer_blocklisted
            if nltype in "pc":
                # publications or categories
                nlobj = get_object_or_404(Publication if nltype == "p" else Category, slug=nlslug, has_newsletter=True)
                nl_field = ("" if nltype == "p" else "category_") + "newsletters"
                getattr(getattr(user.subscriber, nl_field), "add" if nl_subscribe_activated else "remove")(nlobj)
            else:
                # Mailtrain list (nltype='m' the only possible value left in the url pattern deffinition)
                api_uri, api_key = settings.CRM_API_BASE_URI, getattr(settings, "CRM_UPDATE_USER_API_KEY", None)
                assert api_uri and api_key, "CRM api not configured"
                r = getattr(requests, "post" if nl_subscribe_activated else "delete")(
                    api_uri + "mailtrain_list_subscription/",
                    **crm_rest_api_kwargs(api_key, {"email": user.email, "list_id": nlslug}),
                )
                r.raise_for_status()
        except Exception as exc:
            # TODO: check (p/c cases only) when UpdateCrmEx raised in test (Python ver?)
            if settings.DEBUG:
                print("ERROR: nl_auth_subscribe exception: %s" % exc)
            return HttpResponseBadRequest()
        return set_amp_cors_headers(request, JsonResponse({})) if from_amp else HttpResponse()
    else:
        return HttpResponseForbidden()


@never_cache
@csrf_exempt
def communication_subscribe(request, com_type):
    """ communications subscription or unsubscription for authenticated users (by ajax or POST) """
    from_amp = request.GET.get("__amp_source_origin")
    user = get_related_user(request) if from_amp else request.user
    if not user.is_anonymous and (request.method == 'POST' or is_xhr(request)):
        target_field = com_type  # assuming the field here
        try:
            subscribe_activated = getattr(request, request.method, {}).get("com_subscribe", "true") == "true"
            if getattr(user.subscriber, target_field) != subscribe_activated:
                if subscribe_activated:
                    assert user.email and user.email not in bouncer_blocklisted
                setattr(user.subscriber, target_field, subscribe_activated)
                user.subscriber.save()
        except Exception:
            # TODO: check when UpdateCrmEx raised in test (Python ver?)
            return HttpResponseBadRequest()
        return set_amp_cors_headers(request, JsonResponse({})) if from_amp else HttpResponse()
    else:
        return HttpResponseForbidden()


@never_cache
def nl_subscribe(request, publication_slug=None, hashed_id=None):
    if publication_slug and hashed_id:
        # "1-click" subscription
        publication = get_object_or_404(Publication, slug=publication_slug, has_newsletter=True)
        ctx = {
            'publication': publication,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        decoded = decode_hashid(hashed_id)
        if decoded:
            subscriber = get_object_or_404(Subscriber, id=decoded[0])
            if (not subscriber.user or not subscriber.user.email or subscriber.user.email in bouncer_blocklisted):
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
    if request.user.is_authenticated:
        return HttpResponseRedirect(next_page)
    else:
        request.session['next'] = next_page
        return HttpResponseRedirect(
            reverse('account-login') + getattr(settings, "THEDAILY_NL_SUBSCRIBE_LOGIN_URL_PLUS", "")
        )


@never_cache
@to_response
def nl_category_subscribe(request, slug, hashed_id=None):
    """
    if hashed id is given, this view will do similar things than nl_subscribe with a category instead of a publication
    """
    if hashed_id:
        # "1-click" subscription
        category = get_object_or_404(Category, slug=slug, has_newsletter=True)
        ctx = {
            'category': category,
            'logo': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO', settings.HOMEV3_LOGO),
            'logo_width': getattr(settings, 'THEDAILY_NL_SUBSCRIPTIONS_LOGO_WIDTH', ''),
        }
        decoded = decode_hashid(hashed_id)
        if decoded:
            subscriber = get_object_or_404(Subscriber, id=decoded[0])
            if (not subscriber.user or not subscriber.user.email or subscriber.user.email in bouncer_blocklisted):
                raise Http404
            try:
                subscriber.category_newsletters.add(category)
            except Exception as e:
                # for some reason UpdateCrmEx does not work in test (Python ver?)
                ctx['error'] = e.displaymessage
            else:
                next_page = request.GET.get('next')
                if next_page:
                    return HttpResponseRedirect(next_page)
            return 'nlsubscribe.html', ctx
        else:
            raise Http404
    else:
        # next page redirection
        next_page = reverse('edit-profile') + '#category-newsletter-' + slug
        if request.user.is_authenticated:
            return HttpResponseRedirect(next_page)
        else:
            request.session['next'] = next_page
            return HttpResponseRedirect(reverse('account-login'))


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@csrf_protect
@ensure_csrf_cookie
@readerid_assoc
def login(request, product_slug=None, product_variant=None):
    # next_page value got here will be available in session (TODO: explain how this happen)
    return_param = amp_login_param(request, 'return')
    if return_param:
        # redirect email/google AMP logins (google social auth do not redirect to external urls)
        next_page = "%s?url=%s" % (reverse("amp-readerid:redirect"), return_param)
    else:
        next_page = request.GET.get('next', request.session.get('next', '/'))

    if request.user.is_authenticated:
        request.session.pop('next', None)  # if not removed, google signin from AMP will redirect in infinite loop
        request.session.modified = True
        return HttpResponseRedirect(next_page)

    article_id, login_formclass, response, login_error, context = None, LoginForm, None, None, {}
    default_planslug = settings.THEDAILY_SUBSCRIPTION_TYPE_DEFAULT
    if default_planslug:
        context["default_subscription_type"] = SubscriptionPrices.objects.get(subscription_type=default_planslug)

    market_next_page, market_next_qparams = None, {}
    if product_slug:
        template = product_checkout_template(product_slug)
        if product_variant:
            context["product_variant"] = True
            market_next_qparams["variant"] = 1
        market_next_page = reverse("product-checkout", kwargs={"product_slug": product_slug})
        next_page = market_next_page + qparamstr(market_next_qparams)
        if "prelogin" not in request.POST:
            login_formclass = get_formclass(request, "PreLogin")
        context.update({"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS, "product_slug": product_slug})
    else:
        article_id = request.GET.get('article')
        template = get_app_template('login.html')

    if article_id and settings.SIGNUPWALL_RISE_REDIRECT:
        try:
            article = Article.objects.get(id=article_id)
        except (ValueError, Article.DoesNotExist):
            pass
        else:
            next_page = article.get_absolute_url()
            if "prelogin" not in request.POST:
                login_formclass = get_formclass(request, "PreLogin")
            template = hard_paywall_template()
            context.update({"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS, "article": article})

    context.update({'next_page': next_page, 'next': pathname2url(next_page.encode('utf8'))})

    initial, name_or_mail = {}, request.GET.get('name_or_mail')
    if name_or_mail:
        initial['name_or_mail'] = name_or_mail
    if request.session.get("terms_and_conds_accepted"):
        initial["terms_and_conds_accepted"] = True

    if request.method == 'POST':
        login_form = login_formclass(request.POST)
        if login_form.is_valid():
            password = request.POST.get('password')  # Taken directly from POST (not all form classes have password)
            if password:
                user = authenticate(username=login_form.username, password=password)
                if user is not None:
                    if user.is_active:
                        do_login(request, user)
                        request.session.pop('next', None)
                        # also remove possible unfinished google sign-in information from the session, if not,
                        # the social pipelines will try to finish and an error will be raised regarding to the conflict
                        # between the user that just logged-in and the user that has this "unfinished" google signin
                        # attempt.
                        request.session.pop("google-oauth2_state", None)
                        request.session.modified = True
                        # terms and conds acceptance save
                        if (
                            request.session.get("terms_and_conds_accepted")
                            and not user.subscriber.terms_and_conds_accepted
                        ):
                            user.subscriber.terms_and_conds_accepted = True
                            try:
                                user.subscriber.save()
                            except Exception:
                                # do not break login if an error raised during the subscriber object save
                                pass
                        response = HttpResponseRedirect(next_page)
                    else:
                        response = HttpResponseRedirect(reverse('account-confirm_email'))
                else:
                    login_error = 'Usuario y/o contraseña incorrectos.'
            else:
                request.session["terms_and_conds_accepted"] = True
                request.session.modified = True
                qparams = market_next_qparams if product_slug else {"article": article_id}
                qparams["email"] = login_form.data.get("email")
                response = HttpResponseRedirect(
                    (market_next_page if product_slug else reverse('account-signup')) + qparamstr(qparams)
                )
        else:
            email = login_form.data.get('name_or_mail')
            if email:
                # alert admins if is a user with duplicated email. TODO: can be improved using error_code
                if User.objects.filter(email=email).count() > 1:
                    mail_managers("Multiple email in users", email)
            elif product_slug or article_id:
                # applies only to "pre-login"
                # return a normal login form only if the error is in email field and has INVALID code
                # if more errors, remove the error in email field only if it has INVALID code
                err_data = login_form.errors.as_data()
                err_datalen = len(err_data)
                if err_datalen >= 1:
                    err_data_email = err_data.get("email")
                    if err_data_email and err_data_email[0].code != EmailValidationError.INVALID:
                        if err_datalen == 1:
                            request.session["terms_and_conds_accepted"] = True
                            initial["name_or_mail"] = login_form.data.get('email')
                            login_form = LoginForm(initial=initial)
                        else:
                            login_form.errors.pop("email")
        if login_error:
            if '__all__' in login_form.errors:
                login_form.errors['__all__'].append(login_error)
            else:
                login_form.errors['__all__'] = [login_error]
    else:
        login_form = login_formclass(initial=initial)

    if not response:
        # update next page in session for cases when google sign-in option is used
        request.session["next"] = next_page
        context['login_form'] = login_form
        response = render(request, template, context)

    response['Expires'], response['Pragma'] = 0, 'no-cache'
    return response


@never_cache
def signup(request):
    template, article_id, context = get_app_template('signup.html'), request.GET.get("article"), {}

    if article_id and settings.SIGNUPWALL_RISE_REDIRECT:
        try:
            article = Article.objects.get(id=article_id)
        except (ValueError, Article.DoesNotExist):
            article_id = None
        else:
            if request.user.is_authenticated:
                return HttpResponseRedirect(article.get_absolute_url())
            context["article"] = article
            template = hard_paywall_template()

    next_page = request.GET.get('next')
    if request.user.is_authenticated:
        return HttpResponseRedirect(next_page or reverse("edit-profile"))

    signup_form_class = get_formclass(request, "Signup")
    if request.method == 'POST':
        post = request.POST.copy()
        signup_form = signup_form_class(post)
        if signup_form.is_valid():
            user = None
            try:
                user = signup_form.create_user()
                add_default_newsletters(user.subscriber)  # TODO: better call this after email confirmation success
                # TODO: check if request is needed
                # TODO: notifications/signup.html is also used for this purpose (2 templates to the same thing?)
                was_sent = send_validation_email(
                    'Verificá tu cuenta',
                    user,
                    'notifications/account_signup.html',
                    get_signup_validation_url,
                    {'request': request},
                )
                if not was_sent:
                    raise Exception("El email de verificación para el usuario %s no pudo ser enviado." % user)
                next_page = signup_form.cleaned_data.get('next_page')
                if next_page:
                    return HttpResponseRedirect(next_page)
                else:
                    context['signup_mail'] = user.email
                    return render(request, get_app_template("welcome.html"), context)
            except Exception as exc:
                msg = "Error al enviar email de verificación para el usuario: %s." % user
                error_log(msg + " Detalle: {}".format(str(exc)))
                if user:
                    email_to_delete = user.email
                    user.delete()
                    deletecrmuser(email_to_delete)

                signup_form.add_error(None, msg)
    else:
        initial = {}
        if next_page:
            initial['next_page'] = next_page
        email = request.GET.get('email')
        if email:
            initial['email'] = email
        if request.session.get("terms_and_conds_accepted"):
            initial["terms_and_conds_accepted"] = True
        signup_form = signup_form_class(initial=initial)
        if article_id:
            signup_form.helper.form_action = reverse("account-signup") + "?article=%s" % article_id

    context.update(
        {
            'signup_form': signup_form,
            'errors': signup_form.errors.get('__all__'),
            "signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS,
        }
    )
    return render(request, template, context)


@never_cache
def welcome(request, signup=False, subscribed=False):
    """
    welcome page, will be rendered only if welcome in session has a value, otherwise will be redirected to home.
    """
    if request.session.get('welcome'):
        request.session.pop('welcome')
        return render(
            request,
            get_app_template("welcome.html"),
            {'signup': signup, 'subscribed': subscribed, "signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS},
        )
    else:
        return HttpResponseRedirect(reverse('home'))


@never_cache
@to_response
@require_http_methods(["GET", "POST"])
def google_phone(request):
    """
    Ask for "phone" and terms and conditions acceptance when using google-sign-in to create an account
    TODO: check that for AMP the next TODO happens only in case of new accounts
    TODO: for new accounts, when coming from AMP or hard_paywall:
      The landing "welcome" page should be different because the expected behaviour is to go back to the article page
      that originated the login, ask UX team for feedback on what to do, one option is to show the welcome page and
      after some seconds redirect to the "next" page (for AMP is the google page that closes the window).
    """
    # if planslug in session this came from a new subscription attemp and we should continue it
    subscribe_log(request, 'google_phone begin')
    planslug, is_new = request.session.get('planslug'), request.GET.get('is_new') == '1'
    if planslug:
        request.session.pop('planslug')
        if is_new:
            # default category newsletters are not added here because some subscriptions may not add the default
            # category newsletters. TODO: Add a M2M relation from subscriptionprices(planslug) to Category
            pass
        return HttpResponseRedirect(reverse('subscribe', kwargs={'planslug': planslug}))
    try:
        oas = OAuthState.objects.get(state=request.session.get('google-oauth2_state'))
    except OAuthState.DoesNotExist:
        raise Http404

    profile, ctx = get_or_create_user_profile(oas.user), {"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS}
    next_page = google_phone_next_page(request, is_new)
    assume_tnc_accepted = getattr(settings, 'THEDAILY_TERMS_AND_CONDITIONS_ACCEPTED_IN_GOOGLE', True)
    form_kwargs = {"instance": profile, "is_new": is_new, "assume_tnc_accepted": assume_tnc_accepted}
    initial = {"next_page": next_page} if next_page else {}

    if assume_tnc_accepted:
        # By default we asume that the T&C are accepted in Google flows.
        initial["terms_and_conds_accepted"] = True
        if not profile.terms_and_conds_accepted:
            profile.terms_and_conds_accepted = True
            try:
                profile.save()
            except Exception as exc:
                subscribe_log(request, 'google_phone error saving T&C accepted for user %d: %s' % (oas.user.id, exc))
    elif request.session.get("terms_and_conds_accepted"):
        initial["terms_and_conds_accepted"] = True
    if initial:
        form_kwargs["initial"] = initial

    if request.method == 'POST':
        google_signin_form = GoogleSigninForm(request.POST, **form_kwargs)
        if google_signin_form.is_valid():
            google_signin_form.save()
            if is_new:
                request.session['welcome'] = True
                try:
                    send_notification(oas.user, 'notifications/signup.html', '¡Te damos la bienvenida!', ctx)
                except Exception as exc:
                    # fail silently in case of error when sending the email, only log or debug
                    err_msg = "welcome email message send error for user %d: %s" % (oas.user.id, exc)
                    subscribe_log(request, 'google_phone' + err_msg)
                    if settings.DEBUG:
                        print("DEBUG: " + err_msg)
            request.session.modified = True  # TODO: see comments in portal.libs.social_auth_pipeline
            redirect_kwargs = {'backend': 'google-oauth2'}
            # if the user didn't complete the phone, we tell pipeline to not redirect here again through oas obj
            if google_signin_form.instance.phone:
                oas.delete()
            else:
                oas.phone_submitted_blank = True
                oas.save()
            return HttpResponseRedirect(
                reverse('social:begin', kwargs=redirect_kwargs) + (("?next=" + next_page) if next_page else "")
            )
    else:
        # if is a new user add the default category newsletters (reached only from "free" subscriptions)
        if is_new:
            add_default_newsletters(profile)
        elif profile.terms_and_conds_accepted:
            # can be redirected now if T&C
            return HttpResponseRedirect(next_page or reverse('home'))
        google_signin_form = GoogleSigninForm(**form_kwargs)
    subscribe_log(request, 'google_phone end')
    ctx.update({'google_signin_form': google_signin_form, "is_new": is_new})
    return 'google_signup.html', ctx


class SubscriptionPricesListView(ListView):
    model = SubscriptionPrices
    template_name = get_app_template("subscribe-landing.html")


@never_cache
def subscribe(request, planslug, category_slug=None):
    """
    This view handles the plan subscriptions.
    """
    custom_module, article_id = getattr(settings, 'THEDAILY_VIEWS_CUSTOM_MODULE', None), request.GET.get("article")

    context, article = {"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS}, None
    template = get_app_template("subscribe.html")
    if article_id and settings.SIGNUPWALL_RISE_REDIRECT:
        try:
            article = Article.objects.get(id=article_id)
        except (ValueError, Article.DoesNotExist):
            article_id = None
        else:
            context["article"] = article
            template = hard_paywall_template()

    if custom_module:
        subscribe_custom = __import__(custom_module, fromlist=['subscribe']).subscribe
        return subscribe_custom(request, planslug, category_slug, article_id)
    else:
        # category_slug is allowed only if custom_module is defined
        if category_slug:
            raise Http404
        user, auth, qparams = request.user, request.GET.get('auth'), {}
        user_is_auth = user.is_authenticated
        if article_id:
            if not user_is_auth:
                return HttpResponseRedirect(reverse("account-login") + "?article=%s" % article_id)
            qparams["article"] = article_id
        qparams_str = urlencode(qparams)
        qparams_str_wqmark = (('?%s' % qparams_str) if qparams_str else '')
        if auth:
            request.session['planslug'] = planslug
            request.session.modified = True  # TODO: see comments in portal.libs.social_auth_pipeline
            return HttpResponseRedirect(
                '%s?next=%s%s'
                % (
                    reverse("social:begin", kwargs={'backend': auth}),
                    reverse('subscribe', kwargs={'planslug': planslug}),
                    qparams_str_wqmark,
                )
            )

        oauth2_state = request.session.get('google-oauth2_state')
        if oauth2_state:
            try:
                oas = OAuthState.objects.get(state=oauth2_state)
            except OAuthState.DoesNotExist:
                request.session.pop('google-oauth2_state')
                return HttpResponseRedirect(request.path + qparams_str_wqmark)
            else:
                user = oas.user

        product = get_object_or_404(Publication, slug=settings.DEFAULT_PUB)
        # TODO post release: Usage guide should describe when 404 is raised here
        subscription_price = get_object_or_404(SubscriptionPrices, subscription_type=planslug)
        oauth2_button, subscription_in_process, default_province = True, False, get_default_province()
        online = subscription_price.ga_category == 'D'

        if user_is_auth:
            subscriber = user.subscriber
            is_subscriber = subscriber.is_subscriber()

            if is_subscriber and article:
                return HttpResponseRedirect(article.get_absolute_url())

            if oauth2_state:
                oauth2_button = False
                profile = get_or_create_user_profile(user)
                if online:
                    subscriber_form = GoogleSignupForm(instance=profile)
                else:
                    if not profile.province and default_province:
                        profile.province = default_province
                    subscriber_form = GoogleSignupAddressForm(instance=profile)
            else:
                initial = {
                    'email': user.email, 'first_name': user.first_name.strip() or subscriber.name or user.username
                }
                if subscriber.phone:
                    initial['phone'] = subscriber.phone

                if online:
                    subscriber_form = SubscriberForm(initial=initial)
                else:
                    initial.update({'address': subscriber.address, 'city': subscriber.city})
                    if subscriber.province:
                        initial['province'] = subscriber.province
                    subscriber_form = SubscriberAddressForm(initial=initial)

                # do not show oauth button if this user is already associated
                if user.social_auth.filter(provider='google-oauth2').exists():
                    oauth2_button = False

        else:
            # not authenticated
            is_subscriber = False
            if oauth2_state:
                oauth2_button = False
                profile = get_or_create_user_profile(user)
                if online:
                    subscriber_form = GoogleSignupForm(instance=profile)
                else:
                    if not profile.province and default_province:
                        profile.province = default_province
                    subscriber_form = GoogleSignupAddressForm(instance=profile)
            else:
                subscriber_form = (
                    SubscriberSignupForm if online else SubscriberSignupAddressForm
                )(initial={'next_page': request.path})
            # check session and if a new user was created, encourage login
            if request.method == 'GET':
                subscription = request.session.get('subscription')
                subscription_in_process = subscription and subscription.subscriber

        PROMOCODE_ENABLED, nocaptcha = getattr(settings, 'THEDAILY_PROMOCODE_ENABLED', False), no_captcha(request)

        subscription_formclass = (
            (WebSubscriptionPromoCodeForm if PROMOCODE_ENABLED else WebSubscriptionForm)
            if nocaptcha else (
                WebSubscriptionPromoCodeCaptchaForm if PROMOCODE_ENABLED else WebSubscriptionCaptchaForm
            )
        ) if online else (
            (SubscriptionPromoCodeForm if PROMOCODE_ENABLED else SubscriptionForm)
            if nocaptcha else (SubscriptionPromoCodeCaptchaForm if PROMOCODE_ENABLED else SubscriptionCaptchaForm)
        )
        # a last transformation pipeline step for the subscription form (can be completely overrided by settings)
        subscription_formclass_custom = getattr(settings, 'THEDAILY_SUBSCRIPTION_FORMCLASS', None)
        if subscription_formclass_custom:
            subscription_formclass = locate(subscription_formclass_custom)

        initial = {
            'subscription_type_prices': planslug,
            "terms_and_conds_accepted": (
                subscriber.terms_and_conds_accepted
                if user_is_auth else request.session.get("terms_and_conds_accepted", False)
            ),
        }
        subscription_form = subscription_formclass(initial=initial)

        if not is_subscriber and request.method == 'POST':
            post = request.POST.copy()

            if user_is_auth:
                subscription = request.session.get('subscription')
                subscription_type = request.session.get('subscription_type')
                if subscription and subscription_type:
                    # delete possible in-process subscription
                    # TODO: delete only matched against a new setting
                    subscription.subscription_type_prices.remove(subscription_type)

                # if for any reason, a google state is still "unfinished" for an authenticated user, do the same
                # things that would be done in our next "elif" condition (bind the form). If not, the form save
                # that will be called will create a new Subscriber instead of update the existing one.
                # Note that to avoid security issues, the login view removes this unfinished google signin
                # information from the session if a "new" login is made.
                # Also, instance here is the user logged-in (no doubt on that), this is useful in case that for any
                # reason, the Subscriber object has a blank phone, the form will submit a phone value and then
                # the form.save call must save the field in the Subscriber obj.
                subscriber_form_v = (
                    GoogleSignupForm if online else GoogleSignupAddressForm
                ) if oauth2_state else (
                    SubscriberForm if online else SubscriberAddressForm
                )(post, instance=get_or_create_user_profile(request.user))
            elif oauth2_state:
                subscriber_form_v = (
                    GoogleSignupForm if online else GoogleSignupAddressForm
                )(post, instance=get_or_create_user_profile(user))
            else:
                subscriber_form_v = (SubscriberSignupForm if online else SubscriberSignupAddressForm)(post)

            # TODO: commented code is the old one, remove it after testing
            # subscription_form_v = (
            #     subscription_formclass(post, initial=initial) if online else (
            #         SubscriptionForm if nocaptcha else SubscriptionCaptchaForm
            #     )(post)
            # )
            subscription_form_v = subscription_formclass(post, initial=initial)

            if subscriber_form_v.is_valid(planslug) and subscription_form_v.is_valid():
                # TODO: (DRY_start) can be moved to a function (one of our custom apps does near exactly the same,
                #       not exactly exactly because for example, the "category_slug" thing is not yet implemented here)
                # TODO: use form.cleaned_data instead of post.get
                email = user.email if user_is_auth else (
                    subscriber_form_v.cleaned_data['email'] if user.is_anonymous else user.username
                )
                if not email:
                    # TODO: decide what to do in this case
                    pass
                subscriptions = Subscription.objects.filter(email=email)

                if subscriptions:
                    try:
                        subscription = subscriptions.get(subscriber=None)
                    except Subscription.DoesNotExist:
                        try:
                            if user_is_auth:
                                subscription = subscriptions.get(subscriber=user)
                            else:
                                subscription = subscriptions.get(subscriber__email=email)
                        except Subscription.DoesNotExist:
                            # TODO: notify managers/admin "Data inconsistency in subscriptions"
                            subscription = Subscription.objects.create(email=email)
                        except Subscription.MultipleObjectsReturned:
                            subscription = subscriptions.latest()
                    except Subscription.MultipleObjectsReturned:
                        subscription = subscriptions.latest()
                else:
                    subscription = Subscription.objects.create(email=email)

                subscription.subscription_type_prices.add(subscription_price)

                first_name = subscriber_form_v.cleaned_data.get("first_name")
                if oauth2_state:
                    subscriber_form_v.save()
                    if not subscription.first_name:
                        # take first_name from oas (it can be not present due a previous not finished google signup)
                        subscription.first_name = oas.fullname
                    subscription.telephone = post.get('phone')
                else:
                    subscription.first_name = first_name
                    subscription.telephone = post['phone']

                for post_key in ('address', 'city', 'province', 'promo_code'):
                    post_value = post.get(post_key)
                    if post_value:
                        setattr(subscription, post_key, post_value)

                user_created = False
                if user_is_auth:
                    # possible user new first name should be updated
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                        user.save()
                    # terms and conds have been accepted because the form is valid
                    if (
                        settings.THEDAILY_TERMS_AND_CONDITIONS_FLATPAGE_ID
                        and not subscriber.terms_and_conds_accepted
                    ):
                        subscriber.terms_and_conds_accepted = True
                        subscriber.save()
                    subscription.subscriber = user
                    subscription.save()
                else:
                    if oauth2_state:
                        # succesfull google sigin usage (form saved lines above), we can remove the oas object (just
                        # like the google_phone view does after a succesfull POST)
                        subscription.subscriber = user
                        subscription.save()
                        oas.delete()
                    else:
                        user, user_created = subscriber_form_v.signup_form.create_user(), True
                        try:
                            was_sent = send_validation_email(
                                f'Verificá tu cuenta de {site_name}',
                                user,
                                'notifications/account_signup_subscribed.html',
                                get_signup_validation_url,
                            )
                            if not was_sent:
                                raise Exception("Error al enviar email de verificación para el usuario %s" % user)
                        except Exception as exc:
                            msg = str(exc)
                            error_log(msg)
                            subscription.delete()
                            errors = subscriber_form_v._errors.setdefault("email", ErrorList())
                            errors.append(
                                (
                                    'Datos de suscripción incorrectos, '
                                    '<a class="ld-link-low" href="%s">cierre sesión</a>' % reverse("logout")
                                    + " e intente nuevamente utilizando otra dirección de " + _("email")
                                ) if isinstance(exc, IntegrityError) else (
                                    'No se pudo enviar el email de verificación al crear tu cuenta, '
                                    + (
                                        '¿lo escribiste correctamente?'
                                        if isinstance(exc, SMTPRecipientsRefused)
                                        else 'intentá <a class="ld-link-low" href="%s">pedirlo nuevamente</a>.'
                                        % reverse('account-confirm_email')
                                    )
                                )
                            )
                            context.update(
                                {'subscriber_form': subscriber_form_v, 'subscription_form': subscription_form_v}
                            )
                            return render(request, template, context)
                        else:
                            subscription.subscriber = user
                            subscription.save()

                # we should save the subscription and its type in the session
                request.session['subscription'] = subscription
                request.session['subscription_type'] = subscription_price
                # TODO (DRY_end)

                if oauth2_state:
                    if online:
                        social_next = reverse("online-subscription")  # TODO: this pattern must be mapped
                    else:
                        request.session['notify_phone_subscription'] = True
                        request.session['preferred_time'] = post.get('preferred_time')
                        social_next = reverse('phone-subscription')
                    request.session.modified = True  # TODO: see comments in portal.libs.social_auth_pipeline
                    return HttpResponseRedirect(
                        '%s?next=%s' % (reverse('social:begin', kwargs={'backend': 'google-oauth2'}), social_next)
                    )
                else:
                    if online:
                        context.update(
                            # TODO: try save the subscription form, then last entry can be removed (==form.instance)
                            {
                                "subscription_price": subscription_price,
                                "planslug": planslug,
                                "user_created": user_created,
                                'subscriber_form': subscriber_form_v,
                                'subscription_form': subscription_form_v,
                                'subscription': subscription,
                            }
                        )
                        try:
                            # TODO: more customization is needed on how to use the next_page
                            view_func = resolve(subscription_form_v.next_page).match.func
                            return view_func(request, planslug, context)
                        except AttributeError:
                            pass
                        return render(request, get_app_template("online_subscription.html"), context)
                    else:
                        request.session['notify_phone_subscription'] = True
                        request.session['preferred_time'] = post.get('preferred_time')
                        return HttpResponseRedirect(reverse('phone-subscription'))

            else:
                error_msg = "\n".join(
                    f'{type(form)} errors: {form.errors}' for form in (subscriber_form_v, subscription_form_v)
                )
                if settings.DEBUG:
                    print(error_msg)
                context.update(
                    {
                        'subscriber_form': subscriber_form_v,
                        'subscription_form': subscription_form_v,
                        'oauth2_button': oauth2_button,
                        'planslug': planslug,
                        'subscription_price': subscription_price,
                    }
                )
                return render(request, template, context)

        context.update(
            {
                'subscriber_form': subscriber_form,
                'oauth2_button': oauth2_button,
                'subscription_form': subscription_form,
                'is_already_subscribed': is_subscriber,
                'product': product,
                'planslug': planslug,
                'subscription_price': SubscriptionPrices.objects.get(subscription_type=planslug),
                'subscription_in_process': subscription_in_process,
            }
        )
        return render(request, template, context)


def hash_validate(user_id, hash):
    user = get_object_or_404(User, id=user_id)
    if not default_token_generator.check_token(user, hash):
        raise Http404('Invalid token.')
    return user


def get_password_validation_url(user):
    return reverse(
        'account-password_change-hash',
        kwargs={'user_id': str(user.id), 'hash': default_token_generator.make_token(user)},
    )


@never_cache
@to_response
def complete_signup(request, user_id, hash):
    """
    This view is executed when the user clicks account activation button in his/her email.
    """
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
        mail_admins('New user', '%i - %s' % (user.id, user.get_full_name()))

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
            send_default_welcome = False
            notify_subscription(user, subscription_type)

    if send_default_welcome:
        send_notification(
            user,
            'notifications/signup.html',
            'Tu cuenta gratuita está activa',
            {"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS},
        )

    request.session['welcome'] = 'account-welcome' + ('-s' if is_subscriber_any else '')

    if not user.has_usable_password():
        # email is valid, so, generate pass token and redirect to change form
        return HttpResponseRedirect(get_password_validation_url(user))

    if is_subscriber_any:
        return HttpResponseRedirect(reverse('account-welcome-s'))
    else:
        return HttpResponseRedirect(reverse('account-welcome'))


@never_cache
def password_reset(request, user_id=None, hash=None):
    if user_id and hash:
        return password_change(request, user_id, hash)
    ctx = {}
    if request.method == 'POST':
        # TODO: we should also check for telephone number as google_auth
        post = request.POST.copy()
        reset_form = PasswordResetRequestForm(post)
        if reset_form.is_valid():
            try:
                user = reset_form.cleaned_data["user"]
                if user.is_active:
                    send_validation_email(
                        'Recuperación de contraseña',
                        user,
                        get_app_template('notifications/password_reset_body.html'),
                        get_password_validation_url,
                    )
                else:
                    is_subscriber_any = hasattr(user, 'subscriber') and user.subscriber.is_subscriber_any()
                    notification_template = get_app_template(
                        'notifications/account_signup%s.html' % ('_subscribed' if is_subscriber_any else '')
                    )
                    send_validation_email(
                        f'Verificá tu cuenta de {site_name}', user, notification_template, get_signup_validation_url
                    )
            except Exception as exc:
                error_log(delivery_err + " Detalle: {}".format(str(exc)))
                ctx['error'] = delivery_err
        ctx["action_content_template"] = get_app_template("password_reset_action_content.html")
    else:
        ctx['form'] = PasswordResetRequestForm()
    return render(request, get_app_template('password_reset.html'), ctx)


@never_cache
def confirm_email(request):
    if request.user.is_authenticated:
        raise Http404
    ctx = {}
    if request.method == 'POST':
        confirm_email_form = ConfirmEmailRequestForm(request.POST)
        if confirm_email_form.is_valid():
            try:
                user = confirm_email_form.cleaned_data["user"]
                is_subscriber_any = hasattr(user, 'subscriber') and user.subscriber.is_subscriber_any()
                send_validation_email(
                    f'Verificá tu cuenta de {site_name}',
                    user,
                    get_app_template(
                        'notifications/account_signup%s.html' % ('_subscribed' if is_subscriber_any else '')
                    ),
                    get_signup_validation_url,
                )
            except Exception as exc:
                error_log(delivery_err + " Detalle: {}".format(str(exc)))
                ctx['error'] = delivery_err
        ctx["action_content_template"] = get_app_template("confirm_email_action_content.html")
    else:
        ctx["form"] = ConfirmEmailRequestForm()
    return render(request, get_app_template('confirm_email.html'), ctx)


@never_cache
def session_refresh(request, next_page=None):
    """
    This view was created with the only purpose to delete subscription and subscription_type session variables for an
    in-process subscription. Then another session variables that can impact in a "new session" were also removed.
    """
    subscription = request.session.pop('subscription', None)
    subscription_type = request.session.pop('subscription_type', None)
    request.session.pop("google-oauth2_state", None)
    if subscription and subscription_type:
        subscription.subscription_type_prices.remove(subscription_type)
    referer = next_page or request.headers.get('referer')
    return HttpResponseRedirect(referer if referer and referer != request.path else '/')


@never_cache
def logout_view(request, next_page='/usuarios/sesion-cerrada/'):
    next_page = request.GET.get("next") or next_page
    if request.user.is_authenticated:
        return LogoutView.as_view(next_page=next_page)(request)
    else:
        return session_refresh(request, next_page)


@never_cache
@to_response
def password_change(request, user_id=None, hash=None):
    is_post = request.method == 'POST'
    post = request.POST.copy() if is_post else None
    if user_id and hash:
        user = get_object_or_404(User, id=user_id)
        form_kwargs = {'user': user_id, 'hash': hash}
        password_change_form = PasswordResetForm(post, **form_kwargs) if is_post else PasswordResetForm(**form_kwargs)
    else:
        if not request.user.is_authenticated:
            raise Http404('Unauthorized access.')
        user = request.user
        if user.has_usable_password():
            password_change_form = PasswordChangeForm(post, user=request.user) if is_post else PasswordChangeForm()
        else:
            password_change_form = PasswordChangeBaseForm(post) if is_post else PasswordChangeBaseForm()
    if is_post and password_change_form.is_valid():
        user.set_password(password_change_form.get_password())
        user.save(update_fields=["password"])
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        do_login(request, user)
        return HttpResponseRedirect(reverse(request.session.get('welcome') or 'account-password_change-done'))
    return render(
        request,
        get_app_template('password_change.html'),
        {'form': password_change_form, 'user_id': user_id, 'hash': hash},
    )


@never_cache
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

                # delete possible non-finished google signin (now is finished)
                try:
                    OAuthState.objects.get(user=user).delete()
                except OAuthState.DoesNotExist:
                    pass

                if old_email != user.email:
                    # TODO: send the email after saving the user and take actions if it not sent
                    was_sent = send_validation_email(
                        'Verificá tu cuenta', user, 'notifications/account_signup.html', get_signup_validation_url
                    )
                    if not was_sent:
                        raise Exception("Error al enviar email de verificación para el usuario %s" % user)
                    UserSocialAuth.objects.filter(user=user, provider='google-oauth2').delete()
                    user_form.save()
                    profile_form.save()
                    user.is_active = False
                    user.save()
                    messages.success(request, 'Perfil actualizado, revisá tu email para verificar el cambio de email.')
                    logout(request)
                    return HttpResponseRedirect(reverse('account-logout'))
                else:
                    user_form.save()
                    profile_form.save()
                    messages.success(request, 'Perfil Actualizado.')

            except UpdateCrmEx as e:
                user.refresh_from_db()
                messages.warning(request, e.displaymessage)

            except Exception as exc:
                user.refresh_from_db()
                msg = "Error al enviar email de verificacion para el usuario: %s." % user
                error_log(msg + " Detalle: {}".format(str(exc)))
                user_form.add_error(None, msg)
                profile_form.add_error(None, msg)

        else:
            user.refresh_from_db()
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    # Google oauth note: disconnections are discouraged when the email used is the same as the user's email because
    #                    once disconnected, if the user has no valid password, he/she would not be able to login again
    #                    without a successful pasword reset.
    oauth2_assoc, google_oauth2_multiple = None, False
    try:
        oauth2_assoc = UserSocialAuth.objects.get(user=user, provider='google-oauth2')
    except UserSocialAuth.DoesNotExist:
        pass
    except UserSocialAuth.MultipleObjectsReturned:
        oauth2_assoc, google_oauth2_multiple = True, True

    return render(
        request,
        get_app_template("edit_profile.html"),
        {
            'user_form': user_form,
            'profile_form': profile_form,
            'profile_data_form': ProfileExtraDataForm(instance=profile),
            'is_subscriber_digital': user.subscriber.is_digital_only(),
            'google_oauth2_assoc': oauth2_assoc,
            'google_oauth2_multiple': google_oauth2_multiple,
            'google_oauth2_allow_disconnect':
                not google_oauth2_multiple and oauth2_assoc and (user.email != oauth2_assoc.uid),
            'publication_newsletters': Publication.objects.filter(has_newsletter=True),
            'publication_newsletters_enable_preview': False,  # TODO: Not yet implemented, do it asap
            'newsletters': get_profile_newsletters_ordered(),
            "mailtrain_lists": MailtrainList.objects.all(),
            "incomplete_field_count": sum(
                not bool(value) for value in (
                    user.get_full_name(),
                    user.subscriber.document,
                    user.email,
                    user.subscriber.phone,
                    user.subscriber.address,
                )
            ),
            "email_is_bouncer": user.subscriber.email_is_bouncer(),
            "signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS,
        },
    )


@never_cache
@login_required
def lista_lectura_leer_despues(request):
    followings = recent_following(request.user, Article)
    followings_count = len(followings)
    if is_xhr(request):
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

    return render(
        request,
        get_app_template("lista-lectura.html"),
        {'leer_despues': followings, 'leer_despues_count': followings_count},
    )


@never_cache
@login_required
def lista_lectura_favoritos(request):
    user = request.user
    favoritos = [favorito.target for favorito in Favorite.objects.for_user(user)]
    favoritos_count = len(favoritos)
    if is_xhr(request):
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

    return render(
        request, get_app_template("lista-lectura.html"), {'favoritos': favoritos, 'favoritos_count': favoritos_count}
    )


@never_cache
@login_required
def lista_lectura_historial(request):
    """
    Returns a paginated view of all articles viewed by the user, ordered by recently viewewd.
    They are the ones in mongodb that have not been synced yet, union the ones already sinced saved in the model used
    for this purpose.
    """
    # start the result set with mongo because these are the most recent viewed.
    historial, mids = [], []
    if mongo_db is not None:
        for a in mongo_db.core_articleviewedby.find({'user': request.user.id}).sort('viewed_at', pymongo.DESCENDING):
            try:
                article_id = a['article']
                historial.append(Article.objects.get(id=article_id))
                mids.append(article_id)
            except Article.DoesNotExist:
                # the article could be removed
                pass
    # perform the union with the ones in the model
    historial += [
        avb.article for avb in request.user.articleviewedby_set.exclude(article_id__in=mids).order_by('-viewed_at')
    ]
    historial_count = len(historial)
    if is_xhr(request):
        return HttpResponse(historial_count)

    page = request.GET.get('pagina', 1)
    paginator_historial = Paginator(historial, 10)
    try:
        historial = paginator_historial.page(page)
    except PageNotAnInteger:
        historial = paginator_historial.page(1)
    except EmptyPage:
        historial = paginator_historial.page(paginator_historial.num_pages)

    return render(
        request, get_app_template("lista-lectura.html"), {'historial': historial, 'historial_count': historial_count}
    )


@never_cache
@csrf_exempt
@require_POST
def lista_lectura_toggle(request, event, article_id):
    """
    TODO: describe this view
          (its name should be changed, this view also works for toggle fav)
    """
    user = get_related_user(request, use_body=True)

    if not hasattr(user, 'subscriber'):
        return HttpResponseForbidden()

    try:
        article = Article.objects.get(id=article_id)
    except Exception:
        return HttpResponseServerError()  # TODO: does somebody catch this? if no, no reason to use a try-block

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
@api_view(['POST', "PUT"])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def update_user_from_crm(request):
    """
    Update User or Subscriber from CRM.
    updatefromcrm flag must be set to avoid ws loop.
    User is updated when the field to change is "email"
    Subscriber is updated when the field is other (a field mapping between CRM fields and Subscriber's field should be
    provided somewhere)
    """
    def changeuseremail(user, newemail):
        """
        Change linked user email
        @param user: User object
        @param newemail: new email to update the user
        """
        if user.email == user.username:
            user.username = newemail
        user.email = newemail

    def changesubscriberfield(s, field, value):
        """
        Change subscriber field value
        @param s: Subscriber object
        @param field: Subscriber field
        @param value: Subscriber field value
        """
        mapped_field = settings.CRM_UPDATE_SUBSCRIBER_FIELDS.get(field)
        if not mapped_field:
            return  # Skip if no field mapping found

        # Conversion for boolean fields
        field_value = value
        if isinstance(getattr(subscriber, mapped_field), bool):
            field_value = value if type(value) is bool else value.lower() in ['true', '1', 'yes']

        setattr(subscriber, mapped_field, field_value)

    def updatesubscriberemail(user, newemail):
        """
        Update subscriber email and peforms integrity validations
        @param u: User object
        @param newemail: new email to update the subscriber
        """
        if newemail:
            check_user_email = User.objects.filter(email=newemail)
            check_user_username = User.objects.filter(username=newemail)
            if check_user_email.exists() or check_user_username.exists():
                if check_user_email.count() == 1:
                    check_user = check_user_email[0]
                elif check_user_username.count() == 1:
                    check_user = check_user_username[0]
                else:
                    msg = 'Multiple email in users'
                    mail_managers(msg, msg)
                    return HttpResponseBadRequest()
                if check_user and check_user != user:
                    return HttpResponseBadRequest('El email ya existe en otro usuario de la web')
            # change the web user email if it's different
            if user.email != newemail:
                changeuseremail(user, newemail)
                user.updatefromcrm = True
                user.save()

    def updateuserfields(user, first_name="", last_name=""):
        updated = False
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if updated:
            user.updatefromcrm = True
            user.save()

    def updatesubscriberfields(s, fields, contact_id=None):
        """
        Update subscriber fields.
        @param s: Subscriber object
        @param contact_id: Contact ID from crm
        @param fields: fields and values in dictionary format
        """
        save_subscriber = False
        if not s.contact_id and contact_id:
            try:
                # Fetch subscriber with the given contact_id
                checked_subscriber = Subscriber.objects.get(contact_id=contact_id)
                if s != checked_subscriber:
                    return HttpResponseBadRequest(f"Contact ID: {contact_id} is already associated with another user.")
            except Subscriber.DoesNotExist:
                # No action needed if the contact_id does not exist
                pass
            except Subscriber.MultipleObjectsReturned:
                msg = f"Multiple contacts with ID: {contact_id} found in subscribers."
                mail_managers(msg, msg)
                return HttpResponseBadRequest("Multiple subscribers found with the same contact ID.")

            s.contact_id = contact_id
            save_subscriber = True

        for field, value in fields.items():
            if field == 'newsletters':
                pubs_slugs = json.loads(value)
                given_publications = Publication.objects.filter(slug__in=pubs_slugs)
                given_categories = Category.objects.filter(slug__in=pubs_slugs)
                set_newsletters = set(given_publications.values_list("slug", flat=True))
                set_cat_newsletters = set(given_categories.values_list("slug", flat=True))
                # TODO: give an example where the next affirmation could happen (not easy to understand)
                # This code set duplicates slugs in both relationships. This could be a bug in the future
                # This case would happens if for example we have a category with slug "deporte"
                # and also we have an publication with the slug "deporte".
                # In this case, if a "deporte" comes like slug for update newsletters,
                # this code code will add "deporte" like a category newsletter and like publication newsletter,
                # cause is hard to set up.
                # TODO: Pending of full review for remove the commented code (commented code, now removed, is the code
                #       that was here before this change)
                #       This can be checked with tests:
                #           given a set of slugs
                #           after this sync is made, the Subscriber's NLs set must be equal to the set given
                #       (that was exactly what the commented and now removed code used to do)
                #       NOTE: is very probbable that the "if" now will require also be True for "area_newsletters"
                s.updatefromcrm = True
                s.newsletters.set(Publication.objects.filter(slug__in=set_newsletters))
                s.category_newsletters.set(Category.objects.filter(slug__in=set_cat_newsletters))
            else:
                changesubscriberfield(s, field, value)
                save_subscriber = True

        if save_subscriber:
            s.updatefromcrm = True
            s.save()
        if settings.DEBUG:
            fields_keys, flag = fields.keys(), getattr(s, 'updatefromcrm', False)
            print(
                f"DEBUG: sync API: Subscriber={s} fields={fields_keys} save_subscriber={save_subscriber} flag={flag}"
            )

    try:
        contact_id = request.data['contact_id']
        name = request.data.get('name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        newemail = request.data.get('newemail')
        fields = json.loads(request.data.get('fields', "{}"))
    except KeyError:
        return HttpResponseBadRequest()
    try:
        subscriber = Subscriber.objects.select_related('user').get(contact_id=contact_id)
        if request.method == "PUT":
            updatesubscriberemail(subscriber.user, newemail)
            updatesubscriberfields(subscriber, fields)
            updateuserfields(subscriber.user, name, last_name)
        elif request.method == "POST":
            return HttpResponseBadRequest("already exists", status=409)
    except Subscriber.DoesNotExist:
        if settings.DEBUG:
            print(f"DEBUG: sync API: Subscriber.DoesNotExist for contact_id={contact_id}")
            print(f"DEBUG: sync API: request.data={request.data}")
            print(f"DEBUG: sync API: fields={fields}")
        if email or fields.get('email'):
            try:
                email_to_use = email or fields.get('email')
                u = User.objects.get(email__exact=email_to_use)
                u.updatefromcrm = True
                if newemail:
                    updatesubscriberemail(u, newemail)
                if hasattr(u, 'subscriber'):
                    u.subscriber.updatefromcrm = True
                    updatesubscriberfields(u.subscriber, fields, contact_id)
                updateuserfields(u, name, last_name)
            except User.DoesNotExist:
                # create new user
                # TODO: this except block is very similar to the one in the next "elif newemail:" block,
                #       we should refactor this code to avoid repetition.
                if settings.DEBUG:
                    print(f"DEBUG: sync API: User.DoesNotExist for email={email_to_use}")
                user_args = {
                    "email": newemail, "username": newemail, "first_name": name or "", "last_name": last_name or ""
                }
                new_user = User(**user_args)
                new_user.updatefromcrm = True
                try:
                    new_user.save()
                    subscriber = new_user.subscriber
                    subscriber.contact_id = contact_id
                    subscriber.updatefromcrm = True
                    subscriber.save()
                except IntegrityError as inner_ie:
                    mail_managers(
                        'IntegrityError saving user', "%s: %s" % (email_to_use, strip_tags(str(inner_ie))), True
                    )
                    return HttpResponseBadRequest()
            except MultipleObjectsReturned:
                mail_managers('Multiple email in users', email_to_use, True)
                return HttpResponseBadRequest()
            except IntegrityError as ie:
                mail_managers('IntegrityError saving user', "%s: %s" % (email_to_use, strip_tags(str(ie))), True)
                return HttpResponseBadRequest()
        elif newemail:
            try:
                u = User.objects.get(email__exact=newemail)
                if hasattr(u, 'subscriber') and u.subscriber.contact_id and u.subscriber.contact_id != contact_id:
                    mail_managers('The user already exists', newemail, True)
                    # return 409 (Conflict) when the contact_id is already associated with another user
                    return HttpResponseBadRequest(status=409)
            except User.DoesNotExist:
                # create new user
                if settings.DEBUG:
                    print(f"DEBUG: sync API: User.DoesNotExist for email={newemail}")
                user_args = {
                    "email": newemail, "username": newemail, "first_name": name or "", "last_name": last_name or ""
                }
                new_user = User(**user_args)
                new_user.updatefromcrm = True
                new_user.save()
                subscriber = new_user.subscriber
                subscriber.contact_id = contact_id
                subscriber.updatefromcrm = True
                subscriber.save()
            except MultipleObjectsReturned:
                mail_managers('Multiple email in users', newemail, True)
                return HttpResponseBadRequest()
            except IntegrityError as ie:
                mail_managers('IntegrityError saving user', "%s: %s" % (newemail, strip_tags(str(ie))), True)
                return HttpResponseBadRequest()
    except (IntegrityError, AttributeError) as ie_or_ae:
        mail_managers(
            f'{type(ie_or_ae).__name__} saving User or Subscriber',
            "contact_id=%s, %s" % (contact_id, strip_tags(str(ie_or_ae))),
            True,
        )
        return HttpResponseBadRequest()
    except KeyError:
        pass
    return JsonResponse({"message": "OK"})


@never_cache
@api_view(['DELETE'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def delete_user_from_crm(request):
    """
    Delete user API
    TODO: can be migrated to users API
    """
    def validation_on_delete(user):
        is_valid = True
        if user.is_staff or user.is_superuser:
            msg = "usuario 'staff'"
            is_valid = False
        else:
            collector = Collector(using='default')
            collector.collect([user])
            safe_to_delete, msg_err = collector_analysis(collector.data)
            if safe_to_delete:
                msg = "eliminado correctamente"
            else:
                msg = f"conjunto de datos relacionados importante o demasiado grande: {msg_err}"
                is_valid = False
        return is_valid, msg

    try:
        contact_id = request.POST["contact_id"]
        email = request.POST.get("email", "")
    except KeyError:
        return HttpResponseBadRequest("Missing argument contact_id")

    user_to_delete = None
    try:
        subscriber = Subscriber.objects.select_related("user").get(contact_id=contact_id)
        user_to_delete = subscriber.user
    except Exception:
        if email:
            user_to_delete = get_object_or_404(User, email=email)
        else:
            raise Http404

    if user_to_delete:
        is_valid, msg = validation_on_delete(user_to_delete)
        if is_valid:
            user_to_delete.delete()
        else:
            return HttpResponseBadRequest(f"No es seguro remover este usuario/suscriptor: {msg}")

    return JsonResponse({"msg": "OK"})


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

    user, reader_id = get_related_user(request, True)
    path, authenticated = urlparse(url).path, not user.is_anonymous
    result, has_subscriber = {'authenticated': authenticated}, hasattr(user, 'subscriber')
    subscriber_any = authenticated and has_subscriber and user.subscriber.is_subscriber_any()
    result['subscriber_any'] = subscriber_any

    if authenticated:
        # Make the reader_id easily available in xhr post forms in AMP page
        result["rid"] = reader_id

    if path == '/' or not settings.SIGNUPWALL_ENABLED:

        result.update({'subscriber': subscriber_any, 'access': True, 'signupwall_enabled': False})

    else:

        try:
            article = get_article_by_url_path(path)
        except Article.DoesNotExist:
            # search in url history
            article = get_object_or_404(ArticleUrlHistory, absolute_url=path).article

        restricted_article = article.is_restricted() or article.full_restricted
        result.update({'signupwall_enabled': True, 'article_restricted': restricted_article})

        if authenticated:

            if has_subscriber:
                is_subscriber = subscriber_access(user.subscriber, article)
                # newsletters
                result.update([('nl_' + slug, True) for slug in user.subscriber.get_newsletters_slugs()])
            else:
                is_subscriber = False

            result.update(
                {
                    'subscriber': is_subscriber,
                    'article_allowed': is_subscriber or article.is_public(),
                    'followed': article in following(user, Article),
                    'favourited': article in [f.target for f in Favorite.objects.for_user(user)],
                }
            )

            if is_subscriber:

                result.update({'access': True, 'edit': user.has_perm('core.change_article')})

            else:

                MAX_CREDITS = settings.SIGNUPWALL_MAX_CREDITS

                # Find up to MAX_CREDITS + 2 articles (more than that makes no difference in this logic)
                articles_visited = set() if (article.is_public() or restricted_article) else set([article.id])
                articles_visited_count = len(articles_visited)

                if mongo_db is not None:
                    for x in mongo_db.core_articleviewedby.find({'user': user.id, 'allowed': None}):
                        articles_visited.add(x['article'])
                        articles_visited_count = len(articles_visited)
                        if articles_visited_count >= MAX_CREDITS + 2:
                            break

                signupwall_limit_reach = not article.is_public() and (articles_visited_count == MAX_CREDITS + 1)
                if signupwall_limit_reach:
                    # this code is also in signupwall/middleware
                    limited_free_article_mail(user)

                credits = MAX_CREDITS - articles_visited_count
                result['access'] = article.is_public() or (credits >= 0)
                result['credits'] = credits if credits > 0 else False
                credits_eval = result['credits'] or 0
                result["signupwall_header"] = settings.SIGNUPWALL_HEADER_ENABLED and credits_eval >= 0 and not (
                    settings.SIGNUPWALL_REMAINING_BANNER_ENABLED and user.subscriber.is_subscriber_any()
                )
                if result["signupwall_header"]:
                    result.update(
                        {
                            "remaining_articles_msg":
                                render_to_string("remaining_articles_msg.html", {"credits": credits_eval}).strip(),
                            "remaining_articles_content": remaining_articles_content(optional_value=credits_eval),
                            "remaining_articles_word": number_to_words(credits_eval),
                        }
                    )

        else:

            # anon users, they will face the signupwall (see note related in settings.py).
            result['subscriber'] = False
            result['access'] = article.is_public()
            result['credits'] = bool(settings.SIGNUPWALL_ANON_MAX_CREDITS)
            if settings.AMP_DEBUG:
                print('AMP DEBUG: session_key=%s, authorization_result=%s' % (get_session_key(request), result))

        # NOTE: banner is rendered despite of setting for anon users
        result["signupwall_remaining_banner"] = not authenticated or settings.SIGNUPWALL_REMAINING_BANNER_ENABLED

        # feedback form link
        result["feedback_allowed"] = feedback_allowed(request, article, authenticated)

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
            user = get_related_user(request)

            if not user.is_anonymous:

                if mongo_db is not None and not blocked:

                    set_values = {'viewed_at': timezone.now()}
                    if article_allowed:
                        set_values['allowed'] = True
                    mongo_db.core_articleviewedby.update_one(
                        {'user': user.id, 'article': article.id}, {'$set': set_values}, upsert=True
                    )

            elif not article.is_public() and not blocked:
                # only spend a credit if the article is not public and was not blocked

                visitor = get_or_create_visitor(request)

                if visitor and mongo_db is not None:
                    mongo_db.signupwall_visitor.update_one(
                        {'_id': visitor.get('_id')}, {'$set': {'path_visited': path}}
                    )

            # inc this article visits if not blocked
            if not blocked and mongo_db is not None:
                mongo_db.core_articlevisits.update_one({'article': article.id}, {'$inc': {'views': 1}}, upsert=True)

    response = HttpResponse()
    return set_amp_cors_headers(request, response)


def users_api_noauth(request):
    # legacy support, url pattern must be defined by third party modules who want to use it. TODO: deprecation sched
    max_device_msg = 'Ha superado la cantidad de dispositivos permitidos'
    try:
        email = request.POST['email']
        if not email:
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
        msg = 'Parameter missing'
    except User.DoesNotExist:
        msg = 'User does not exist'
    except MultipleObjectsReturned:
        msg = 'Multiple email in users'
        mail_managers(msg, email)
    return HttpResponseBadRequest(msg)


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def users_api(request):
    return users_api_noauth(request)


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def email_check_api(request):
    """
    If no subscriber with the contact_id given: ok
    else:
      if exist user with the given email/username/social_auth:
        the subscriber of this user should have the same contact_id given
    """
    try:

        email, contact_id, retval = request.POST['email'], int(request.POST['contact_id']), 0

        if Subscriber.objects.filter(contact_id=contact_id).exists():

            s = User.objects.select_related('subscriber').get(
                Q(username=email) | Q(email=email) | Q(social_auth__uid=email)
            ).subscriber
            cid = getattr(s, "contact_id", None)
            if cid != contact_id:
                msg, retval = 'Ya existe otro usuario en la web utilizando ese email', getattr(s, "id", 0)
            else:
                msg = 'OK'

        else:
            msg = 'OK'

    except KeyError:
        msg, retval = 'Parameter missing', -1
    except ValueError:
        msg, retval = 'Wrong values', -2
    except User.DoesNotExist:
        msg = 'OK'
    except MultipleObjectsReturned:
        msg, retval = 'Hay más de un usuario con ese email en la web', -3
    except Subscriber.DoesNotExist:
        msg, retval = 'No hay suscriptor asociado al usuario web', -4

    return JsonResponse({"msg": msg, "retval": retval})


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def most_read_api(request):
    """
    Returns the top 5 most read articles filtered with the condition that the user with the email given, has also read
    them.
    """
    try:

        email = request.POST['email']

        if not email:
            return HttpResponseForbidden()

        # returns the top five most read articles filtered by the condition that user
        most_read_articles = Article.objects.filter(
            viewed_by=User.objects.get(email=email)
        ).values(
            'headline', 'url_path', 'date_created'
        ).annotate(total_views=Count("articleviewedby")).order_by("-total_views")[:5]

    except KeyError:
        return HttpResponseBadRequest('Parameter missing')
    except ValueError:
        return HttpResponseBadRequest('Wrong values')
    except User.DoesNotExist:
        return Http404("Usuario no encontrado")
    except MultipleObjectsReturned:
        return Http404("Multiples usuarios encontrados con el mismo email")
    return HttpResponse(most_read_articles)


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def last_read_api(request):
    """
    Takes email from POST and get the five latest read articles for the given user
    """
    try:
        email = request.POST['email']
        if not email:
            return HttpResponseForbidden()

        user = User.objects.get(email=email)

        # get latest read articles for the user
        latest_read_articles = user.articleviewedby_set.all().values(
            'article__headline',
            'article__url_path',
            'viewed_at').order_by("-viewed_at")[:5]
        # formatting the list for CRM
        articles_list = [{
            'headline': a['article__headline'],
            'url': a['article__url_path'],
            'viewed_at': a['viewed_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for a in latest_read_articles]

    except KeyError:
        return HttpResponseBadRequest('Parameter missing')
    except ValueError:
        return HttpResponseBadRequest('Wrong values')
    except User.DoesNotExist:
        return JsonResponse({"message": "Usuario no encontrado"}, status=404)
    except MultipleObjectsReturned:
        return JsonResponse({"message": "Multiples usuarios encontrados con el mismo email"}, status=404)
    return JsonResponse(articles_list, safe=False, status=200)


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def read_articles_percentage_api(request):
    """
    Takes email from POST and get the five latest read articles categories expressed in percentages
    This take in consideration the articles read in the last 6 months
    """
    try:
        email = request.POST['email']
        if not email:
            return HttpResponseForbidden()

        user = User.objects.get(email=email)

        # get six months ago date
        six_moths_ago = timezone.datetime.today() - relativedelta(months=+6)
        # get viewed articles
        viewed_articles = Article.objects.filter(
            viewed_by=user, articleviewedby__viewed_at__gt=six_moths_ago).select_related('main_section').distinct()
        total_articles_count = viewed_articles.count()
        index_object = dict()
        category_ids_counts = dict()
        for article in viewed_articles:
            if article.main_section:
                if article.main_section.section.slug in getattr(settings, 'DASHBOARD_MAIN_SECTION_SLUGS', []):
                    index_object['object'] = article.main_section.section
                    index_object['name'] = article.main_section.section.name
                    index_object['slug_id'] = 'section-{}'.format(  # noqa
                        index_object['name'], article.main_section.section.name  # TODO: fix unused arg at possition 1
                    )
                elif article.main_section.section and article.main_section.section.category:
                    index_object['object'] = article.main_section.section.category
                    index_object['name'] = article.main_section.section.category.name
                    index_object['slug_id'] = 'category-{}'.format(
                        str(article.main_section.section.category.name).lower()
                    )
                elif (
                        article.main_section.edition.publication
                        and article.main_section.edition.publication.slug
                        not in getattr(settings, "DASHBOARD_EXCLUDE_PUBLICATION_SLUGS", [])
                ):
                    index_object['object'] = article.main_section.edition.publication
                    index_object['name'] = article.main_section.edition.publication.name
                    index_object['slug_id'] = 'publication-{}'.format(article.main_section.edition.publication.slug)
                if len(index_object) > 0:
                    category_viewed_count = category_ids_counts.get(index_object['slug_id'], {'count': 0})
                    category_viewed_count = category_viewed_count['count'] + 1
                    category_ids_counts[index_object['slug_id']] = {
                        'name': index_object['name'],
                        'count': category_viewed_count,
                        'category_percentage': category_viewed_count * 100 / total_articles_count
                    }
    except KeyError:
        return HttpResponseBadRequest('Parameter missing')
    except ValueError:
        return HttpResponseBadRequest('Wrong values')
    except User.DoesNotExist:
        return JsonResponse({"message": "Usuario no encontrado"}, status=404)
    except MultipleObjectsReturned:
        return JsonResponse({"message": "Multiples usuarios encontrados con el mismo email"}, status=404)
    return JsonResponse(category_ids_counts, status=200)


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def user_comments_api(request):
    result = {'error': None}
    try:
        email = request.POST['email']
        if not email:
            return HttpResponseForbidden()
        talk_url = getattr(settings, 'TALK_URL', None)
        if talk_url:
            result.update(
                requests.post(
                    talk_url + 'api/graphql',
                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + settings.TALK_API_TOKEN},
                    data='{"query":"query user($id:ID!){user(id:$id){comments{nodes{story{url,metadata{title}},body}}}}",'  # noqa
                    '"variables":{"id":%d},"operationName":"user"}' % User.objects.get(email__iexact=email).id,
                ).json()['data']['user']['comments']
            )
        else:
            result['error'] = 'Sistema de comentarios temporalmente fuera de servicio'
    except KeyError:
        result['error'] = 'Parameter missing'
    except TypeError:
        result['error'] = 'No hay comentarios en la web asociados al usuario con ese email'
    except ValueError:
        result['error'] = 'Wrong values'
    except User.DoesNotExist:
        result['error'] = 'No existe usuario en la web con ese email'
    except MultipleObjectsReturned:
        result['error'] = 'Hay más de un usuario en la web con ese email'

    return HttpResponse(json.dumps(result), content_type="application/json")


@never_cache
@api_view(['POST'])
@api_view_auth_decorator
@permission_classes([HasAPIKey])
def custom_api(request):
    msg = ''
    try:
        operation = request.POST['operation']
        if not operation:
            return HttpResponseForbidden()
        os.system(settings.LDSOCIAL_CUSTOM_API_CMD[operation])
        return HttpResponse()
    except KeyError:
        msg = 'Parameter missing'
    return HttpResponseBadRequest(msg)


@never_cache
@to_response
def referrals(request, hashed_id):
    decoded, user = decode_hashid(hashed_id), None
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
            subject, urljoin(settings.SITE_URL, subscription.get_absolute_url()), from_mail, rcv, fail_silently=True
        )
        return 'referrals_thankyou.html'
    else:
        return 'form_referral.html'


@csrf_exempt
@never_cache
@to_response
def nlunsubscribe(request, publication_slug, hashed_id):
    publication = get_object_or_404(Publication, slug=publication_slug)
    try:
        subscriber_id = decode_hashid(hashed_id)[0]
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
            email = 'anonymous_user@localhost'
        ctx['email'] = email
        return 'nlunsubscribe.html', ctx
    except IndexError:
        raise Http404


@csrf_exempt
@never_cache
@to_response
def nl_category_unsubscribe(request, category_slug, hashed_id):
    category = get_object_or_404(Category, slug=category_slug)
    try:
        subscriber_id = decode_hashid(hashed_id)[0]
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
            email = 'anonymous_user@localhost'
        ctx['email'] = email
        return 'nlunsubscribe.html', ctx
    except IndexError:
        raise Http404


@cache_page(60 * 60 * 24 * 365)  # 1-year cache timeout since only the first open event by nl/user is significant
def nl_track_open_event(request, s8r_or_registered, hashed_id, nl_campaign, nl_date):
    ga_api_secret, debug = getattr(settings, "GA_API_SECRET", None), request.GET.get("debug") == "1"
    if ga_api_secret and settings.GA_MEASUREMENT_ID:
        tracker = GtagMP(ga_api_secret, settings.GA_MEASUREMENT_ID, str(uuid4()))
        subscriber = get_object_or_404(Subscriber, id=decode_hashid(hashed_id)[0])
        ga4_response = requests.post(
            # use "...com/debug/mp/coll.." for debug
            "https://www.google-analytics.com/%smp/collect?&api_secret=%s&measurement_id=%s" % (
                "debug/" if debug else "", ga_api_secret, settings.GA_MEASUREMENT_ID
            ),
            json={
                "client_id": tracker.random_client_id(),
                "user_id": str(subscriber.id),
                "events": [
                    {
                        "name": 'open_email_%c' % s8r_or_registered,
                        "params": {"campaign": nl_campaign, "date": nl_date, "subscriber_id": str(subscriber.id)},
                    }
                ],
            },
        )
        if debug:
            # for debugging: make a request to the gif url adding ?debug=1
            print("DEBUG: nl_track_open_event GA4 resp (%s): %s" % (ga4_response.status_code, ga4_response.json()))
    response = HttpResponse(content_type="image/gif")
    one_pixel_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    one_pixel_img.save(response, "GIF", transparency=0)
    return response


@csrf_exempt
@never_cache
@to_response
def disable_profile_property(request, property_id, hashed_id):
    """ Disables the profile bool property_id related to the subscriber matching the hashed_id argument given """
    try:
        subscriber = get_object_or_404(Subscriber, id=decode_hashid(hashed_id)[0])
        if not subscriber.user:
            raise Http404
        setattr(subscriber, property_id, False)
        ctx = {
            'property_name': {
                'allow_news': 'Novedades',
                'allow_promotions': 'Promociones',
                'allow_polls': 'Encuestas',
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
            'seller_fullname': 'Seller Fullname' if seller_fullname is None else seller_fullname,
        }
        result = render(request, get_app_template('notifications/%s.html' % template), ctx)
    except TemplateDoesNotExist:
        raise Http404
    return result


@never_cache
@csrf_exempt
def subscribe_notice_closed(request, key="subscribe"):
    if request.method == "POST":
        request.session[key + '_notice_closed'] = True
        return HttpResponse()
    else:
        return JsonResponse({"closed": request.session.get(key + '_notice_closed', False)})


@never_cache
def phone_subscription(request):
    """
    Sends an email notification to a configured receipt with the information submitted in this view.
    But also can send too, if there is enough information collected in the session using other views when the user
    selects the "subscription by phone" method, these views process the POST themselves and redirect here.

    Note: this is the default subscription method in utopia-cms because no payment gateways are ready to include yet.
    """
    template, thankyou_template, ctx = 'phone_subscription_form.html', "phone_subscription_thankyou.html", {}
    subject, mail_to = "Solicitud de suscripción", settings.SUBSCRIPTION_BY_PHONE_EMAIL_TO

    if request.POST:
        form = PhoneSubscriptionForm(request.POST)
        if form.is_valid():
            phone_blisted = phone_is_blocklisted(request.POST.get("phone"))
            if phone_blisted:
                template, ctx["phone_blocklisted"] = thankyou_template, phone_blisted
            else:
                already_done = phone_subscription_log_get4today(request)
                if already_done:
                    template, ctx["already_done"] = thankyou_template, already_done
                else:
                    text = "Nombre: %s\nTeléfono: %s\nContactar: %s" % (
                        form.cleaned_data.get('full_name'),
                        form.cleaned_data.get('phone'),
                        dict(form.fields['preferred_time'].choices)[form.cleaned_data.get('preferred_time')]
                    )
                    message = Message(
                        subject=subject, text=text, mail_from=settings.DEFAULT_FROM_EMAIL, mail_to=mail_to
                    )
                    try:
                        send_notification_message(subject, message, mail_to)
                    except Exception:
                        form.add_error(None, ValidationError(delivery_err))
                    else:
                        phone_subscription_log(request)
                        template = thankyou_template
        ctx["form"] = form

    elif request.session.get('notify_phone_subscription'):
        is_authenticated = request.user.is_authenticated
        subscription = request.session.get('subscription')
        if is_authenticated:
            user = request.user
        else:
            user = subscription.subscriber
        user.subscriber.address = subscription.address
        user.subscriber.city = subscription.city
        user.subscriber.province = subscription.province
        preferred_time = request.session.get('preferred_time')

        phone_blisted = user.subscriber.phone and phone_is_blocklisted(user.subscriber.phone.as_e164)
        if phone_blisted:
            template, ctx["phone_blocklisted"] = thankyou_template, phone_blisted
        else:
            already_done = phone_subscription_log_get4today(request, user)
            if already_done:
                template, ctx["already_done"] = thankyou_template, already_done
            else:
                user.subscriber.save()
                message = Message(
                    subject=subject,
                    text=telephone_subscription_msg(user, preferred_time),
                    mail_from=settings.DEFAULT_FROM_EMAIL,
                    mail_to=mail_to,
                )
                try:
                    send_notification_message(subject, message, mail_to)
                except Exception:
                    ctx["form"] = {"non_field_errors": [delivery_err]}
                else:
                    phone_subscription_log(request, user)
                    request.session.pop('notify_phone_subscription')
                    # delete this subscription successful attemp in session
                    request.session.pop('subscription', None)
                    is_google = request.session.get('google-oauth2_state')
                    display = not is_google and not is_authenticated
                    template = thankyou_template
                    ctx.update({'display': display, 'email': user.email})

    if "form" not in ctx:
        ctx["form"] = PhoneSubscriptionForm()
    return render(request, get_app_template(template), ctx)


def phone_subscription_log_get4today(request, user=None):
    if mongo_db is not None:
        user = user or (request.user if request.user.is_authenticated else None)
        find_arg = {'user': user.id} if user else {'session_key': get_session_key(request)}
        find_arg["timestamp"] = {"$gt": timezone.now() - timedelta(1)}
        return mongo_db.phone_subscription_log.count_documents(find_arg, limit=1)
    return False


def phone_subscription_log(request, user=None):
    if mongo_db is not None:
        user = user or (request.user if request.user.is_authenticated else None)
        insert_arg = {'user': user.id} if user else {}
        insert_arg.update({'session_key': get_session_key(request), "timestamp": timezone.now()})
        mongo_db.phone_subscription_log.insert_one(insert_arg)


def telephone_subscription_msg(user, preferred_time):
    """ Returns a body message for the subscriprion request notiffication """
    name = user.get_full_name() or user.subscriber.name
    return (
        (
            'Nombre: %s\nTipo suscripción: %s\nEmail: %s\n'
            'Teléfono: %s\nHorario preferido: %s\nDirección: %s\n'
            'Ciudad: %s\nDepartamento: %s\n'
        ) % (
            name,
            dict(settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES).get(
                user.suscripciones.all()[0].subscription_type_prices.all()[0].subscription_type, '-'
            ),
            user.email,
            user.subscriber.phone,
            dict(SUBSCRIPTION_PHONE_TIME_CHOICES).get(preferred_time, "-"),
            user.subscriber.address,
            user.subscriber.city,
            user.subscriber.province,
        )
    )
