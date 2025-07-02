from social_core.backends.google import GoogleOAuth2

class CustomGoogleOAuth2(GoogleOAuth2):
    def auth_params(self, state=None):
        params = super().auth_params(state)
        # Adding login_hint if present in the request
        login_hint = self.strategy.request_data().get('login_hint')
        if login_hint:
            params['login_hint'] = login_hint
        return params
