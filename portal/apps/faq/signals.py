from __future__ import unicode_literals
from django.dispatch import Signal


published = Signal()
unpublished = Signal()
sites_changed = Signal()
