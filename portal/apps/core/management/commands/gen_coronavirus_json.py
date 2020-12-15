import io
import json

from django.core.management import BaseCommand

from django.template.loader import render_to_string
from django.template import Context

from core.models import Category


class Command(BaseCommand):
    help = """Generates a json with all Coronavirus category articles

Output (.json): {'articles': [{'slug': ... 'html': ...}, { .... }, ...]}

    $ ./manage.py gen_coronavirus_json <name.json>

The command saves the file ./<name.json>

Example: $ ./manage.py gen_coronavirus_json coronavirus.json"""

    def handle(self, *args, **options):
        file = args[0]
        cat = Category.objects.get(name='Coronavirus')

        res = []
        for art in cat.articles().iterator():
            template = "article/detail_min.html"
            html = render_to_string(
                template, Context(
                    {"article": art, "section": art.publication_section()}))
            html = html.replace('\n', '')
            res.append({"html": html, "slug": art.slug})
        data = {}
        data['articles'] = res

        with io.open(file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))
