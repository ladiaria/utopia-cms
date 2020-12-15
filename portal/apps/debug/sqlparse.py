# -*- coding: utf-8 -*-
import sqlparse

def print_sql(qs):
    q = qs.query.as_sql()
    statement = q[0] % q[1]
    print sqlparse.format(statement, reindent=True, keyword_case='upper')
