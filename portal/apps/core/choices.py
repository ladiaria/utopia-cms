from __future__ import unicode_literals

from .models import Section


# TODO: are NOTA_* used?
NOTA_H1 = 'H1'
NOTA_H2 = 'H2'
NOTA_H3 = 'H3'


def section_choices():
    """
    Returns a hierarchical and ordered choice structure for the sections gruped by category giving precedence to the
    sections with category.
    TODO: Obtain the first "-----" default option in a more elegant way.
    """
    # Sections with category
    result, result_item, prev_category = (('', '---------'), ), None, None
    for s in Section.objects.filter(category__isnull=False).order_by('category__name', 'name'):
        if s.category != prev_category:
            if result_item:
                result += (result_item, )
            result_item = (s.category.name, ((s.id, s.name), ))
        else:
            result_item = (result_item[0], result_item[1] + ((s.id, s.name), ))
        prev_category = s.category
    if result_item:
        result += (result_item, )
    # Sections with publications and without category
    result_item = ()
    for s in Section.objects.filter(publications__isnull=False, category__isnull=True).distinct().order_by('name'):
        result_item += ((s.id, s.name), )
    if result_item:
        result += (("Secciones sin área", result_item), )
    # Sections without publications and without category
    result_item = ()
    for s in Section.objects.filter(publications__isnull=True, category__isnull=True).order_by('name'):
        result_item += ((s.id, s.name), )
    if result_item:
        result += (("Secciones sin área ni publicaciones", result_item), )
    return result
