from django.db import models
from ..compat import AUTH_USER_MODEL


class Language(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE)
    language = models.CharField("language", max_length=10)
