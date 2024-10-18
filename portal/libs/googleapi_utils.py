import json

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from django.conf import settings


def build_youtube_api():
    """
    Builds a YouTube API client using the credentials defined in settings.
    """
    auth_method, cred = getattr(settings, "UTOPIA_CMS_YOUTUBE_API_AUTH_METHOD", None), None
    build_kwargs = {}
    if auth_method:
        if auth_method == "oauth":
            cred_info = getattr(settings, "UTOPIA_CMS_YOUTUBE_API_CREDENTIALS", None)
            if cred_info:
                cred = Credentials.from_authorized_user_info(json.loads(open(cred_info).read()))
        elif auth_method == "service":
            client_secrets_file = getattr(settings, "UTOPIA_CMS_YOUTUBE_API_SECRETS", None)
            if client_secrets_file:
                cred = service_account.Credentials.from_service_account_file(client_secrets_file)
        if cred:
            build_kwargs["credentials"] = cred
    else:
        api_key = getattr(settings, "UTOPIA_CMS_GOOGLE_API_KEY", None)
        if api_key:
            build_kwargs["developerKey"] = api_key
    if build_kwargs:
        return build('youtube', 'v3', **build_kwargs)


def youtube_api_playlistItems(youtube_api, playlistId, maxResults=8, reverse=False):
    """
    Returns a list of tuples with the video id, title and type of the playlist items.
    """
    items = [
        (
            v["snippet"]["resourceId"]["videoId"], v["snippet"]["title"], "playlist"
        ) for v in youtube_api.playlistItems().list(
            part="snippet", playlistId=playlistId, maxResults=maxResults
        ).execute()["items"]
    ] if youtube_api and playlistId else []
    if reverse:
        items.reverse()
    return items


def youtube_api_embeds(youtube_api, video_ids):
    """
    Returns a tuple with the "iframe" html tag for a list of videos
    @param: vids is a list of tuples with the video in the first position)
    """
    return (
        p["player"]["embedHtml"] for p in youtube_api.videos().list(
            part='player', id=",".join(t[0] for t in video_ids), maxHeight=210
        ).execute()["items"]
    )
