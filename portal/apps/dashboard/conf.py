from django.conf import settings


MAIN_SECTION_SLUGS = getattr(settings, 'DASHBOARD_MAIN_SECTION_SLUGS', [])
EXCLUDE_PUBLICATION_SLUGS = getattr(settings, 'DASHBOARD_EXCLUDE_PUBLICATION_SLUGS', [])
