import requests


class API:

    def do_get(self, url, headers, params=None):
        try:
            r = requests.get(url, params=params, headers=headers)
            if r.status_code not in [200, 201]:
                raise Exception("Service error for {}. Detail: {}".format(url, str(r.text)))
            if r.status_code == 404:
                return None
            return r.json()
        except Exception as ex:
            if 'r' in locals():
                print(url, r.status_code, r.text, r.request.headers)
            raise Exception("Error in get request for {}. Detail: {}".format(str(url), str(ex)))

    def do_post(self, url, headers, data=None):
        try:
            r = requests.post(url, data=data, headers=headers)
            if r.status_code not in [200, 201]:
                raise Exception("Service error for {}. Detail: {}".format(url, str(r.text)))
            return r.json()
        except Exception as ex:
            if 'r' in locals():
                print(url, r.status_code, r.text, r.request.headers)
            raise Exception("Error in post request for {}. Detail: {}".format(str(url), str(ex)))
