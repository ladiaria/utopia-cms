#!/bin/sh
TEST_MODULES="homev3 core signupwall dashboard"
SVACTIVE="systemctl is-active --quiet supervisord"
# exit now if we are being sourced by another script or shell
[[ "${#BASH_SOURCE[@]}" -gt "1" ]] && { return 0; }
python -W ignore manage.py test --settings=test_settings --exclude-tag celery --keepdb ${TEST_MODULES} thedaily
`$SVACTIVE` && (
    supervisorctl stop utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
    supervisorctl start utopiacms_test
    python -W ignore manage.py test --settings=test_settings --tag celery --keepdb core
    supervisorctl stop utopiacms_test
    supervisorctl start utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
)
