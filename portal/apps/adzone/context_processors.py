from signupwall.utils import get_ip


def get_source_ip(request):
    return {'from_ip': get_ip(request)}
