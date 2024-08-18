# -*- coding: utf-8 -*-
from progress.bar import Bar

from core.models import Article, ArticleRel, Publication, ArticleUrlHistory


articles_to_set = Article.objects.filter(
    is_published=True, sections__isnull=False, main_section__isnull=True).distinct()
pubs_ld_and_fs = Publication.objects.filter(slug__in=('ladiaria', 'findesemana'))
bar = Bar('Processing', max=articles_to_set.count())

for a in articles_to_set.iterator():

    warn1, warn2, filter_kwargs = False, False, {'article': a}
    if a.publication:
        # article has pub
        if a.publication in pubs_ld_and_fs:
            filter_kwargs['edition__publication__in'] = pubs_ld_and_fs
        else:
            filter_kwargs['edition__publication'] = a.publication

        target_editions = ArticleRel.objects.filter(**filter_kwargs).order_by('edition__date_published')
        if target_editions:
            # set the oldest as the main one
            a.main_section = target_editions[0]
        else:
            target_editions = ArticleRel.objects.filter(article=a).order_by('edition__date_published')
            # set the oldest as the main one and print warn
            a.main_section, warn1 = target_editions[0], True
    else:
        # article has not publication
        # set the oldest article_rel as the main one and print warn
        target_editions = ArticleRel.objects.filter(**filter_kwargs).order_by('edition__date_published')
        a.main_section, warn2 = target_editions[0], True

    a.publication = None
    try:
        a.save()
        if warn1:
            print(u"\nArtículo %d: pub. principal establecida: %s" % (a.id, a.main_section))
        if warn2:
            print(u"\nArtículo %d: (no tenía pub. asociada) pub. principal establecida: %s" % (a.id, a.main_section))
        # add new url to the history
        new_url = a.get_absolute_url()
        if not a.articleurlhistory_set.filter(absolute_url=new_url).exists():
            ArticleUrlHistory.objects.create(article=a, absolute_url=new_url)
    except Exception as e:
        print(u"\nArticle %d: not modified, an error occurred when saving it - e" % (a.id, e))

    bar.next()

bar.finish()
