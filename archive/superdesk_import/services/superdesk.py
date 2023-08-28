import base64
import pytz
from django.conf import settings
from dateutil import parser
from datetime import datetime, timedelta
from .restapi import API

# BASIC_URL = 'http://localhost:8080/api'
BASIC_URL = settings.SP_API_URL if hasattr(settings, 'SP_API_URL') else 'http://localhost:8080/api'


class SuperDeskService:

    _token = None

    def __init__(self):
        self.api = API()

    def set_token(self, token_param):
        try:
            t = str(token_param) + ':'
            result = b'basic ' + base64.b64encode(t.encode('ascii'))
            self._token = result
        except Exception as ex:
            raise Exception("Error in getting authorization token process. Detail {}".format(str(ex)))

    def get_headers(self):
        try:
            if not self._token:
                raise Exception("No Authorization Token, No Headers")
            return {
                'Authorization': self._token,
                'Content-Type': 'application/json;charset=UTF-8'
            }
        except Exception as ex:
            raise

    def login(self):
        try:
            url = BASIC_URL + '/auth_db'
            username = settings.SP_USERNAME if hasattr(settings, 'SP_USERNAME') else "admin"
            password = settings.SP_PASSWORD if hasattr(settings, 'SP_PASSWORD') else "admin"
            values = """{{
            "username": "{username}", "password": "{password}"
            }}""".format(username=username, password=password)

            headers = {
              'Content-Type': 'application/json',
              # 'Content-Type': 'multipart/form-data'
            }
            res = self.api.do_post(url, data=values, headers=headers)
            t = res['token']
            self.set_token(t)
        except Exception as ex:
            raise Exception("Error on log in. Detail: {}".format(ex))

    def get_user(self, user_id):
        try:
            url = BASIC_URL + '/users/{}'.format(str(user_id))
            headers = self.get_headers()
            res = self.api.do_get(url, headers=headers)
            return res
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_user_email(self, email_param):
        try:
            url = BASIC_URL + '/users'
            headers = self.get_headers()
            email_filter = '{"email": "{}"}'.format(email_param)
            params = {'where': email_filter, 'max_results': '1'}
            res = self.api.do_get(url, headers=headers, params=params)
            return res[0] if len(res) > 1 else None
        except Exception as ex:
            raise Exception("Error getting user by email. Detail: {}".format(ex))

    def get_user_byline(self, byline_param):
        try:
            url = BASIC_URL + '/users'
            headers = self.get_headers()
            email_filter = '{{"{byline}": "{byline_value}"}}'.format(byline='byline', byline_value=byline_param)
            params = {'where': email_filter, 'max_results': '1'}
            res = self.api.do_get(url, headers=headers, params=params)
            return res['_items'][0] if len(res['_items']) > 0 else None
        except Exception as ex:
            raise Exception("Error getting user by email. Detail: {}".format(ex))

    def get_users(self):
        try:
            url = BASIC_URL + '/users'
            headers = self.get_headers()
            res = self.api.do_get(url, headers=headers)
            return res.get("_items", [])
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_users_by_ids(self, ids):
        try:
            return [self.get_user(i) for i in ids]
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_user_archive(self, user_id):
        try:
            url = BASIC_URL + '/users/{}/archive'.format(str(user_id))
            headers = self.get_headers()
            res = self.api.do_get(url, headers=headers)
            return res
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_user_archive_submitted(self, user_id):
        try:
            url = BASIC_URL + '/users/{}/archive'.format(str(user_id))
            headers = self.get_headers()
            # params = {'where': '{{"{state}": "{value}"}}'.format(state='state', value='submitted')}
            res = self.api.do_get(url, headers=headers)
            return res
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_archives(self, date_param):
        try:
            date_str = date_param.strftime("%Y-%m-%d")
            url = BASIC_URL + '/archive'
            headers = self.get_headers()
            params = {'where': '{{"{first_created}": "{date}"}}'.format(first_created='firstcreated', date=date_str)}
            res = self.api.do_get(url, headers=headers, params=params)
            return res["_items"]
        except Exception as ex:
            raise Exception("Error getting archives. Detail: {}".format(ex))

    def get_archive(self, archive_id):
        try:
            url = BASIC_URL + '/archive/{}'.format(str(archive_id))
            headers = self.get_headers()
            res = self.api.do_get(url, headers=headers)
            return res
        except Exception as ex:
            raise Exception("Error getting user. Detail: {}".format(ex))

    def get_submitted_articles(self):
        """
        Get SP published articles that was created in the given date
        """
        try:
            url = BASIC_URL + '/archive'
            headers = self.get_headers()
            params = {'where': '{{"{state}": "{value}"}}'.format(state='state', value='submitted')}
            res = self.api.do_get(url, headers=headers, params=params)
            utc = pytz.UTC
            d_now = (datetime.now() + timedelta(hours=3)).replace(tzinfo=utc)
            d_last_24h = (d_now - timedelta(hours=30)).replace(tzinfo=utc)
            return [a for a in res["_items"] if d_last_24h <= parser.parse(a['_updated']).replace(tzinfo=utc) <= d_now]
        except Exception as ex:
            raise Exception("Error getting published articles. Detail: {}".format(str(ex)))

    def get_submitted_users_articles(self):
        """
        Get SP published articles that was created in the given date
        """
        try:
            all_submitted_articles = list()
            users = self.get_users()
            utc = pytz.UTC
            d_now = (datetime.now() + timedelta(hours=3)).replace(tzinfo=utc)
            d_last_24h = (d_now - timedelta(hours=30)).replace(tzinfo=utc)
            for user in users:
                user_id = user["_id"]
                user_articles = self.get_user_archive_submitted(user_id)
                for u_article in user_articles:
                    if d_last_24h <= parser.parse(u_article['_updated']).replace(tzinfo=utc) <= d_now:
                        all_submitted_articles.append(u_article)
            return all_submitted_articles
        except Exception as ex:
            raise Exception("Error getting published articles. Detail: {}".format(str(ex)))

    # filters
    def get_not_image_articles(self, sp_articles):
        """
        Get not image SP published articles
        """
        try:
            return [a for a in sp_articles if a['type'] != 'picture']
        except Exception as ex:
            raise Exception("Error getting not image articles. Detail: {}".format(str(ex)))
