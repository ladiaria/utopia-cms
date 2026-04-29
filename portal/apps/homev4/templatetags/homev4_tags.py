from django import template

register = template.Library()


@register.filter
def slider_position_class(counter, total):
    if total > 3:
        if counter == 3:
            return "article--slider-right-edge"
        elif counter == 4:
            return "article--slider-left-edge"
    return ""
