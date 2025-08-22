from django.urls import path

from core.views.newsletters import index

urlpatterns = [
    path('', index, name='user_newsletters'),
]
