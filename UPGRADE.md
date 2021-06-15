# From version 0.0.8 to 0.0.9

```
git pull
git checkout 0.0.9
cd portal
# activate your virtual env
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate core
```

# From version 0.0.7 to 0.0.8

```
git pull
git checkout 0.0.8
cd portal
# activate your virtual env
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate thedaily
```

# From version 0.0.6 to 0.0.7

```
git pull
git checkout 0.0.7
mysql -u <db_user> -p <db_name> -Be "SELECT * FROM core_home" > /tmp/core_home.csv
mysql -u <db_user> -p <db_name> -Be "SELECT * FROM core_module" > /tmp/core_module.csv
cd portal
# activate your virtual env and migrate core (answer "yes" to the question of removing stalled content types):
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate core
./manage.py shell
# inside the Django shell execute this line:
execfile('libs/scripts/one_time/20210524_migrate_category_homes.py')
```

# From version 0.0.5 to 0.0.6

```
git pull
git checkout 0.0.6
cd portal
# activate your virtual env
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate thedaily
```

# From version 0.0.4 to 0.0.5

```
git pull
git checkout 0.0.5
rm -rf static/jquery_lazyload
cd portal
# activate your virtual env
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate core
```

# From version 0.0.3 to 0.0.4

```
git pull
git checkout 0.0.4
cd portal
# activate your virtual env
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate core
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate thedaily
```

# From version 0.0.2 to 0.0.3

```
git pull
git checkout 0.0.3
cd portal
rm -rf apps/tagging_autocomplete_tagit
# activate your virtual env
pip install -r requirements.txt
```

# From version 0.0.1 to 0.0.2

```
git pull
git checkout 0.0.2
cd portal
# activate your virtual env
pip remove django-inplaceedit-bootstrap
pip remove django-inplaceedit-extra-fields
pip install --upgrade -r requirements.txt
DJANGO_SETTINGS_MODULE=install_settings ./manage.py migrate core
./manage.py sqlall favit | mysql <your_local_db_parameters>
```
