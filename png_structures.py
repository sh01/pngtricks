#!/usr/bin/env python
#Copyright 2007 Sebastian Hagen
# This file is part of pngtricks.

# pngtricks is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2
# as published by the Free Software Foundation

# pngtricks is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import struct
import binascii
import cStringIO
import zlib

CMP_METHOD_INFLATE = 0

class PNGError(StandardError):
   pass

class PNGFormatError(PNGError):
   pass

class CRCError(PNGError):
   pass

class PngImage:
   signature = '\x89PNG\r\n\x1a\n'
   __slots__ = ('chunks',)
   
   def __init__(self, chunks=None):
      if (chunks is None):
         chunks = []
      self.chunks = chunks
   
   @classmethod
   def build_from_stream(cls, stream):
      sig = stream.read(len(cls.signature))
      if (sig != cls.signature):
         raise PNGFormatError('Start of data does not match %r' % cls.signature)
      
      chunks = []
      while (True):
         data_length_raw = stream.read(4)
         if (data_length_raw == ''):
            break

         data_length = struct.unpack('>I', data_length_raw)[0]
         chunk_type = stream.read(4)
         assert(len(chunk_type) == 4)
         data_raw = stream.read(data_length)
         assert (len(data_raw) == data_length)
         crc_raw = stream.read(4)
         assert (len(crc_raw) == 4)
         crc = struct.unpack('>i', crc_raw)[0]
         
         chunks.append(PngChunk.build(chunk_type, data_raw, crc))
         if (chunk_type == 'IEND'):
            tail_data = stream.read()
            if (tail_data):
               chunks.append(PngChunk.build('_TAIL', tail_data, None))
            break
         
      return cls(chunks)
      
   @classmethod
   def build_from_string(cls, string):
      return cls.build_from_stream(cStringIO.StringIO(string))
      
   def __repr__(self):
      return '%s(%r)' % (self.__class__.__name__, self.chunks)

   def list_chunks_hr(self, fmtstr = '%6s %10s %16s', linesep='\n'):
      resultlist = [fmtstr % ('type', 'data_len', 'crc')]
      
      for chunk in self.chunks:
         resultlist.append(chunk.chunk_summary_fmt_hr(fmtstr, linesep))
      return linesep.join(resultlist)

   def get_binstring(self):
      retval = self.signature
      for chunk in self.chunks:
         retval += chunk.get_binstring()
      return retval

   def get_imagedata(self):
      if (self.chunks[0].chunk_type != 'IHDR'):
         raise PNGError('Expected first chunk to be of type IHDR, found %s.' % (chunks[0],))
      cmp_method = self.chunks[0].get_compression_method()
      if (cmp_method != CMP_METHOD_INFLATE):
         raise PNGError('Unknown compression_method %d.' % (cmp_method,))

      id_raw = ''.join([chunk.data for chunk in self.chunks if (chunk.chunk_type == 'IDAT')])
      return zlib.decompress(id_raw)
      

class PngChunk:
   attributes = ()
   __slots__ = ('chunk_type', 'data', 'crc')
   def __init__(self, chunk_type, data, crc=None):
      self.chunk_type = chunk_type
      self.data = data
      crc_computed = self.crc_compute()
      if (crc == None):
         crc = crc_computed
      elif (crc != crc_computed):
         raise CRCError('Computed crc %d, got %r.' % (crc_computed, crc))
      
      self.crc = crc
   
   @classmethod
   def build(cls, chunk_type, *args, **kwargs):
      varspace = globals()
      cls_name = (cls.__name__ + chunk_type)
      if (cls_name in varspace):
         cls = varspace[cls_name]
      return cls(chunk_type, *args, **kwargs)
   
   def crc_compute(self):
      return binascii.crc32(self.chunk_type + self.data)
   
   def __repr__(self):
      return '%r(%r)' % (self.__class__.__name__, (self.chunk_type, self.data, self.crc))

   def __str__(self):
      return '<%s type: %r data-length: %d crc: %s>' % (self.__class__.__name__, self.chunk_type, len(self.data), self.crc)

   def _get_u8(self, index):
      return struct.unpack('>B', self.data[index:index+1])[0]

   def _get_u32(self, index):
      return struct.unpack('>I', self.data[index:index+4])[0]

   def _set_u32(self, index, val):
      self.data = self.data[:index] + struct.pack('>I', val) + self.data[index+4:]

   def chunk_summary_fmt_hr(self, fmtstring = '%6s %10s %16s', linesep='\n', attributes_list=True):
      retval = fmtstring % (self.chunk_type, len(self.data), self.crc)
      if (attributes_list):
         for attribute in self.attributes:
            info_str = '  %20s: %10s' % (attribute, getattr(self, 'get_%s' % attribute)())
            retval += ('%s %s' % (linesep, info_str))
            
      return retval
   
   def get_binstring(self):
      return '%s%s%s%s' % (struct.pack('>I', len(self.data)), self.chunk_type, self.data, struct.pack('>i', self.crc))

class PngChunkIHDR(PngChunk):
   attributes = ('width', 'height', 'bit_depth', 'color_type', 'compression_method', 'filter_method', 'interlace_method')
   def get_width(self):
      return self._get_u32(0)
   def get_height(self):
      return self._get_u32(4)
   def get_bit_depth(self):
      return self._get_u8(8)
   def get_color_type(self):
      return self._get_u8(9)
   def get_compression_method(self):
      return self._get_u8(10)
   def get_filter_method(self):
      return self._get_u8(11)
   def get_interlace_method(self):
      return self._get_u8(12)


class PngChunkgAMA(PngChunk):
   attributes = ('gamma',)
   def get_gamma(self):
      return self._get_u32(0) / 100000.0
   
   def set_gamma(self, val):
      retval = self._set_u32(0, int(100000*val))
      self.crc = self.crc_compute()
      return retval

class PngChunk_TAIL(PngChunk):
   """As the name suggests, this is not a real chunk; it represents data appended to the png file."""
   def __init__(self, *args, **kwargs):
      PngChunk.__init__(self, *args, **kwargs)
      self.crc = None # This is a hack, but works

if (__name__ == '__main__'):
   import sys
   filename = sys.argv[1]
   image = PngImage.build_from_stream(file(filename))
   print image.list_chunks_hr()


