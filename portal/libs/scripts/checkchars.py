#!/usr/bin/python2.5
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from string import lower

def check_chars(line):
    chars = ' aábcdeéfghiíjklmnñoópqrstuúvwxyz0123456789'
    bits = [chunk.strip().strip('"') for chunk in line.split(',')]
    for bit in bits:
        for char in bit:
            if lower(char) not in chars:
                print('%s, %s, %s' % (bits[0], bits[1], bits[2]))
                return None

handler = open('clientes_activos-20090827.csv', 'r')
for line in handler.readlines():
    check_chars(line)
