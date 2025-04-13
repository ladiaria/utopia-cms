@never_cache
@to_response
def referrals(request, hashed_id):
    """
    This view is used to handle the referral form submission, urlpattern entry:
    re_path(r'^referidos/(?P<hashed_id>\w+)/$', referrals, name="referrals"),
    """
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
            subscription.billing_email = user.email
            subscription.subscriber = user.subscriber
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
