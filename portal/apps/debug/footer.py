#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from django.dispatch import dispatcher
from django.core.signals import request_started
from django.test.signals import template_rendered
from django.conf import settings
from django.db import connection
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe

USE_PYGMENTS = False
try:
    import textwrap
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import SqlLexer
    from pygments.styles import get_style_by_name
    USE_PYGMENTS = True
except ImportError:
    pass

if USE_PYGMENTS:
    WRAP = 120
    STYLE = get_style_by_name('colorful')

HEIGHT = '240px' # or '100%' if full height is wished

TEMPLATE = """
<div id="debug" style="clear:both;">
<a href="#debugbox"
    onclick="this.style.display = 'none';
        document.getElementById('debugbox').style.display = 'block';
        return false;"
    style="font-size: small; color: red; text-decoration: none; display: block; margin: 12px;"
>+</a>

<div style="display: none;clear: both; border: 1px solid red; padding: 12px; {{ height }} margin: 12px; overflow: auto;"
     id="debugbox">

<p>Server-time taken: {{ server_time|floatformat:"5" }} seconds</p>
<p>Templates used:</p>
{% if templates %}
<ol>
    {% for template in templates %}
        <li><strong>{{ template.0 }}</strong> loaded from <samp>{{ template.1 }}</samp></li>
    {% endfor %}
</ol>
{% else %}
    None
{% endif %}
<p>Template path:</p>
{% if template_dirs %}
    <ol>
    {% for template in template_dirs %}
        <li>{{ template }}</li>
    {% endfor %}
    </ol>
{% else %}
    None
{% endif %}
<p>SQL executed:</p>
{% if sql %}
<ol>
{% for query in sql %}
    <li><pre>{{ query.sql|linebreaksbr }}</pre><p>took {{ query.time|floatformat:"3" }} seconds</p></li>
{% endfor %}
</ol>
<p>Total SQL time: {{ sql_total }}</p>
{% else %}
    None
{% endif %}
</div>
</div>
</body>
"""

# Monkeypatch instrumented test renderer from django.test.utils - we could use
# django.test.utils.setup_test_environment for this but that would also set up
# e-mail interception, which we don't want
from django.test.utils import instrumented_test_render
from django.template import Template, Context
if Template.render != instrumented_test_render:
    Template.original_render = Template.render
    Template.render = instrumented_test_render
# MONSTER monkey-patch
old_template_init = Template.__init__
def new_template_init(self, template_string, origin=None, name='<Unknown Template>'):
    old_template_init(self, template_string, origin, name)
    self.origin = origin
Template.__init__ = new_template_init

class DebugFooterMiddleware:
    def process_request(self, request):
        self.time_started = time.time()
        self.templates_used = []
        self.contexts_used = []
        self.sql_offset_start = len(connection.queries)
        """
        dispatcher.connect(
            self._storeRenderedTemplates, signal=template_rendered
        )
        """

    def process_response(self, request, response):
        # Only include debug info for text/html pages not accessed via Ajax
        if 'text/html' not in response['Content-Type']:
            return response
        if request.is_ajax():
            return response
        if not settings.DEBUG:
            return response
        if response.status_code != 200:
            return response

        templates = [
            (t.name, t.origin and t.origin.name or 'No origin')
            for t in self.templates_used
        ]
        sql_queries = connection.queries[self.sql_offset_start:]
        # Reformat sql queries a bit
        sql_total = 0.0

        for query in sql_queries:
            query['sql'] = highlight_sql(query['sql'])
            sql_total += float(query['time'])

        #import pdb; pdb.set_trace()


        debug_content = Template(TEMPLATE).render(Context({
            'server_time': time.time() - self.time_started,
            'templates': templates,
            'sql': sql_queries,
            'sql_total': sql_total,
            'template_dirs': settings.TEMPLATE_DIRS,
            'height': 'height: %s;' % (HEIGHT, ),
        }))

        content = response.content
        response.content = force_unicode(content).replace('</body>', debug_content)

        #import pdb; pdb.set_trace()
        return response

    def _storeRenderedTemplates(self, signal, sender, template, context):
        self.templates_used.append(template)
        self.contexts_used.append(context)

def highlight_sql(sql):
    if USE_PYGMENTS:
        sql = mark_safe(highlight(textwrap.fill(sql, WRAP),
                                  SqlLexer(encoding='utf-8'),
                                  HtmlFormatter(encoding='utf-8',
                                                noclasses=True,
                                                style=STYLE)
                                  )
                        )
    else:
        sql = reformat_sql(sql)
    return sql

def reformat_sql(sql):
    sql = sql.replace('`,`', '`, `')
    sql = sql.replace('` FROM `', '` \n  FROM `')
    sql = sql.replace('` WHERE ', '` \n  WHERE ')
    sql = sql.replace(' ORDER BY ', ' \n  ORDER BY ')
    return sql
