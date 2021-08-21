from django import forms

from models import YouTubeVideo
import re

YT_RE = re.compile(r'(?:v|embed)[=\/]([\w_-]{11})')


class YouTubeVideoForm(forms.ModelForm):
    class Meta:
        model = YouTubeVideo
        fields = "__all__"

    def clean(self):
        cleaned_data = super(YouTubeVideoForm, self).clean()
        url = cleaned_data.get("url")
        if not url or not YT_RE.findall(url):
            msg = u"No es una url de youtube valida"
            self._errors["url"] = self.error_class([msg])

        return cleaned_data
