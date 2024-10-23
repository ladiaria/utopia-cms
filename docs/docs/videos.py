# -*- coding: utf-8 -*-
"""
Instructions to generate the necessary credentials to access the youtube api from backend:

In the google project:
  - include the youtube api from the library.
  - create an api key and restrict it to use the youtube api (this step is not confirmed if it is necessary).
  - in the oauth client id, authorize the url http://localhost:8080/.
  - download the secret to use it in the following code.
"""

import os

import google_auth_oauthlib.flow  # pip install google_auth_oauthlib


scopes = ["https://www.googleapis.com/auth/youtube"]


def main():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    client_secrets_file = "YOUR_CLIENT_SECRET_FILE.json"
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
    credentials = flow.run_local_server()
    # folow the google dialogs to authorize this credentials use the account you want to request the youtube api
    # then save the credentials.json file to use for request the youtube api
    with open('credentials.json', 'w') as f:
        f.write(credentials.to_json())


"""
# example usage to get file details, not remember now, but it could be return less data if the user hitting the api is
# not the owner of the videos.

api_service_name = "youtube"
api_version = "v3"
youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

request = youtube.videos().list(
    part="fileDetails",
    id="tG-7S8Hs5AY,KoRTsT9kz94"
)
response = request.execute()

print(response)
"""
