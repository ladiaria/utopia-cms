#!/usr/bin/python
# -*- coding utf-8 -*-
import urllib, urllib2
import re
import os

LADIARIA_DOMAIN = 'http://www.ladiaria.com.uy/'
LADIARIA_URL = LADIARIA_DOMAIN + '?q=node/%i'
LADIARIA_RE = r'/files/images/(.*\d{8}.*\.jpg)'
ldre = re.compile(LADIARIA_RE)
logger = file('ladiaria.com.uy.log', 'a')
for x in range(1, 900):
    html = None
    url = LADIARIA_URL % x
    try:
        html = urllib2.urlopen(url)
    except urllib2.HTTPError:
        pass
    if html:
        print LADIARIA_URL % x
        for filename in ldre.findall(html.read()):
            content = None
            filename = filename.replace('.preview', '')
            print filename
            file_url = '%sfiles/images/%s' % (
                LADIARIA_DOMAIN, urllib.quote(filename))
            try:
                content = urllib2.urlopen(file_url)
            except urllib2.HTTPError:
                pass
            if content:
                if not os.path.exists(filename.replace(' ', '-')):
                    handler = file(filename.replace(' ', '-'), 'w+')
                    handler.write(content.read())
                    handler.close()
                    logger.write('%s\n' % url)
                    logger.write('    %s\n' % filename)
                else:
                    print 'file exists'
        print ''
logger.close()
