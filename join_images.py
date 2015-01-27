# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 09:50:30 2015

@author: chuong
"""

import glob
import os
from scipy import misc
import numpy as np

Folder = "/home/chuong/Data/a_data/Gigavision/chuong_tests/2015/2015_01/2015_01_20/2015_01_20_19"
PanoRows = 19
PanoCols = 44
PanoOverViewScale = 0.5  # 0.1

FileNameList = glob.glob(os.path.join(Folder, "*.jpg"))
FileNameList.sort()

n = 0
for iCol in range(PanoCols):
    for jRow in range(PanoRows):
        FileNameList = glob.glob(os.path.join(Folder, "*{:04}.jpg".format(n)))
        if len(FileNameList) > 1:
            print(FileNameList)
        Image = misc.imread(FileNameList[0])
        ImageHeight, ImageWidth, _ = Image.shape
        if n == 0:
            ScaledHeight = int(PanoOverViewScale*ImageHeight)
            ScaledWidth = int(PanoOverViewScale*ImageWidth)
            PanoOverViewHeight = PanoRows*ScaledHeight
            PanoOverViewWidth = PanoCols*ScaledWidth
            PanoOverView = np.zeros((PanoOverViewHeight,
                                     PanoOverViewWidth, 3),
                                    dtype=np.uint8)
        ScaledHeight = int(PanoOverViewScale*ImageHeight)
        ScaledWidth = int(PanoOverViewScale*ImageWidth)
        ImageResized = misc.imresize(Image,
                                     (ScaledHeight, ScaledWidth,
                                      Image.shape[2]))
        PanoOverView[ScaledHeight*jRow:ScaledHeight*(jRow+1),
                     ScaledWidth*iCol:ScaledWidth*(iCol+1), :] = ImageResized
        n += 1
misc.imsave(os.path.join(Folder, "_data", "JoinImage.jpg"), PanoOverView)
