#!/bin/sh

exit_if_last_failed() {
    if tail $TMPLOG | grep -m1 "^FAILED"; then
        echo "FAILED"
        rm $TMPLOG
        exit 1
    fi
}

TMPLOG=`mktemp /tmp/utopia_cms_tests.XXXXXXXXXX.log`
echo "logging to $TMPLOG"

TEST_MODULES="homev3 core dashboard"
SVACTIVE="systemctl is-active --quiet supervisord"
# exit now if we are being sourced by another script or shell
[[ "${#BASH_SOURCE[@]}" -gt "1" ]] && { return 0; }
MANAGEPYTEST="python -W ignore manage.py test --settings=test_settings --failfast"
set -ex
${MANAGEPYTEST} --exclude-tag celery --keepdb ${TEST_MODULES} thedaily.tests.test_crmsync
exit_if_last_failed
# separated because fails on "transaction"
${MANAGEPYTEST} --exclude-tag skippable --exclude-tag celery --keepdb signupwall
exit_if_last_failed
${MANAGEPYTEST} --exclude-tag celery --keepdb thedaily.tests.test_subscribe
exit_if_last_failed
set +ex
`$SVACTIVE` && (
    supervisorctl stop utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
    supervisorctl start utopiacms_test
    set -ex
    ${MANAGEPYTEST} --tag celery --keepdb core
    set +ex
    supervisorctl stop utopiacms_test
    supervisorctl start utopiacms_w1 utopiacms_w2 utopiacms_w3 utopiacms_beat
)
