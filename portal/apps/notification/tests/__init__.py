from ..models import NOTICE_MEDIA


def get_backend_id(backend_name):
    for bid, bname in NOTICE_MEDIA:
        if bname == backend_name:
            return bid
    return None
