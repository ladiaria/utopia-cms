import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/portal')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

activate_this_file = '/opt/venv/utopiacms/bin/activate_this.py'

exec(compile(open(activate_this_file, "rb").read(), activate_this_file, 'exec'), dict(__file__=activate_this_file))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
