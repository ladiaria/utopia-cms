#!/bin/sh
# TODO post release: next comment line should be analized in the issue41
# TODO: signupwall app tests should be debugged (tested in Django 1.5 or 1.11)
TEST_MODULES="homev3 core thedaily"
# exit now if we are being sourced by another script or shell
[[ "${#BASH_SOURCE[@]}" -gt "1" ]] && { return 0; }
python -W ignore manage.py test --settings=test_settings --keepdb ${TEST_MODULES}
