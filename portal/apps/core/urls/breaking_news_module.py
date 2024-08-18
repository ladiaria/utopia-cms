from core.views.breaking_news_module import notification_closed, content

from django.urls import path

urlpatterns = [
    path('<int:bn_id>/closed/', notification_closed, name='bn-notification-closed'),
    path('content/', content, name='bn-content'),
]
