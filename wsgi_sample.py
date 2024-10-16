"""
TODO: docstring for this file, authors, etc.
      Also, a sample is not needed anymore, this can be the real file used in deployments.
"""
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/portal')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'


from django.core.wsgi import get_wsgi_application  # noqa
application = get_wsgi_application()
