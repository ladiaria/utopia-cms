# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from .models import Contribution

from django.contrib.admin import site

site.register(Contribution)
