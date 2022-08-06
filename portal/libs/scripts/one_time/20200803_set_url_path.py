# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from progress.bar import Bar

from core.models import Article


articles_to_set = Article.objects.filter(is_published=True, url_path=u'')
bar = Bar('Processing ...', max=articles_to_set.count())

for a in articles_to_set.iterator():

    try:
        a.url_path = a.build_url_path()
        a.save()
    except Exception as e:
        print(u"\nArticle %d: not modified, an error occurred when saving it - e" % (a.id, e))

    bar.next()

bar.finish()
