# -*- coding: utf-8 -*-
# from pympler.asizeof import asizeof
from pympler.muppy import muppy, refbrowser, summary

def output_function(o):
    return str(type(o))

class MemoryMiddleware(object):
    """
    Measure memory taken by requested view, and response
    """

    def process_request(self, request):
        req = request.META['PATH_INFO']
        if req.find('site_media') == -1:
            self.start_objects = muppy.get_objects()

    def process_response(self, request, response):
        req = request.META['PATH_INFO']
        if req.find('site_media') == -1:
            print req
            self.end_objects = muppy.get_objects()
            sum_start = summary.summarize(self.start_objects)
            sum_end = summary.summarize(self.end_objects)
            diff = summary.get_diff(sum_start, sum_end)
            summary.print_(diff)
            #print '~~~~~~~~~'
            #cb = refbrowser.ConsoleBrowser(response, maxdepth=2, str_func=output_function)
            #cb.print_tree()
            print '~~~~~~~~~'
            a = asizeof(response)
            print 'Total size of response object in kB: %s' % str(a/1024.0)
            print '~~~~~~~~~'
            a = asizeof(self.end_objects)
            print 'Total size of end_objects in MB: %s' % str(a/1048576.0)
            b = asizeof(self.start_objects)
            print 'Total size of start_objects in MB: %s' % str(b/1048576.0)
            print '~~~~~~~~~'
        return response
