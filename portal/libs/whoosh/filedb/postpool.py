
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""Support functions and classes implementing the KinoSearch-like external sort
merging model. This module does not contain any user-level objects.
"""
from __future__ import division
from __future__ import unicode_literals

from builtins import next
from builtins import chr
from past.utils import old_div
from builtins import object
import os, struct, tempfile
from marshal import dumps, loads
from heapq import heapify, heapreplace, heappop

import whoosh.filedb.structfile as structfile

_int_size = struct.calcsize("!i")

# Utility functions

def encode_posting(fieldNum, text, doc, data):
    """Encodes a posting as a string, for sorting."""
    
    return "".join([struct.pack("!i", fieldNum),
                    text.encode("utf8"),
                    chr(0),
                    struct.pack("!i", doc),
                    dumps(data)
                    ])

def decode_posting(posting):
    """Decodes an encoded posting string into a
    (field_number, text, document_number, data) tuple.
    """
    
    field_num = struct.unpack("!i", posting[:_int_size])[0]
    
    zero = posting.find(chr(0), _int_size)
    text = posting[_int_size:zero].decode("utf8")
    
    docstart = zero + 1
    docend = docstart + _int_size
    doc = struct.unpack("!i", posting[docstart:docend])[0]
    
    data = loads(posting[docend:])
    
    return field_num, text, doc, data

def merge(run_readers, max_chunk_size):
    # Initialize a list of terms we're "current"ly
    # looking at, by taking the first posting from
    # each buffer.
    #
    # The format of the list is
    # [("encoded_posting", reader_number), ...]
    #
    # The list is sorted, and the runs are already
    # sorted, so the first term in this list should
    # be the absolute "lowest" term.
    
    current = [(next(r), i) for i, r
               in enumerate(run_readers)]
    heapify(current)
    
    # The number of active readers (readers with more
    # postings to available), initially equal
    # to the total number of readers/buffers.
    
    active = len(run_readers)
    
    # Initialize the output buffer, and a variable to
    # keep track of the output buffer size. This buffer
    # accumulates postings from the various buffers in
    # proper sorted order.
    
    output = []
    outputBufferSize = 0
    
    while active > 0:
        # Get the first ("encoded_posting", reader_number)
        # pair and add it to the output buffer.
        
        p, i = current[0]
        output.append(p)
        outputBufferSize += len(p)
        
        # If the output buffer is full, "flush" it by yielding
        # the accumulated postings back to the parent writer
        # and clearing the output buffer.
        
        if outputBufferSize > max_chunk_size:
            for p in output:
                yield decode_posting(p)
            output = []
            outputBufferSize = 0
        
        # We need to replace the posting we just added to the output
        # by getting the next posting from the same buffer.
        
        if run_readers[i] is not None:
            # Take the first posting from buffer i and insert it into the
            # "current" list in sorted order.
            # The current list must always stay sorted, so the first item
            # is always the lowest.
            
            p = next(run_readers[i])
            if p:
                heapreplace(current, (p, i))
            else:
                heappop(current)
                active -= 1
    
    # If there are still terms in the "current" list after all the
    # readers are empty, dump them into the output buffer.
    
    if len(current) > 0:
        output.extend([p for p, i in current])
    
    # If there's still postings in the output buffer, yield
    # them all to the parent writer.
    
    if len(output) > 0:
        for p in output:
            yield decode_posting(p)


# Classes

class RunReader(object):
    """An iterator that yields posting strings from a "run" on disk.
    This class buffers the reads to improve efficiency.
    """
    
    def __init__(self, stream, count, buffer_size):
        """
        :param stream: the file from which to read.
        :param count: the number of postings in the stream.
        :param buffer_size: the size (in bytes) of the read buffer to use.
        """
        
        self.stream = stream
        self.count = count
        self.buffer_size = buffer_size
        
        self.buffer = []
        self.pointer = 0
        self.finished = False
    
    def close(self):
        self.stream.close()
    
    def _fill(self):
        # Clears and refills the buffer.
        
        # If this reader is exhausted, do nothing.
        if self.finished:
            return
        
        # Clear the buffer.
        buffer = self.buffer = []
        
        # Reset the index at which the next() method
        # reads from the buffer.
        self.pointer = 0
        
        # How much we've read so far.
        so_far = 0
        count = self.count
        
        while so_far < self.buffer_size:
            if count <= 0:
                break
            p = self.stream.read_string()
            buffer.append(p)
            so_far += len(p)
            count -= 1
        
        self.count = count
    
    def __iter__(self):
        return self
    
    def __next__(self):
        assert self.pointer <= len(self.buffer)
        
        if self.pointer == len(self.buffer):
            self._fill()
        
        # If after refilling the buffer is still empty, we're
        # at the end of the file and should stop. Probably this
        # should raise StopIteration instead of returning None.
        if len(self.buffer) == 0:
            self.finished = True
            return None
        
        r = self.buffer[self.pointer]
        self.pointer += 1
        return r


class PostingPool(object):
    """Represents the "pool" of all postings to be sorted. As documents are added,
    this object writes out "runs" of sorted encoded postings. When all documents
    have been added, this object merge sorts the runs from disk, yielding decoded
    postings to the SegmentWriter.
    """
    
    def __init__(self, limit):
        """
        :param limit: the maximum amount of memory to use at once
            for adding postings and the merge sort.
        """
        
        self.limit = limit
        self.size = 0
        self.postings = []
        self.finished = False
        
        self.runs = []
        self.count = 0
    
    def add_posting(self, field_num, text, doc, data):
        """Adds a posting to the pool."""
        
        if self.finished:
            raise Exception("Can't add postings after you iterate over the pool")
        
        if self.size >= self.limit:
            #print "Flushing..."
            self._flush_run()
        
        posting = encode_posting(field_num, text, doc, data)
        self.size += len(posting)
        self.postings.append(posting)
        self.count += 1
    
    def _flush_run(self):
        # Called when the memory buffer (of size self.limit) fills up.
        # Sorts the buffer and writes the current buffer to a "run" on disk.
        
        if self.size > 0:
            tempfd, tempname = tempfile.mkstemp(".run")
            runfile = structfile.StructFile(os.fdopen(tempfd, "w+b"))
            
            self.postings.sort()
            for p in self.postings:
                runfile.write_string(p)
            runfile.flush()
            runfile.seek(0)
            
            self.runs.append((runfile, self.count))
            #print "Flushed run:", self.runs
            
            self.postings = []
            self.size = 0
            self.count = 0
    
    def __iter__(self):
        # Iterating the PostingPool object performs a merge sort of
        # the runs that have been written to disk and yields the
        # sorted, decoded postings.
        
        if self.finished:
            raise Exception("Tried to iterate on PostingPool twice")
        
        run_count = len(self.runs)
        if self.postings and run_count == 0:
            # Special case: we never accumulated enough postings to flush
            # to disk, so the postings are still in memory: just yield
            # them from there.
            
            self.postings.sort()
            for p in self.postings:
                yield decode_posting(p)
            return
        
        if not self.postings and run_count == 0:
            # No postings at all
            return
        
        if self.postings:
            self._flush_run()
            run_count = len(self.runs)
        
        #This method does an external merge to yield postings
        #from the (n > 1) runs built up during indexing and
        #merging.
        
        # Divide up the posting pool's memory limit between the
        # number of runs plus an output buffer.
        max_chunk_size = int(old_div(self.limit, (run_count + 1)))
        
        run_readers = [RunReader(run_file, count, max_chunk_size)
                       for run_file, count in self.runs]
        
        for decoded_posting in merge(run_readers, max_chunk_size):
            yield decoded_posting
        
        for rr in run_readers:
            assert rr.count == 0
            rr.close()
        
        # And we're done.
        self.finished = True






        