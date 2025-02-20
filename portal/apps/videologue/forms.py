from django import forms

from .models import YouTubeVideo, YT_RE


class YouTubeVideoForm(forms.ModelForm):
    class Meta:
        model = YouTubeVideo
        fields = "__all__"

    def clean_url(self):
        url = self.cleaned_data.get("url")
        yt_id = YT_RE.findall(url)
        if url and yt_id:
            return YouTubeVideo.format_url(yt_id[0])
        else:
            self.add_error("url", "No es una url de youtube válida")
