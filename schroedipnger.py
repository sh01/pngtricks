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

# takes two source images, and creates a png file containing both in 
# superposition

import os
import logging

import png_structures
from png_structures import PngChunkgAMA

# requires PIL
import Image

class SchroediPng:
   _logger = logging.getLogger('SchroediPng')
   _log = _logger.log
   def __init__(self, img1, img2, file_gamma=0.01515):
      self.img1 = img1.copy()
      self.img2 = img2.copy()
      self.target_size = (min(img1.size[0], img2.size[0]), min(img1.size[1], img2.size[1]))
      if (img1.size != img2.size):
         self._log(30, 'size %r of img1 is different from size %r of img2. Using %r.' % (img1.size, img2.size, self.target_size))
      self.target = None
      self.result = None
      self.file_gamma = file_gamma

   def __superposition(self):
      self._log(20, 'Starting superposition for %r and %r, target size %r.' % (self.img1, self.img2, self.target_size))
      self.target = Image.new('RGB', self.target_size)
      for y in range(self.target_size[1]):
         img1_next = (not bool(y % 2))
         for x in range(self.target_size[0]):
            if (img1_next):
               gp = self.img1.getpixel
            else:
               gp = self.img2.getpixel
            self.target.putpixel((x,y), gp((x,y)))
            img1_next = (not img1_next)
      
      self._log(20, 'Superposition finished.')

   def gamma_adjust(self, color, base=255, cutoff=10):
      if (color < cutoff):
         # move any color mapped to 0 aside slightly, otherwise that component
         # would stay at 0 and remain dark in the non-gAMA phase
         color = cutoff
      color = float(color)
      color /= base
      assert (0 <= color <= 1)
      color **= self.file_gamma
      color *= base
      return int(color)

   def __color_img1_warp(self, limit=230):
      # Modify colors of image 1 to not coincide with the upper bound of the
      # color space, otherwise they won't get washed out properly by a 
      # viewer respecting gAMA
      self._log(20, 'Color warping %r.' % self.img1)
      gp = self.img1.getpixel
      for y in range(self.target_size[1]):
         for x in range(self.target_size[0]):
            pixel = gp((x,y))
            self.img1.putpixel((x,y), (min(limit, pixel[0]), min(limit, pixel[1]), min(limit, pixel[2])) + pixel[3:])
         
      self._log(20, 'Color warp of %r finished.' % self.img1)

   def __color_img2_warp(self):
      self._log(20, 'Color warping %r.' % self.img2)
      gp = self.img2.getpixel
      for y in range(self.target_size[1]):
         for x in range(self.target_size[0]):
            pixel = gp((x,y))
            self.img2.putpixel((x,y), ((self.gamma_adjust(pixel[0]), self.gamma_adjust(pixel[1]), self.gamma_adjust(pixel[2])) + pixel[3:]))
      self._log(20, 'Color warp of %r finished.' % self.img2)
   
   def __result_gamma_adjust(self):
      self._log(20, 'Adjusting gamma of %r result.' % (self.target,))
      gamma_adjusted = False
      for chunk in self.result.chunks:
         if (chunk.chunk_type == 'gAMA'):
            chunk.set_gamma(self.file_gamma)
            gamma_adjusted = True
            
      if (not gamma_adjusted):
         chunk = PngChunkgAMA('gAMA', '\x00\x00\x00\x00')
         chunk.set_gamma(self.file_gamma)
         self.result.chunks.insert(1, chunk)
         
      self._log(20, 'Gamma adjustment of %r result finished.' % (self.target,))
   
   def result_compute(self):
      if (self.target is None):
         self.__color_img1_warp()
         self.__color_img2_warp()
         self.__superposition()
         result_data = os.tmpfile()
         self.target.save(result_data, 'PNG')
         result_data.seek(0)
         self.result = png_structures.PngImage.build_from_stream(result_data)
         del(result_data)
         self.__result_gamma_adjust()

   def output_write(self, stream):
      self.result_compute()
      self._log(20, 'Writing %r result to %r.' % (self.target, stream))
      stream.write(self.result.get_binstring())
      self._log(20, 'Writing of %r result to %r finished.' % (self.target, stream))

if (__name__ == '__main__'):
   import sys
   
   logger = logging.getLogger()
   logger.setLevel(logging.DEBUG)
   formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
   handler_stderr = logging.StreamHandler()
   handler_stderr.setLevel(logging.DEBUG)
   handler_stderr.setFormatter(formatter)
   logger.addHandler(handler_stderr)
   
   logger.log(50, 'Starting...')
   
   filename1 = sys.argv[1]
   filename2 = sys.argv[2]
   
   img1 = Image.open(filename1)
   img2 = Image.open(filename2)
   
   spng = SchroediPng(img1, img2)
   
   spng.output_write(file('spng_out_test.png', 'w'))
   logger.log(50, 'All done.')

