"""
This views should receive a group of RTFs and convert them to Articles
What about an Article constructor from a RTF?
"""

from subprocess import check_output

def rtf2article(rtf):
    """ Receive a RTF filepath to produce an Article """
    # por ahora usando comando unrtf, TODO: ver si los tildes son un problema
    text = check_output(['unrtf', '--text'], stdin=open(rtf))
