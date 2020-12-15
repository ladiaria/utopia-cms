ALLDIRS = [
    '/opt/venv/utopiacms/lib/python2.7/site-packages', '/srv/utopia-cms', '/srv/utopia-cms/portal',
    '/srv/utopia-cms/portal/media',]

activate_this = '/opt/venv/utopiacms/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import os
import sys
import site

# redirect sys.stdout to sys.stderr for bad libraries like geopy that uses
# print statements for optional import exceptions.
sys.stdout = sys.stderr
prev_sys_path = list(sys.path)

for directory in ALLDIRS:
    site.addsitedir(directory)

# Reorder sys.path so new directories at the front.
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)

sys.path[:0] = new_sys_path

from os.path import abspath, dirname, join
from site import addsitedir

sys.path.insert(0, abspath(join(dirname(__file__), ".")))

from django.conf import settings
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()

