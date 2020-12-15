# nose tests
# TODO post release: next comment line should be analized in the issue41
# TODO: signupwall app tests should be debugged (tested in Django 1.5 or 1.11)

DJANGO_SETTINGS_MODULE=test_settings REUSE_DB=1 python -W ignore manage.py test -s --nologcapture -x homev3 thedaily

