#!/usr/bin/python
# -*- coding: utf-8 -*-
from urllib2 import urlopen
import re

def get_html():
    YOUTUBE_URL = 'http://www.youtube.com/profile?user=LosInformantes&view=videos&start=%i'
    handler = file('rdesc.youtube', 'a')
    for jump in (0, 20, 40, 60, 80, 100, 120):
        handler.write('%s\n' % urlopen(YOUTUBE_URL % jump).read())
    handler.close()
    print 'Fertig.'

def get_links(html):
    vre = re.compile(r'/watch\?v=.{11}')
    handler = file('reportedescomunal', 'a')
    used = []
    for link in vre.findall(html):
        if link not in used:
            used.append(link)
            handler.write('http://www.youtube.com%s\n' % link)
    handler.close()
    print 'Fertig.'

def get_video(url):
    import subprocess

    if len(url) == 11:
        url = 'http://www.youtube.com/watch?v=%s' % url
    elif len(url) < 11:
        return
    args = ['youtube-dl', '-b', '-g', '-2', url]
    fre = re.compile(r'\d{2} \d{2} \d{2}')
    stdout = subprocess.Popen(args, stdout=subprocess.PIPE).stdout.read().strip()
    day, month, year = fre.findall(stdout)[0].split(' ')
    title, flv_url = stdout.split('\n')
    print '%s (%s/%s/%s)' % (title, day, month, year)
    args = ['youtube-dl', '-b', url]

if __name__ == '__main__':
    import sys

    # get_html()
    # get_links(file('rdesc.youtube', 'r').read())
    handler = file('reportedescomunal', 'r')
    x = 0
    for link in handler.readlines():
        get_video(link)
        x += 1
        if x == 10:
            raise Exception
    sys.exit()
