from core.models import Journalist, Article, Section

# changes all journalists job in Section posturas from PE to CO


def get_exception_set():
    e1 = Journalist.objects.get(slug='soledad-platero')
    e2 = Journalist.objects.get(slug='andres-alsina')
    e3 = Journalist.objects.get(slug='andres-prieto')
    e4 = Journalist.objects.get(slug='antonio-romano')
    e5 = Journalist.objects.get(slug='ariel-scher')
    e6 = Journalist.objects.get(slug='carlos-demasi')
    e7 = Journalist.objects.get(slug='carlos-rehermann')
    e8 = Journalist.objects.get(slug='danilo-espino')
    e9 = Journalist.objects.get(slug='emilio-martinez-muracciole')
    e10 = Journalist.objects.get(slug='facundo-franco')
    e11 = Journalist.objects.get(slug='fernando-errandonea')
    e12 = Journalist.objects.get(slug='fernando-esponda')
    e13 = Journalist.objects.get(slug='fiorella-buzeta-carminatti')
    e14 = Journalist.objects.get(slug='florencia-dansilio')
    e15 = Journalist.objects.get(slug='gerardo-leibner')
    e16 = Journalist.objects.get(slug='guillermo-garat')
    e17 = Journalist.objects.get(slug='guillermo-lamolle')
    e18 = Journalist.objects.get(slug='jorge-burgell')
    e19 = Journalist.objects.get(slug='mariana-greif')
    e20 = Journalist.objects.get(slug='martin-rodriguez')
    e21 = Journalist.objects.get(slug='micaela-dominguez-prost')
    e22 = Journalist.objects.get(slug='ricardo-antunez')
    e23 = Journalist.objects.get(slug='romulo-martinez-chenlo')
    e24 = Journalist.objects.get(slug='rosario-lazaro-igoa')
    e25 = Journalist.objects.get(slug='simon-lopez-ortega')
    e26 = Journalist.objects.get(slug='the-intercept')
    e27 = Journalist.objects.get(slug='veronica-pellejero')

    lst = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10,
           e11, e12, e13, e14, e15, e16, e17, e18, e19, e20,
           e21, e22, e23, e24, e25, e26, e27]

    exception_set = set(lst)

    return exception_set


def main():
    exceptions = get_exception_set()
    s = Section.objects.get(slug='posturas')
    articles = s.articles_core.filter(
        is_published=True).distinct().order_by('-date_published')
    journalists = set()
    for article in articles:
        jj = article.byline.all()
        for j in jj:
            if j not in exceptions:
                journalists.add(j)
            else:
                print('Exception: %s' % j.name)

    print('converting from PE to CO...')
    for journalist in journalists:
        if journalist.job == u'PE':
            journalist.job = u'CO'
            journalist.save()
    print('script finished')
