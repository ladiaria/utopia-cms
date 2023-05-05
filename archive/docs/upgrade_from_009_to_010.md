# Upgrade from 0.0.9 to 0.1.0 guide

NOTE: A database superuser is required.

## 0.

**Backup** your database in case anything goes wrong.

Specially **backup** your "robots" app data (if any) to **restore it manually** after the upgrade, because this app will be upgraded and its data will be deleted.

## 1.

```
cd portal
./manage.py dumpdata photologue --indent 2 > photologue_data.json
cd ..
git pull
git checkout 0.1.0
rm -rf static/typi
pip install --upgrade pip setuptools
pip install -r portal/requirements.txt
```

If you got a Pillow error, upgrade it with: `pip install --upgrade pillow`.

If you have custom django apps installed, do a pip install of them, among with their new requirements for Django 1.11 if they have been chaged.

## 2.

```
pip uninstall south
pip install --force-reinstall "git+git://github.com/ladiaria/django-tagging-autocomplete-tag-it.git#egg=django-tagging-autocomplete"
```

## 3.

Update your local settings based on `local_settings_sample.py`.

Comment the use of the argument "article__photo__extended__photographer" in `core/models.py` filters, in the `top_articles` and `get_articles_in_section` methods of the `Edition` class.

## 4.

```
find . -name "*.pyc" -delete
pip install "python-social-auth==0.2.21"
```

## 5.

Replace "social_django" by "social.apps.django_app.default" in `settings.INSTALLED_APPS`.

## 6.

```
cd portal
./manage.py migrate --fake
mv photologue_data.json libs/scripts/upgradeDjango11
cd libs/scripts/upgradeDjango11
./upgrade_to_18.py photologue_data.json
sed -i 's/title_slug/slug/g' photologue_data.json
cd -
./manage.py dbshell
```

Execute the following SQL statements in the database shell opened with the last command:

```
ALTER TABLE django_content_type MODIFY COLUMN name varchar(100);
ALTER TABLE auth_user MODIFY COLUMN last_login datetime;
```

Exit database shell with CTRL-d.

## 7.

```
./manage.py migrate --fake photologue zero
```

Enter a database shell using a database server superuser (this is usually done by executing `sudo mysql`) and execute the following statement:

`SET @@GLOBAL.FOREIGN_KEY_CHECKS = 0; SET @@SESSION.foreign_key_checks = 0;`

Exit the superuser database shell and enter again in a Django dbshell with `manage.py dbshell` and execute this statement:

`DROP TABLE photologue_gallery, photologue_gallery_photos, photologue_galleryupload, photologue_photo, photologue_photoeffect, photologue_photosize, photologue_watermark;`

Exit database shell with CTRL-d.

## 8.

```
./manage.py migrate photologue
```

Enter again in a Django dbshell with `manage.py dbshell` and execute the following statements:

```
ALTER TABLE photologue_gallery MODIFY COLUMN title VARCHAR(250) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
ALTER TABLE photologue_gallery MODIFY COLUMN description longtext CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
ALTER TABLE photologue_photo MODIFY COLUMN caption longtext CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
ALTER TABLE photologue_photo MODIFY COLUMN title varchar(250) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
ALTER TABLE photologue_photo MODIFY COLUMN image varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL;
DELETE FROM photologue_photosize;
```

Exit database shell with CTRL-d and add the line `USE_TZ=True` to your `local_settings.py`.

## 9.

```
./manage.py loaddata libs/scripts/upgradeDjango11/photologue_data.json
```

Remove the file used in the last step if everything was ok with the loaddata command.

Remove the line added in previous step, enter a database shell using a database server superuser and execute this statement:

`SET @@GLOBAL.FOREIGN_KEY_CHECKS = 1; SET @@SESSION.foreign_key_checks = 1;`

Exit database shell with CTRL-d.

## 10.

```
git checkout apps/core/models.py
./manage.py migrate --fake
./manage.py migrate actstream 0002 --fake
./manage.py migrate actstream
./manage.py migrate --fake star_ratings zero
./manage.py migrate star_ratings
```

Enter again in a Django dbshell with `manage.py dbshell` and execute the following statements:

```
DROP TABLE robots_rule_allowed;
DROP TABLE robots_rule_disallowed;
DROP TABLE robots_rule_sites;
DROP TABLE robots_url;
DROP TABLE robots_rule;
DELETE FROM django_migrations WHERE app='robots';
```

Exit database shell with CTRL-d.

## 11.

```
rmdir apps/robots
./manage.py migrate robots
./manage.py migrate social_auth 0001 --fake
./manage.py migrate social_auth
git checkout settings.py
./manage.py migrate
pip install --upgrade python-social-auth
./manage.py collectstatic -c --noinput
./manage.py clear_cache
```
