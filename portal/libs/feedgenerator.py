# coding: utf-8
from django.utils.feedgenerator import Rss201rev2Feed


class DefaultFeed(Rss201rev2Feed):
    """
    RSS 2.0 + namespaces:
      - dc        http://purl.org/dc/elements/1.1/
      - content   http://purl.org/rss/1.0/modules/content/
      - media     http://search.yahoo.com/mrss/
      - image     http://www.google.com/schemas/sitemap-image/1.1
      - atom      http://www.w3.org/2005/Atom
    Also writes:
      - <atom:link rel="self" ...>
      - <content:encoded><![CDATA[...]]></content:encoded>
      - <dc:creator>...</dc:creator>
      - <media:content url="..." medium="image" />
      - <image:image>...</image:image> (opcional)
    """
    def rss_attributes(self):
        attrs = super().rss_attributes()
        attrs.update({
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:content': 'http://purl.org/rss/1.0/modules/content/',
            'xmlns:media': 'http://search.yahoo.com/mrss/',
            'xmlns:image': 'http://www.google.com/schemas/sitemap-image/1.1',
            'xmlns:atom': 'http://www.w3.org/2005/Atom',
        })
        return attrs

    def add_root_elements(self, handler):
        # base: <title>, <link>, <description>, <lastBuildDate>, etc.
        super().add_root_elements(handler)
        # agrega <atom:link rel="self" ...> si feed_url está presente
        feed_url = self.feed.get('feed_url')
        if feed_url:
            handler.addQuickElement('atom:link', None, {
                'href': feed_url,
                'rel': 'self',
                'type': 'application/rss+xml',
            })

    def add_item_elements(self, handler, item):
        # base: <title>, <link>, <description>, <guid>, <pubDate>, <category>, author, etc.
        super().add_item_elements(handler, item)

        # --- content:encoded ---
        content_html = item.get('content_html')
        if content_html:
            handler.startElement('content:encoded', {})
            # CDATA para preservar HTML
            handler._write('<![CDATA[' + content_html + ']]>')
            handler.endElement('content:encoded')

        # --- dc:creator (puede repetirse varias veces) ---
        creators = item.get('dc_creators') or []
        if isinstance(creators, (list, tuple)):
            for name in creators:
                if name:
                    handler.addQuickElement('dc:creator', name)
        elif creators:
            handler.addQuickElement('dc:creator', creators)

        # --- media:content (MRSS) ---
        image_url = item.get('image_url')
        if image_url:
            handler.startElement('media:content', {
                'url': image_url,
                'medium': 'image',
            })
            handler.endElement('media:content')

        # --- image:image (opcional, si querés emular exactamente el ejemplo TyC) ---
        image_title = item.get('image_title')
        if image_url:
            handler.startElement('image:image', {})
            handler.addQuickElement('image:loc', image_url)
            if image_title:
                handler.startElement('image:title', {})
                handler._write('<![CDATA[' + image_title + ']]>')
                handler.endElement('image:title')
            handler.endElement('image:image')
