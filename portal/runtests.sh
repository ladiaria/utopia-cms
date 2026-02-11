#!/bin/sh
TEST_MODULES="homev3 core dashboard"
SVACTIVE="systemctl is-active --quiet supervisord"
# exit now if we are being sourced by another script or shell
[[ "${#BASH_SOURCE[@]}" -gt "1" ]] && { return 0; }
python -W ignore manage.py test --settings=test_settings --exclude-tag celery --keepdb ${TEST_MODULES} thedaily.tests.test_crmsync
# separated because fails on "transaction"
python -W ignore manage.py test --settings=test_settings --exclude-tag skippable --exclude-tag celery --keepdb signupwall
python -W ignore manage.py test --settings=test_settings --exclude-tag celery --keepdb thedaily.tests.test_subscribe
`$SVACTIVE` && (
    supervisorctl stop utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
    supervisorctl start utopiacms_test
    python -W ignore manage.py test --settings=test_settings --tag celery --keepdb core
    supervisorctl stop utopiacms_test
    supervisorctl start utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
)
