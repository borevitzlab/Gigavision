# -*- coding: utf-8 -*-
"""
Created on Wed May  6 14:26:27 2015

@author: chuong
"""
# Python 3.x behavior
from __future__ import absolute_import, division, print_function

import urllib
import os
import io
from datetime import datetime
import numpy as np
import csv
import PIL.Image
from scipy import misc
import time

IPVAL = '10.132.11.32:4442'
USERVAL = 'root'
PASSVAL = 'admin'
ImageSize = [1280, 720]
URL_Capture = 'USERVAL:PASSVAL@IPVAL/axis-cgi/bitmap/image.bmp?resolution=WIDTHVALxHEIGHTVAL&compression=0'
URL_SetPanTilt = 'USERVAL:PASSVAL@IPVAL/axis-cgi/com/ptz.cgi?pan=PANVAL&tilt=TILTVAL'
URL_SetZoom = 'USERVAL:PASSVAL@IPVAL/axis-cgi/com/ptz.cgi?zoom=ZOOMVAL'
URL_SetFocusMode = 'USERVAL:PASSVAL@IPVAL/axis-cgi/com/ptz.cgi?autofocus=FOCUSMODE'
URL_GetZoom = 'USERVAL:PASSVAL@IPVAL/axis-cgi/com/ptz.cgi?query=position'
URL_GetFocus = 'USERVAL:PASSVAL@IPVAL/axis-cgi/com/ptz.cgi?query=position'


def captureImage():
    URL_Str = 'http://' + URL_Capture
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    URL_Str = URL_Str.replace("WIDTHVAL", str(ImageSize[0])).replace("HEIGHTVAL", str(ImageSize[1]))
    print(URL_Str)
    stream = urllib.urlopen(URL_Str)
    byte_array = io.BytesIO(stream.read())
    Image = np.array(PIL.Image.open(byte_array))
    return Image

def captureImage2File(OutputFileName):
    URL_Str = 'http://' + URL_Capture
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    URL_Str = URL_Str.replace("WIDTHVAL", str(ImageSize[0])).replace("HEIGHTVAL", str(ImageSize[1]))
    print('Save ' + URL_Str + ' to ' + OutputFileName)
    urllib.urlretrieve(URL_Str, OutputFileName)


def captureImage2File2(OutputFileName):
    Image = captureImage()
    print('Save to ' + OutputFileName)
    misc.imsave(OutputFileName, Image)


def setPanTilt(PANVAL, TILTVAL):
    URL_Str = 'http://' + URL_SetPanTilt
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    URL_Str = URL_Str.replace("PANVAL", str(PANVAL)).replace("TILTVAL", str(TILTVAL))
    print(URL_Str)
    urllib.urlopen(URL_Str)


def setZoom(ZOOMVAL):
    URL_Str = 'http://' + URL_SetZoom
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    URL_Str = URL_Str.replace("ZOOMVAL", str(ZOOMVAL))
    print(URL_Str)
    urllib.urlopen(URL_Str)


def getZoom():
    URL_Str = 'http://' + URL_GetZoom
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    print(URL_Str)
    return urllib.urlopen(URL_Str)


def setAutoFocusMode(FOCUSMODE='on'):
    URL_Str = 'http://' + URL_SetFocusMode
    URL_Str = URL_Str.replace("USERVAL", USERVAL).replace("PASSVAL", PASSVAL).replace("IPVAL", IPVAL)
    URL_Str = URL_Str.replace("FOCUSMODE", str(FOCUSMODE))
    print(URL_Str)
    urllib.urlopen(URL_Str)


def isCameraAvailable():
    try:
        getZoom()
        return True
    except:
        return False


def readRunInfo(FileName):
    with open(FileName, 'r') as File:
        csvread = csv.DictReader(File)
        RunConfig = {"Index": [], "Col": [], "Row": [],
                     "PanDeg": [], "TiltDeg": [],
                     "Zoom": [], "Focus": []}
        for row in csvread:
            RunConfig["Index"].append(int(row["Index"]))
            RunConfig["Col"].append(int(row["Col"]))
            RunConfig["Row"].append(int(row["Row"]))
            RunConfig["PanDeg"].append(float(row["PanDeg"]))
            RunConfig["TiltDeg"].append(float(row["TiltDeg"]))
            RunConfig["Zoom"].append(int(row["Zoom"]))
            RunConfig["Focus"].append(row["Focus"])
        return RunConfig
    return None


def getPanoFolder(RootFolder, CameraName, NoPanoInSameHour):
    Start = datetime.now()
    PanoFolder = os.path.join(
        RootFolder,
        CameraName,
        Start.strftime("%Y"),
        Start.strftime("%Y_%m"),
        Start.strftime("%Y_%m_%d"),
        Start.strftime("%Y_%m_%d_%H"),
        "{}_{}_{:02}".format(CameraName,
                             Start.strftime("%Y_%m_%d_%H"),
                             NoPanoInSameHour))
    if not os.path.exists(PanoFolder):
        os.makedirs(PanoFolder)
        return PanoFolder
    return None


def getFileName(PanoFolder, CameraName, PanoImageNo, FileExtension='jpg'):
    Now = datetime.now()
    FileName = os.path.join(PanoFolder,
                            "{}_{}_00_00_{:04}.{}".format(
                                CameraName,
                                Now.strftime("%Y_%m_%d_%H_%M"),
                                PanoImageNo, FileExtension))
    return FileName


if __name__ == '__main__':
    # settings information
#    RootFolder = '/home/chuong/data/PanoFallback/test'
    RootFolder = '/home/chuong/data/gigavision'
    CameraName = 'ARB-GV-HILL-1'
    StartHour = 7
    EndHour = 17
    LoopIntervalMinute = 60  # take panoram every 1 hour
    PanoWaitMin = 15
    RunInfoFileName = '/home/chuong/data/PanoFallback/test/RunInfo.cvs'
    RunConfig = readRunInfo(RunInfoFileName)

    # set focus at the middle of field of view
    setAutoFocusMode('on')
    setZoom(RunConfig["Zoom"][0])
    i_mid = int(len(RunConfig["Index"])/2)
    setPanTilt(RunConfig["PanDeg"][i_mid], RunConfig["TiltDeg"][i_mid])
    time.sleep(3)
    captureImage()
    setAutoFocusMode('off')

    while True:
        Start = datetime.now()
        WithinHourRange = (Start.hour >= StartHour and
                           Start.hour <= EndHour)
        if WithinHourRange:
            # wait until camera is available
            while not isCameraAvailable():
                time.sleep(15*60)  # sleep 15 minute

            for h in range(10):
                PanoFolder = getPanoFolder(RootFolder, CameraName, h)
                if PanoFolder is not None:
                    break

            # make sure zoom is set at begining
            setZoom(RunConfig["Zoom"][0])
            setPanTilt(RunConfig["PanDeg"][0], RunConfig["TiltDeg"][0])
            time.sleep(3)
            for i in RunConfig["Index"]:
                setPanTilt(RunConfig["PanDeg"][i], RunConfig["TiltDeg"][i])
                if i > 0 and RunConfig["Col"][i-1] != RunConfig["Col"][i]:
                    # move to next column need more time
                    time.sleep(3)
                    print('Sleep 3 secs')
                else:
                    time.sleep(0.5)
#                ImageFileName = getFileName(PanoFolder, CameraName, i, 'bmp')
#                captureImage2File(ImageFileName)
                ImageFileName = getFileName(PanoFolder, CameraName, i, 'jpg')
                captureImage2File2(ImageFileName)
            print('Finished one panorama')

            # wait until next hour
            while True:
                End = datetime.now()
                Quotient, Remainder = divmod((End.hour*60 + End.minute),
                                             LoopIntervalMinute)
                if Remainder <= PanoWaitMin:
                    break
                DueTime = (Quotient+1)*LoopIntervalMinute
                WaitMin = DueTime - (End.hour*60 + End.minute)
                print("Wait for {} minutes before start.".format(WaitMin))
                time.sleep(WaitMin*60)
        else:
            # sleep until start of hour range
            Now = datetime.now()
            DueTime = (24 + StartHour)*60
            WaitMin = DueTime - (Now.hour*60 + Now.minute)
            Hours, Mins = divmod(WaitMin, 60)
            print("Wait {} hours and {} minutes".format(Hours, Mins))
            time.sleep(WaitMin*60)
