# Unit Tests

They are generated according to the testing documentation for Django 1.11: https://docs.djangoproject.com/en/1.11/topics/testing/

You can execute the `runtests.sh` script in the same directory also with the virtualenv activated, this will execute all the tests. It's safe to apply the created migration using `--fake` and obviously there's no need to run the "makemigrations" command again to execute again the tests script, unless you remove the created migration from your virtualenv.

NOTE: To the command contained in said script you can add a `.tests.name_of_module_to_test` to test only a given module within the `tests` module of an app, and in turn adding to the above a `.ClassNameToTest` will only test that class inside the module.

IMPORTANT: on the mysql server `character-set-server=utf8` (in the `mysqld` section) must be set, otherwise the default encoding could be another and the `varchar` lengths 255 could fail because other encodings use more bytes and would exceed the limit of the bytes that MySQL has as cap for varchar.

# Tests using codeception

[Codeception](https://codeception.com/) is a test framework written in PHP. It has a very intuitive functional interface to make assertions in the tests, using "natural" verbs like `IamOnPage("/"); Isee("This is the home page")`. And also a good feature of codeception is that you simulate a real browser session in the tests, downloading static assets and running the JS code of the page, saving also the snapshots browser images of each test in the test logs.

## Codeception installation

Execute this commands in the repo "root" dir:

```
composer require --dev codeception/codeception:^5.0.0-alpha3
composer require --dev codeception/module-webdriver
composer require --dev codeception/module-asserts
cp codeception.sample.yml codeception.yml
```

Edit `codeception.yml` and change default settings (if needed) for your local environment.

## Install chromedriver

Install "chromedriver" (this can vary depending your Linux distro).

## Create and trust your SSL certificates

### Create

The execution of the following script will ask you many questions, the most important are the first password (after the "sudo" one, if asked), which should be set (do not left it blank) and remembered because it will be asked again in the next two steps and in the final step; and the FQDN that should be set to "yoogle.com". The challenge password asked almost at the end can be left blank.

```
cd docs/ssl
sudo ./ca.sh
```

Runing the above script will generate some files, the `yoogle.com` cert and key should be set in your nginx conf files (our nginx samples conf files included in this repository in the `docs/nginx_example_conf` directory; are using the `/etc/nginx/certs` directory to load these cert and key files, don't forget to restart nginx after copy your generated files to the destination directory and configure nginx).

### Trust

There are two options, choose one or both.

1. Import in browser: The `.pem` file generated with the above script can be imported in chrome using "Settings -> Privacy and Security -> Security -> Manage certificates -> Authorities -> Import", for Firefox is quite the same. When importing, at least check the first option "Trust this certificate for identifying websites".

2. Import in the OS, in Linux you can trust a CA certificate like the one generated above, using the following commands (don't do it in a production environment unless you know well whay you're doing), the paths/binaries can vary by distribution/version:

```
sudo cp myCA.pem /usr/share/ca-certificates/trust-source/anchors
sudo update-ca-trust
```

## Running Codeception tests (TODO: check if needed-working)

1. Start chromedriver in another terminal using this command:

`chromedriver --url-base=/wd/hub`

2. Start the Django development server in another terminal as usual.

3. Run test for the "dev" environment usin this command:

`php vendor/bin/codecept run --env=dev`

# Load tests using locust.io (TODO: verify if working)

1. Install locust

2. Copy `tests/locust/local_settings.sample.py` to `tests/locust/local_settings.py` and edit the settings according the environment to test.

3. Execute locust using `tests/locust/test1.py`
