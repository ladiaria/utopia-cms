# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from ..models import YouTubeVideo

from django.shortcuts import render

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# to_response = render('videologue/templates/youtubevideo/')

def youtubevideo_list(request):
    pass

def losinformantes_list(request):
	query =  YouTubeVideo.objects.all().order_by('-date_created')
	paginator = Paginator(query, 8)
	page = request.GET.get('page')
	try:
	    videos = paginator.page(page)
	except PageNotAnInteger:
	    videos = paginator.page(1)
	except EmptyPage:
	    videos = paginator.page(paginator.num_pages)

	return render(request, 'videologue/templates/youtubevideo/archivo.html', {"videos": videos})