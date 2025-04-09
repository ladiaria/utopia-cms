from django.db import models, transaction


class SubscriberManager(models.Manager):
    def get_or_create_deferred(self, defaults=None, **kwargs):
        """
        Mimics get_or_create() with commit=False logic and uses transactions for concurrency handling.
        """
        defaults = defaults or {}
        with transaction.atomic():
            # Try to fetch the object
            obj = self.filter(**kwargs).first()
            if obj:
                return obj, False

            # Object does not exist; create it without saving
            obj = self.model(**kwargs, **defaults)
            return obj, True
