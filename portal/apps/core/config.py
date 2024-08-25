from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Article'))
