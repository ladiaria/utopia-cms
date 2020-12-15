# Unit Tests

They are generated according to the testing documentation for Django 1.5: https://django-document-tchinese.readthedocs.io/en/latest/topics/testing.html

In turn we use django-nose because it saves us several minutes of execution time and also allows us to use a "tests" directory on each app, to run the tests provided chdir to `portal` and execute the `runtests.sh` script.

NOTE: To the command contained in said script you can add a `.tests.name_of_module_to_test` to test only a given module within the `tests` module of an app, and in turn adding to the above a `.ClassNameToTest` will only test that class inside the module.

Note that in addition, in the command, the environment variable `REUSE_DB=1` is set so that the test database is reused and several minutes are not lost in generating it each time the tests are run. In case the database previously used for the execution of a test is outdated, the command must be executed without said environment variable, so that the test database is eliminated and generated again.

IMPORTANT: on the mysql server `character-set-server=utf8` (in the `mysqld` section) must be set, otherwise the default encoding could be another and the `varchar` lengths 255 could fail because other encodings use more bytes and would exceed the limit of the bytes that MySQL has as cap for varchar.

There are many other very useful options such as `--nologcapture` and `--pdb`, to see all run `manage.py help test`.

At the same time we use redefined settings to execute the tests, because some apps fail when executing migrations and because some validations may fail due to the way in which django-nose load the modules.

# Tests using codeception

[Codeception](https://codeception.com/) is a test framework written in PHP. It has a very intuitive functional interface to make assertions in the tests, using "natural" verbs like `IamOnPage("/"); Isee("This is the home page")`. And also a good feature of codeception is that you simulate a real browser session in the tests, downloading static assets and running the JS code of the page, saving also the snapshots browser images of each test in the test logs.

## Codeception installation

Execute this commands in the repo "root" dir:

```
composer require codeception/codeception --dev
composer require codeception/module-webdriver --dev
composer require codeception/module-asserts --dev
cp codeception.sample.yml codeception.yml
```

Edit `codeception.yml` and change default settings (if needed) for your local environment.

## Install chromedriver

Install "chromedriver" (this can vary depending your Linux distro).

## Trust your SSL settings in chrome

```
cd docs/ssl
sudo ./ca.sh
```

Runing the above script will generate some files, the `hexxie.com` cert and key should be set in your nginx conf files (don't forget to restart nginx) and the CA should be imported in chrome using "Settings -> Privacy and Security -> Manage certificates -> Authorities -> Import".

## Run tests

1. Start chromedriver in another terminal using this command:

`chromedriver --url-base=/wd/hub`

2. Start the Django development server in another terminal as usual.

3. Run test for the "dev" environment usin this command:

`php vendor/bin/codecept run --env=dev`

# Load tests using locust

1. Install locust (do not use this project's virtualenv because locust needs Python3)

2. Copy `tests/locust/local_settings.sample.py` to `tests/locust/local_settings.py` and edit the settings according the environment to test.

3. Execute locust using `tests/locust/test1.py`
