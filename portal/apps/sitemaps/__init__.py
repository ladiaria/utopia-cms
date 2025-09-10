
from django.contrib.sitemaps import Sitemap
from libs.utils import get_site_name


class NewsSitemap(Sitemap):
    # This limit is defined by Google. See the index documentation at
    # http://www.google.com/support/webmasters/bin/answer.py?hl=en&answer=74288
    limit = 1000

    def publication_date(self, obj):
        return obj.date_published

    def get_url_info(self, item, current_site):
        url_info = super(NewsSitemap, self).get_url_info(item, current_site)
        url_info.update(
            {
                'publication_date': self._get('publication_date', item, None),
                'keywords': self._get('keywords', item, None),
            }
        )
        return url_info


class NewsSitemap48hs(Sitemap):
    limit = 1000

    publication_name = get_site_name()
    publication_language = "es"

    def publication_date(self, obj):
        return getattr(obj, 'date_published', None)

    def headline(self, obj):
        return getattr(obj, 'headline', None)

    def keywords(self, obj):
        return getattr(obj, 'keywords', '')

    def news_url_info(self, item, current_site, protocol):
        loc_path = self._get('location', item)
        if not loc_path.startswith('http'):
            loc = f"{protocol}://{current_site.domain}{loc_path}"
        else:
            loc = loc_path

        return {
            'location': loc,
            'publication_date': self.publication_date(item),
            'title': self.headline(item),
            'keywords': self.keywords(item),
            'publication_name': self.publication_name,
            'publication_language': self.publication_language,
        }
