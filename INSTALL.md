# Utopia Content Management System Installation

## Install requirements

- Python:

  The Python version we recomend to use is any version from 3.10.6 to 3.11.2

  If your system has a native Python installation in version 3.10.6 - 3.11.2 you can use it, and no installing another Python version may be required.

  If not, we recommend install the version 3.11.2 using pyenv: https://github.com/pyenv/pyenv

- System packages:

  NOTES: package names can vary by OS/distribution.

  mariadb mariadb-devel nginx libtiff libtiff-devel giflib giflib-devel rubygem-sass npm gcc libmaxminddb-devel

- npm (Node.js packages):

  postcss-cli autoprefixer

### Local installation for development in Linux or Mac (Devs / DevOps)

#### Local repository and virtualenv configuration

- Clone the project repository to any local destination directory and init its git submodules (this can take some minutes):

  ```
  user@host:~ $ git clone -b main https://github.com/ladiaria/utopia-cms
  cd utopia-cms && git submodule update --init
  ```

- Clone also another repo with more static files needed:

  `user@host:~/utopia-cms $ git clone -b main https://github.com/ladiaria/lightGallery static/lightGallery`

- Create a virtualenv (venv) for Python3 (the subdirectory `~/.virtualenvs` is not needed, we use it in this guide because is the default virtualenv directory in the tool [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/), also the virtual environment name can be any other, "utopiacms" is chosen in this guide):

  NOTE: if using pyenv, this venv creation is done a bit different, consult the pyenv documentation for that.

  `user@host:~/utopia-cms $ mkdir -p ~/.virtualenvs && virtualenv ~/.virtualenvs/utopiacms`

- Activate the new virtual environment and install the required Python modules:

  ```
  user@host:~/utopia-cms $ source ~/.virtualenvs/utopiacms/bin/activate
  (utopiacms) user@host:~/utopia-cms $ pip install --upgrade pip && pip install -r portal/requirements.txt
  ```

  NOTE: If you get an error that saying `OSError: mysql_config not found` you need to check that mysql is in your PATH,
  for example, you can run `PATH=$PATH:/usr/local/mysql/bin` to add the directory `/usr/local/mysql/bin` to the current
  PATH and then retry the `pip` command. We also have seen errors regarding to "not found" MySQL libraries on MacOS
  installations that were solved doing symlinks.

#### Database setup

- Create a new database and grant user privileges to a new or existing database user:

```
(utopiacms) user@host:~/utopia-cms $ sudo mysqladmin create utopiacms
(utopiacms) user@host:~/utopia-cms $ sudo mysql
MariaDB [(none)]> CREATE USER 'utopiacms_user'@'localhost' IDENTIFIED BY 'password';
MariaDB [(none)]> GRANT ALL PRIVILEGES ON utopiacms.* TO 'utopiacms_user'@'localhost';
```

- Create a local settings module based on the sample given:

```
(utopiacms) user@host:~/utopia-cms $ cd portal
(utopiacms) user@host:~/utopia-cms/portal $ cp local_settings_sample.py local_settings.py
```

Edit the new file created (`local_settings.py`) to set your new database credentials and also fill the `SECRET_KEY` variable using any string or a more secure one generated for example with [this web tool](https://djecrety.ir/).

Check also if your system locale settings match the default language (`es`) and country (`UY`), override this variables in the `local_settings.py` file if not. In most linux distributions the available locales are defined in the `/etc/locale.gen` file, you should have an uncommented line in this file matching your resultant `LOCALE_NAME` setting, (`es_UY.utf-8` by default, if not overrided as said).

- Create needed tables using Django's `migrate` management command twice, without and with the `--run-syncdb` argument:

```
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py migrate
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py migrate --run-syncdb
```

#### Development environment setup

- Create a Django superuser and collect static files using this commands:

```
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py createsuperuser
(utopiacms) user@host:~/utopia-cms/portal $ python -W ignore manage.py collectstatic --noinput
```

- Configure Nginx for reverse proxying the Django's development server and start it:

Follow the steps under "Create and trust your SSL certificates" in `docs/TESTING.md`.

Then create your nginx conf file using the sample provided (edit it after copy, if needed):

```
(utopiacms) user@host:~/utopia-cms/portal $ sudo cp ../docs/nginx_example_conf/utopia-cms-dev.conf /etc/nginx/conf.d
(utopiacms) user@host:~/utopia-cms/portal $ sudo systemctl restart nginx
(utopiacms) user@host:~/utopia-cms/portal $ ./runserver yoogle.com:8000
```

- Login with superuser created before, edit the default site domain and create a publication with the same slug to the one configured in `settings.DEFAULT_PUB`:

NOTE: If you change the default `settings.DEFAULT_PUB` value from `default` to any `otherslug` value in your local settings, then you should update the permission codename used to check when a user is subscribed to this publication, to perform this update, run this SQL sentence below. Ignore this note and the sentence related if the setting was not modified.

`UPDATE auth_permission SET codename='es_suscriptor_otherslug' WHERE codename='es_suscriptor_default';`

Point your preferred web browser to https://yoogle.com/admin/sites/site/1/ and you will be redirected to the Django's admin site login page, after login you will be redirected again to the default site change form, change its domain to `yoogle.com` and optionally also change its display name to any name you want, save the changes and then go to https://yoogle.com/admin/core/publication/add/ fill the form to create the new publication, save it and then you will be able to see the home page working at https://yoogle.com/.
