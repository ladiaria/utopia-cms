from django.core import serializers
from tagging.models import Tag
from django.http import HttpResponse
from django.utils import simplejson
from django.utils.datastructures import MultiValueDictKeyError

def list_tags(request):
	try:
	    tags = Tag.objects.filter(name__istartswith=request.GET['term']).values_list('name', flat=True)
	except MultiValueDictKeyError:
		tags = []

	return JsonResponse([x.encode('utf-8') for x in tags])


class JsonResponse(HttpResponse):
    """
    HttpResponse descendant, which return response with ``application/json`` mimetype.
    """
    def __init__(self, data):
        super(JsonResponse, self).__init__(content=simplejson.dumps(data), mimetype='application/json')
