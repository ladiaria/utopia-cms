from django import forms
from django.contrib.contenttypes.models import ContentType


RATING_CHOICES = ((1,1), (2,2), (3,3), (4,4), (5,5),)

class RatingForm(forms.Form):
    
    content_type_id = forms.CharField(widget=forms.HiddenInput())
    object_id = forms.CharField(widget=forms.HiddenInput())

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={'class':'star'},),
    )
    
    def __init__(self, object, *args, **kwargs):
        content_type_id = ContentType.objects.get_for_model(object).id
        self.base_fields['content_type_id'].initial = content_type_id            
        self.base_fields['object_id'].initial = object.id
        self.base_fields['rating'].initial = object.rating_score

        super(RatingForm, self).__init__(*args, **kwargs)

      