from __future__ import unicode_literals
from django.urls import path

from core.views.masleidos import index, content

urlpatterns = [
    path('', index, name='mas_leidos'),
    path('content/', content, name='mas_leidos_content'),
]
