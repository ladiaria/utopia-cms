# From version 0.3.7 to 0.3.8

```
git pull
git checkout 0.3.8
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.3.6 to 0.3.7

```
git pull
git checkout 0.3.7
cd portal
# update your local settings based on local_settings_sample.py (2 uneeded variables removed)
# activate your virtual env
./manage.py migrate
```

# From version 0.3.5 to 0.3.6

```
git pull
git checkout 0.3.6
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.3.4 to 0.3.5

```
git pull
git checkout 0.3.5
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.3.3 to 0.3.4

```
git pull
git checkout 0.3.4
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.3.2 to 0.3.3

```
git pull
git checkout 0.3.3
cd portal
# activate your virtual env
pip install -r requirements.txt
./manage.py migrate
```

# From version 0.3.1 to 0.3.2

```
git pull
git checkout 0.3.2
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.3.0 to 0.3.1

```
git pull
git checkout 0.3.1
cd portal
# activate your virtual env
cat libs/scripts/one_time/20220906_upd_columns.sql | ./manage.py dbshell
pip install --upgrade -r requirements.txt
./manage.py migrate favit --fake
./manage.py migrate
```

# From version 0.2.9 to 0.3.0

```
git pull
git checkout 0.3.0
# create a new Python virtualenv according to INSTALL.md
# install Python requirements using pip with the new virtualenv activated
# update your local settings based on local_settings_sample.py
find . -name "*.pyc" -delete
cd portal
./manage.py collectstatic
# if using wsgi for deployment: update uwsgi.ini (if using also uwsgi) and wsgi.py based on new sample files
```

# From version 0.2.8 to 0.2.9

```
git pull
git checkout 0.2.9
```

# From version 0.2.7 to 0.2.8

```
git pull
git checkout 0.2.8
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.2.6 to 0.2.7

```
git pull
git checkout 0.2.7
cd portal
# activate your virtual env and execute the commands shown in the output of the following command:
./manage.py shell -c "execfile('libs/scripts/one_time/20220519_mongo_one_db.py')"
```

# From version 0.2.5 to 0.2.6

```
git pull
git checkout 0.2.6
# Following steps needed only if you ever generated any *articles.csv datasets for the dashboard app:
cd portal
# activate your virtual env
pip install tqdm
./manage.py shell -c "execfile('libs/scripts/one_time/add_extra_columns_to_articles_csv.py')"
```

# From version 0.2.4 to 0.2.5

```
git pull
git checkout 0.2.5
# Update your local_settings.py file, see sample file, two variables have been renamed.
```

# From version 0.2.3 to 0.2.4

```
git pull
git checkout 0.2.4
# Update your local_settings.py file, GA_MEASUREMENT_ID (GA v4) is needed, can be set to '' like in sample file.
# activate your virtual env
pip install -r portal/requirements.txt
```

# From version 0.2.2 to 0.2.3

```
git pull
git checkout 0.2.3
cd portal
# activate your virtual env
./manage.py migrate
# optionally uninstall materialize:
pip uninstall materialize
```

In a production environment, to keep the most read articles table synced correctly, you should run the command
`sync_article_views` everyday before day-end.

# From version 0.2.1 to 0.2.2

```
git pull
git checkout 0.2.2
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.2.0 to 0.2.1

```
git pull
git checkout 0.2.1
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.1.9 to 0.2.0

```
git pull
git checkout 0.2.0
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.1.8 to 0.1.9

```
git pull
git checkout 0.1.9
# activate your virtual env
pip install django-elasticsearch-dsl
```

# From version 0.1.7 to 0.1.8

```
git pull
git checkout 0.1.8
cd portal
# activate your virtual env
./manage.py migrate core
```

# From version 0.1.6 to 0.1.7

```
git pull
git checkout 0.1.7
cd portal
# activate your virtual env
./manage.py migrate
./manage.py dbshell
-- inside the dbshell run this sentence to fix non-published articles (if any):
UPDATE core_article SET date_published=NULL WHERE NOT is_published;
```

# From version 0.1.5 to 0.1.6

```
git pull
git checkout 0.1.6
cd portal
# activate your virtual env
./manage.py migrate
```

# From version 0.1.4 to 0.1.5

```
git pull
git checkout 0.1.5
cd portal
# activate your virtual env
./manage.py migrate --sync-db
./manage.py shell
# inside the Django shell execute this sentences:
from django.conf import settings
from django.contrib.auth.models import Permission
p = Permission.objects.get(codename='es_suscriptor_ladiaria')
p.name, p.codename = 'Es suscriptor actualmente', 'es_suscriptor_' + settings.DEFAULT_PUB
p.save()
```

# From version 0.1.3 to 0.1.4

```
git pull
git checkout 0.1.4
cd portal
# activate your virtual env
./manage.py migrate core
```

# From version 0.1.2 to 0.1.3

NOTE: Development domain changed to yoogle.com, update your local_settings if needed.

```
git pull
git checkout 0.1.3
```

# From version 0.1.1 to 0.1.2

```
git pull
git checkout 0.1.2
cd portal
# activate your virtual env
./manage.py migrate core
```

# From version 0.1.0 to 0.1.1

WARNING: The "keep reading" feature was removed, if you want to keep the article relations that you made with this
feature, you have to backup your data before this upgrade. Then you can just relate each "group" of the articles
involved through a tag, we believe that this is the "state of the art" mechanism to maintain a group of related
articles in a publication site, and its usage is easier for the publisher user than the removed feature.

```
git pull
git checkout 0.1.1
cd portal
# activate your virtual env
pip uninstall django-formtools
pip install -r requirements.txt
./manage.py migrate core
```

# From version 0.0.9 to 0.1.0

[Upgrade from 0.0.9 to 0.1.0 guide](docs/upgrade_from_009_to_010.md)

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
