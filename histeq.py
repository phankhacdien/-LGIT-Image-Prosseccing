# -*- coding: utf-8 -*-
"""
Created on Tue May 27 09:59:38 2014

@author: Charles
"""

import time, os
from PIL import Image
import numpy as np
from scipy import ndimage

path = input("path: ")
raw_files = [f for f in os.listdir(path) if (f.endswith('.raw') or f.endswith('.RAW'))]

w,h = 4224, 3024

filesize = int(w*h*5/4)     # 

#channel = list(['B','Gb','Gr','R'])
channel = list(['R','Gr','Gb','B'])

def bayer2raw(bayer) :
   
    a = np.fromfile(bayer, dtype=np.uint8, count=filesize)
    
    a5 = a[4:filesize:5]
    a1 = np.uint16(a[0:filesize:5])*4 + ((a5&(3<<0))>>0)
    a2 = np.uint16(a[1:filesize:5])*4 + ((a5&(3<<2))>>2)
    a3 = np.uint16(a[2:filesize:5])*4 + ((a5&(3<<4))>>4)
    a4 = np.uint16(a[3:filesize:5])*4 + ((a5&(3<<6))>>6)
    
    A = np.vstack((a1,a2,a3,a4))
    raw = np.reshape(A.T,[h,w])
    #raw_img = Image.fromarray(np.uint8(raw/4))
    #raw_img.show()
    return raw

def histeq(im,nbr_bins=256):
   imhist,bins = np.histogram(im.flatten(),nbr_bins,normed=True) #get image histogram
   cdf = imhist.cumsum() #cumulative distribution function
   cdf = 255 * cdf / cdf[-1] #normalize
   im2 = np.interp(im.flatten(),bins[:-1],cdf) #use linear interpolation of cdf to find new pixel values
   return im2.reshape(im.shape), cdf


for i in range(0,len(raw_files)) :
    start_time = time.time() ##############  processing start  ##################################
    filename = path + raw_files[i]
    
    
    raw = bayer2raw(filename) # convert bayer format to raw image

    
    rawq = [   raw[0:h:2,0:w:2], # B
               raw[0:h:2,1:w:2], # GB
               raw[1:h:2,0:w:2], # GR
               raw[1:h:2,1:w:2]  # R      
           ]

    #for j in range(0,len(channel)) :
    #for j in range(1,2) : # Gb channel only
    for j in range(0,1):    #R channel only
        img = rawq[j]
        lsc_model = ndimage.uniform_filter(np.double(img),size=31,mode='nearest')
        lsc_model[lsc_model==0] = 1e-10;
        im_lsc = np.uint8(img/lsc_model*128);
#        lsc_img = Image.fromarray(im_lsc)
#        lsc_img.show()

        im2,cdf = histeq(im_lsc) # apply histogram eqaulization
        
        bmp_img = Image.fromarray(np.uint8(im2))
        bmp_img.save(filename[0:-4]+'_HistEq_'+channel[j]+'.jpg','jpeg')  # save JPG result image
    
    end_time = time.time(); pp = end_time - start_time
    print("process time : %f" % pp)  ###############  processing end  ############################
    
