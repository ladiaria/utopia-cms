
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.shortcuts import render

from core.models import BreakingNewsModule, Category, Publication


@never_cache
def notification_closed(request, bn_id):
    closed = request.session.get('bn_notifications_closed', set())
    closed.add(bn_id)
    request.session['bn_notifications_closed'] = closed
    return HttpResponse()


@never_cache
def content(request):
    category_id, publication_id, bn_mod = request.GET.get('category_id'), request.GET.get('publication'), None
    bn_modules_published = BreakingNewsModule.published
    if bn_modules_published.count():
        if category_id:
            # category detail
            bn_mod = bn_modules_published.filter(categories=Category.objects.get(id=category_id))
        elif publication_id:
            # not article detail
            bn_mod = bn_modules_published.filter(publications=Publication.objects.get(slug=publication_id))
        template = getattr(
            settings, 'CORE_BN_MODULE_DETAIL_TEMPLATE', 'core/templates/breaking_news_module/detail.html'
        )
        if bn_mod:
            return render(request, template, {'bn_mod': bn_mod[0], 'notify_only': False})
        else:
            # no module for publication or category, default to notify only
            bn_mod = bn_modules_published.filter(enable_notification=True).exclude(
                id__in=request.session.get('bn_notifications_closed', set())
            )
            if bn_mod:
                return render(request, template, {'bn_mod': bn_mod[0], 'notify_only': True})
    return HttpResponse()
