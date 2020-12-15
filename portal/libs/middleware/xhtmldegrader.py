"""
XHTML Degrader Middleware.

When sending contents with the XHTML media type, application/xhtml+xml, this
module checks to ensure that the user agent (web browser) is capable of
rendering it.  If not, it changes the media type to text/html and makes the
contents more "HTML-friendly" (as per the XHTML 1.0 HTML Compatibility
Guidelines).
"""

import re

_MEDIA_TYPE_RE =  re.compile(r'application\/xhtml\+xml')

_EMPTY_TAG_END_RE =  re.compile(r'(?<=\S)\/\>')

_PROCESSING_INSTRUCTION_RE = re.compile(r'\<\?.*\?\>')

def _supports_xhtml(request):
    """Examines an HTTP request header to determine whether the user agent
    supports the XHTML media type (application/xhtml+xml).  Returns True or
    False."""
    if '/xhtml+xml' in request.META.get('HTTP_ACCEPT', '').lower():
        # User agent claims to support the XHTML media type.
        return True
    else:
        # No reference to XHTML support.
        return False

class XhtmlDegraderMiddleware(object):
    """Django middleware that "degrades" any contents sent as XHTML if the
    requesting browser doesn't support the XHTML media type.  Degrading involves
    switching the content type to text/html, removing XML processing
    instructions, etc.

    If the HTTP response is already set to text/html, or set to any media type
    other than application/xhtml+xml, this middleware will have no effect.
    """

    def process_response(self, request, response):
        # Check if this is XHTML, and check if the user agent supports XHTML.
        if response['Content-Type'].split(';')[0] != 'application/xhtml+xml' \
                or _supports_xhtml(request):
            # The content is fine, simply return it.
            return response
        # If the response has already been compressed we can't modify it
        # further, so just return it.  (N.B. if you use GZipMiddleware, you
        # should ensure that it's listed in MIDDLEWARE_CLASSES before
        # XhtmlDegraderMiddleware, to allow the XHTML Degrader to act first.)
        if response.has_header('Content-Encoding'):
            # Already compressed, so we can't do anything useful with it.
            return response
        # The content is XHTML, and the user agent doesn't support it.
        # Fix the media type:
        response['Content-Type'] = _MEDIA_TYPE_RE.sub('text/html',
                response['Content-Type'], 1)
        if 'charset' not in response['Content-Type']:
            response['Content-Type'] += '; charset=utf-8'
        # Modify the response contents as required:
        # Remove any XML processing instructions:
        response.content = _PROCESSING_INSTRUCTION_RE.sub('',
                response.content)
        # Ensure there's a space before the trailing '/>' of empty elements:
        response.content = _EMPTY_TAG_END_RE.sub(' />',
                response.content)
        # Lose any excess whitespace:
        response.content = response.content.strip()
        if response.content[0:9] != '<!DOCTYPE':
            # Add a DOCTYPE, so that the user agent isn't in "quirks" mode.
            response.content = '<!DOCTYPE html>\n' + response.content
        return response
