# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.management import CommandError
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from libs.tokens.email_confirmation import send_validation_email, get_signup_validation_url
from thedaily.views import get_password_validation_url
from thedaily.tasks import notify_subscription, send_notification
from thedaily.management.commands.automatic_mail_paywall import send_message
from thedaily.utils import get_app_template, get_notification_subjects


class Command(BaseCommand):
    # TODO: make "wrappers" for each kind of send action, this way, the template can be encapsulated on it and won't be
    # necessary to pass it here duplicating code with hardcoded filenames. (signup_wall is already using this approach)
    help = '(this can be seen as a test), the suffix "preview" was choosed for not to make confussion with native test'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            action='store',
            type=int,
            required=True,
            dest='user_id',
            help='A user id who will be the emails receipt',
        )

    def send_tests(self, user_id):
        # the idea is to test all templates under thedaily/templates/notifications sending a email with each of them.
        try:
            u = User.objects.get(id=user_id)
            assert u.email, "The user with the user_id given has no email, aborting"
        except User.DoesNotExist:
            raise CommandError("The user with the user_id given does not exist, aborting")
        except AssertionError as exc:
            raise CommandError(str(exc))

        notification_subjects = get_notification_subjects()

        # account_info.html
        was_sent = send_validation_email(
            'Ingreso al sitio web',
            u,
            get_app_template('notifications/account_info.html'),
            get_signup_validation_url,
        )
        if not was_sent:
            print("account_info.html - FAIL")

        # account_signup.html
        template_name = 'account_signup.html'
        was_sent = send_validation_email(
            notification_subjects[template_name],
            u,
            get_app_template(f'notifications/{template_name}'),
            get_signup_validation_url,
        )
        if not was_sent:
            print("account_signup.html - FAIL")

        # account_signup_subscribed.html
        template_name = 'account_signup_subscribed.html'
        try:
            was_sent = send_validation_email(
                notification_subjects[template_name],
                u,
                get_app_template(f'notifications/{template_name}'),
                get_signup_validation_url,
            )
            if not was_sent:
                print("account_signup_subscribed.html - FAIL")
        except Exception as exc:
            msg = f"Error al enviar email de verificación de suscripción para el usuario: {u}."
            print(msg + " Detalle: {}".format(str(exc)))

        # used only by mergedocs command temporarily disabled, TODO: enable after mergedocs get updated and fixed
        # html_message = render_to_string(
        #     get_app_template('notifications/validation_email.html'),
        #     {"site": site, "SITE_URL_SD": settings.SITE_URL_SD, 'logo_url': settings.HOMEV3_SECONDARY_LOGO},
        # )
        # validation_email.html
        # u.email_user(
        #     '[%s] Tu cuenta de usuario' % site.name, message=markdownify(html_message), html_message=html_message
        # )

        for subscription_type in settings.THEDAILY_SUBSCRIPTION_TYPE_CHOICES:
            notify_subscription(u, subscription_type)
            notify_subscription(u, subscription_type, "Vendedornombre Vendedorapellido")

        # password_reset_body.html
        template_name = 'password_reset_body.html'
        try:
            was_sent = send_validation_email(
                notification_subjects[template_name],
                u,
                get_app_template(f'notifications/{template_name}'),
                get_password_validation_url,
            )
            if not was_sent:
                print(f"No se pudo enviar el email de recuperación de contraseña para el usuario: {u}")
        except Exception as exc:
            msg = f"Error al enviar email de recuperación de contraseña para el usuario: {u}."
            print(msg + " Detalle: {}".format(str(exc)))

        # signup.html
        template_name = 'signup.html'
        send_notification(
            u,
            get_app_template(f'notifications/{template_name}'),
            notification_subjects[f"{template_name}_variant"],
            {"signupwall_max_credits": settings.SIGNUPWALL_MAX_CREDITS},
        )

        # signup_wall.html
        send_message(u)

    def handle(self, *args, **options):
        user_id = options.get("user_id")
        if user_id:
            self.send_tests(user_id)
