from __future__ import unicode_literals

from django.contrib.sitemaps import Sitemap


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
