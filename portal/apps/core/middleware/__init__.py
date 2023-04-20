from django.utils.deprecation import MiddlewareMixin


class SameSiteMiddleware(MiddlewareMixin):
    """
    Custom "samesite" to set this value to "None" (Django seems not allowing that).
    Tihs is used now because the pip module used is not maintained and does not work in django 2.2
    """
    def process_response(self, request, response):
        if 'sessionid' in response.cookies:
            response.cookies['sessionid']['samesite'] = 'None'
        if 'csrftoken' in response.cookies:
            response.cookies['csrftoken']['samesite'] = 'None'
        return response
