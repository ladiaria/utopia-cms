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
./manage.py migrate core
./manage.py sqlall favit | mysql <your_local_db_parameters>
```
