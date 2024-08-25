#!/usr/bin/python
# -*- coding utf-8 -*-
import os
import subprocess


def make_snapshot(filename, page=0):
    output = filename.replace('.pdf', '.jpg')
    if os.path.exists(output):
        return None
        # os.unlink(output)
    print(filename)
    args = ['convert', '%s[%i]' % (filename, page), output]
    stderr = subprocess.Popen(args, stderr=subprocess.PIPE).stderr.read().strip()
    if stderr:
        print(stderr)
        LOGGER.write('\n%s\n%s\n%s\n' % (filename, ' '.join(args), stderr))

def find_pdf(dirname):
    try:
        contents = os.listdir(dirname)
    except OSError:
        return None
    for filename in contents:
        cwd = os.path.join(dirname, filename)
        if os.path.isdir(cwd):
            find_pdf(cwd)
        else:
            if filename.endswith('.pdf'):
                make_snapshot(cwd)

if __name__ == '__main__':
    LOGGER = file('%s.log' % os.sys.argv[0], 'a')
    if len(os.sys.argv) == 1:
        find_pdf(os.getcwd())
    else:
        for arg in os.sys.argv[1:]:
            if arg.endswith('.pdf'):
                make_snapshot(arg)
            else:
                find_pdf(arg)
    LOGGER.close()
