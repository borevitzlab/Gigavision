# -*- coding: utf-8 -*-
"""
Created on Wed May  6 14:26:27 2015

@author: chuong
"""
# Python 3.x behavior
from __future__ import absolute_import, division, print_function

import urllib2
import base64
import os
import io
from datetime import datetime
import numpy as np
import csv
import PIL.Image
from scipy import misc
import time
import yaml
import subprocess
import shutil

# This is for Axis camera
IPVAL = ''
USERVAL = ''
PASSVAL = ''
# Panorama parameters
ImageSize = [1920, 1080]  # [1280, 720]

# Panaroma 48 x 16 = 768
Zoom = 3500 # degree
FieldOfView = [5.6708, 3.1613]  # degree

## Panorama 75 x 25 = 1875
#Zoom = 5500
#FieldOfView = [3.5865, 1.9994]  # degree

## Panorama 95 x 32 = 3040
#Zoom = 7000
#FieldOfView = [2.8354, 1.58065]  # degree

Focus = 8027
TopLeftCorner = [-15.2804, 6.7060] # degree
BottomRightCorner = [147.0061, -23.3940] # degree
Overlap = 40  # percentage of image overlapping
max_no_tries = 3  # to deal with corrupted connection
# URL command patterns
# Ref: https://www.ispyconnect.com/man.aspx?n=Axis
URL_Capture_Bitmap = 'IPVAL/axis-cgi/bitmap/image.bmp?resolution=WIDTHVALxHEIGHTVAL&compression=0'
URL_Capture_JPG = 'IPVAL/jpg/image.jpg?&resolution=WIDTHVALxHEIGHTVAL'
URL_SetPanTilt = 'IPVAL/axis-cgi/com/ptz.cgi?pan=PANVAL&tilt=TILTVAL'
URL_SetPanTiltZoom = 'IPVAL/axis-cgi/com/ptz.cgi?pan=PANVAL&tilt=TILTVAL&zoom=ZOOMVAL'
URL_SetZoom = 'IPVAL/axis-cgi/com/ptz.cgi?zoom=ZOOMVAL'
URL_SetFocusMode = 'IPVAL/axis-cgi/com/ptz.cgi?autofocus=FOCUSMODE'
URL_GetZoom = 'IPVAL/axis-cgi/com/ptz.cgi?query=position'
RET_GetZoom = '*zoom={}*'
URL_GetFocusMode = 'IPVAL/axis-cgi/com/ptz.cgi?query=position'
RET_GetFocusMode = '*autofocus={}*'


def callURL(URL, IPVAL, USERVAL, PASSVAL):
    URL_Str = 'http://' + URL
    URL_Str = URL_Str.replace("IPVAL", IPVAL)
    print(URL_Str),
    request = urllib2.Request(URL_Str)
    base64string = base64.encodestring('%s:%s' % (USERVAL, PASSVAL)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    try:
        stream = urllib2.urlopen(request, timeout=60)
    except urllib2.URLError, e:
        raise Exception("Time out error: %r" % e)
    return stream.read()


def captureImageBitmap():
    URL_Str = URL_Capture_Bitmap.replace("WIDTHVAL", str(ImageSize[0])).replace("HEIGHTVAL", str(ImageSize[1]))
    output = callURL(URL_Str, IPVAL, USERVAL, PASSVAL)
    byte_array = io.BytesIO(output)
    print(' Read successfull')
    Image = np.array(PIL.Image.open(byte_array))
    return Image


def captureJPGImage2File(OutputFileName):
    URL_Str = URL_Capture_JPG.replace("WIDTHVAL", str(ImageSize[0])).replace("HEIGHTVAL", str(ImageSize[1]))
    URL_Str = 'http://' + URL_Str
    URL_Str = URL_Str.replace("IPVAL", IPVAL)
    JPG_File = open(OutputFileName, 'wb')
    isSuccessfull = True
    try:
        JPG_Data = urllib2.urlopen(URL_Str)
        JPG_File.write(JPG_Data.read())
    except:
        isSuccessfull = False
        print('Fail to capture JPG image')
    finally:
        JPG_File.close()
    print(' Read successfull')
    return isSuccessfull


def captureImage2File(OutputFileName):
    try:
        Image = captureImageBitmap()
    except Exception as e:
        print('Error when capturing an image: {}'.format(e))
        return False
    try:
        print('Save to ' + OutputFileName)
        misc.imsave(OutputFileName, Image)
        return True
    except Exception as e:
        print('Error when saving an image: {}'.format(e))
        return False


def setPanTilt(PANVAL, TILTVAL):
    URL_Str = URL_SetPanTilt.replace("PANVAL", str(PANVAL)).replace("TILTVAL", str(TILTVAL))
    try:
        callURL(URL_Str, IPVAL, USERVAL, PASSVAL)
        return True
    except Exception as e:
        print('Error when setting pan/tilt: {}'.format(e))
        return False


def setPanTiltZoom(PANVAL, TILTVAL, ZOOMVAL):
    URL_Str = URL_SetPanTiltZoom.replace("PANVAL", str(PANVAL)).replace("TILTVAL", str(TILTVAL)).replace("ZOOMVAL", str(ZOOMVAL))
    try:
        callURL(URL_Str, IPVAL, USERVAL, PASSVAL)
        return True
    except Exception as e:
        print('Error when setting pan/tilt: {}'.format(e))
        return False


def setZoom(ZOOMVAL):
    URL_Str = URL_SetZoom.replace("ZOOMVAL", str(ZOOMVAL))
    try:
        callURL(URL_Str, IPVAL, USERVAL, PASSVAL)
        return True
    except Exception as e:
        print('Error when setting zoom: {}'.format(e))
        return False


def getZoom():
    Output = callURL(URL_GetZoom, IPVAL, USERVAL, PASSVAL).strip()
    ZOOMVAL = extractInfo(Output, RET_GetZoom)
    return ZOOMVAL


def setAutoFocusMode(FOCUSMODE):
    URL_Str = URL_SetFocusMode.replace("FOCUSMODE", str(FOCUSMODE))
    print(URL_Str)
    try:
        callURL(URL_Str, IPVAL, USERVAL, PASSVAL)
        return True
    except Exception as e:
        print('Error when setting autofocus mode: {}'.format(e))
        return False


def isCameraAvailable():
    try:
        getZoom()
        return True
    except:
        return False


def extractInfo(Text, RET_Str):
        StrList = RET_Str.split("*")
        StrList = [Str for Str in StrList if len(Str) > 0]
        Vals = []
        for Str in StrList:
            WordList = Str.split("{}")
            WordList = [Word for Word in WordList if len(Word) > 0]
            if len(WordList) == 1:
                Pos = Text.find(WordList[0])
                if Pos >= 0:
                    Val = Text[Pos + len(WordList[0]):]
                    ValList = Val.split("\n")
                    Vals.append(ValList[0].strip())
            elif len(WordList) == 2:
                Pos1 = Text.find(WordList[0])
                Pos2 = Text.find(WordList[1], Pos1 + len(WordList[0]))
                if Pos1 >= 0 and Pos2 >= Pos1:
                    Vals.append(Text[Pos1 + len(WordList[0]):Pos2])
            else:
                print("Unhandled case {}". format(Str))
        return Vals[0]


def readRunInfo(FileName):
    with open(FileName, 'r') as File:
        csvread = csv.DictReader(File)
        RunConfig = {"Index": [], "Col": [], "Row": [],
                     "PanDeg": [], "TiltDeg": [],
                     "Zoom": [], "Focus": [], "FileName": []}
        for row in csvread:
            RunConfig["Index"].append(int(row["Index"]))
            RunConfig["Col"].append(int(row["Col"]))
            RunConfig["Row"].append(int(row["Row"]))
            RunConfig["PanDeg"].append(float(row["PanDeg"]))
            RunConfig["TiltDeg"].append(float(row["TiltDeg"]))
            RunConfig["Zoom"].append(int(row["Zoom"]))
            RunConfig["Focus"].append(row["Focus"])
            RunConfig["FileName"].append(row["FileName"])
        return RunConfig
    return None


def writeRunInfo(FileName, RunConfig):
    with open(FileName, 'w') as File:
        FieldNames = ["Index", "Col", "Row", "PanDeg", "TiltDeg", "Zoom",
                      "Focus", "FileName"]
        File.write(','.join(FieldNames))
        for i in range(len(RunConfig["Index"])):
            row = [str(RunConfig[key][i]) for key in FieldNames]
            File.write('\n' + ','.join(row))
        return True
    return False


def getPanoFolder(RootFolder, CameraName, NoPanoInSameHour=-1):
    Start = datetime.now()
    if NoPanoInSameHour < 0:
        # no hour subfolder
        PanoFolder = os.path.join(
            RootFolder,
            CameraName,
            Start.strftime("%Y"),
            Start.strftime("%Y_%m"),
            Start.strftime("%Y_%m_%d"),
            Start.strftime("%Y_%m_%d_%H"))
    else:
        # create hour subfolders
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


def setFocusAt(PanDeg, TiltDeg, Zoom):
    # set focus at the middle of field of view
    # this may work only with Axis camera
    setAutoFocusMode('on')
    setZoom(Zoom)
    setPanTilt(PanDeg, TiltDeg)
    time.sleep(5)
    captureImageBitmap()
    setAutoFocusMode('off')

def saveBlackImage2File(OutputFileName):
    BlackImage = np.zeros([ImageSize[1], ImageSize[0], 3], dtype=np.uint8)
    try:
        misc.imsave(OutputFileName, BlackImage)
    except:
        print('Failed to save empty image')

def createPanoramaSummary(ImageFolder, MaxWidth=4096):
    def scale(InputFolder, OutputFolder, OutputSize, FilePattern):
        if not os.path.exists(OutputFolder):
            os.makedirs(OutputFolder)
        Command = ['mogrify', '-scale',
                   str(OutputSize), '-path', OutputFolder, FilePattern]
        return subprocess.call(Command, cwd=InputFolder)
    # Load running info
    RunConfig = readRunInfo(os.path.join(ImageFolder, '_data', 'RunInfo.cvs'))

    # Get total width of joined image
#    FilePath = os.path.join(ImageFolder,
#                            os.path.basename(RunConfig['FileName'][0]))
    import glob
    FileList = glob.glob(os.path.join(ImageFolder, '*.jpg'))
    FileList.sort()
    FilePath = FileList[0]

    ImageWidth = misc.imread(FilePath).shape[1]
    JointWidth = ImageWidth*RunConfig['Col'][-1]

    OutputPercentage = '{:0.3f}%'.format(100*float(MaxWidth)/float(JointWidth))
    ScaledFolder = os.path.join(ImageFolder, '_data', 'scale')
    FilePattern = '*.jpg'
    ret = scale(ImageFolder, ScaledFolder, OutputPercentage, FilePattern)
    print(ret)

    # Scaled total size
#    ScaledFilePath = os.path.join(ScaledFolder,
#                                  os.path.basename(RunConfig['FileName'][0]))
    ScaledFilePath = os.path.join(ScaledFolder, os.path.basename(FileList[0]))
    ImageSize = misc.imread(ScaledFilePath).shape
    print(ImageSize)
    JointSize = [ImageSize[0]*(RunConfig['Row'][-1]+1),
                 ImageSize[1]*(RunConfig['Col'][-1]+1),
                 ImageSize[2]]
    # Create scaled joint image
    if ImageSize[0]*ImageSize[1]*ImageSize[2] < 4096*4096*3:
        JointImage = np.zeros(JointSize, dtype=np.uint8)
    else:
        print('Error: joint image size {} is too large'.format(ImageSize))
        exit(-1)
    for i in RunConfig['Index']:
#        ScaledFilePath = os.path.join(
#            ScaledFolder, os.path.basename(RunConfig['FileName'][i]))
        ScaledFilePath = os.path.join(ScaledFolder,
                                      os.path.basename(FileList[i]))
        ScaledImage = misc.imread(ScaledFilePath)
        iCol = RunConfig['Col'][i]
        jRow = RunConfig['Row'][i]
        JointImage[jRow*ImageSize[0]:(jRow+1)*ImageSize[0],
                   iCol*ImageSize[1]:(iCol+1)*ImageSize[1], :] = ScaledImage
    JointdFilePath = os.path.join(ImageFolder, '_data', 'JointImage.jpg')
    misc.imsave(JointdFilePath, JointImage)

    # Remove the scale folder
    shutil.rmtree(ScaledFolder)

if __name__ == '__main__':
    # settings information
    # TODO: makes these commandline options
    RootFolder = '/media/TBUltrabookBackup/phenocams'
#    RootFolder = '/home/chuong/data/phenocams'
    CameraName = 'ARB-GV-HILL-1'
    StartHour = 8
    EndHour = 18
    LoopIntervalMinute = 60  # take panoram every 1 hour
    PanoWaitMin = 15  # minutes
    DelayBetweenColumns = 3  # seconds
    DelayBetweenImages = 0.5  # seconds
    MultiRunPerHour = False  # ON/OFF hour subfolder
    RunInfoFileName = ''  # '/home/pi/workspace/Gigavision/RunInfo.cvs'
    CamConfigFile = '/home/pi/workspace/Gigavision/AxisCamera_Q6115-E.yml'
#    RunInfoFileName = '/home/chuong/workspace/Gigavision/RunInfo.cvs'
#    CamConfigFile = '/home/chuong/workspace/Gigavision/AxisCamera_Q6115-E.yml'

    CamConfig = yaml.load(open(CamConfigFile, 'r'))
    IPVAL = CamConfig['IPVAL']
    USERVAL = CamConfig['USERVAL']
    PASSVAL = CamConfig['PASSVAL']
    if os.path.exists(RunInfoFileName):
        RunConfig = readRunInfo(RunInfoFileName)
    else:
        print('Generate RunConfig')
        RunConfig = {'Index': [], 'Col': [], 'Row': [],
                     'PanDeg': [], 'TiltDeg': [],
                     'Zoom': [], 'Focus': [], 'FileName': []}
        [LeftPan, TopTilt] = TopLeftCorner
        [RightPan, BottomTilt] = BottomRightCorner
        HFoV, VFoV = FieldOfView
        PanoRows = int(round((TopTilt - BottomTilt)/VFoV/(1.0-Overlap/100.0)))
        PanoCols = int(round((RightPan - LeftPan)/HFoV/(1.0-Overlap/100.0)))
        print('Row = {}, Col = {}'.format(PanoRows, PanoCols))
        Index = 0
        print('Index, Col', 'Row, PanDeg, TiltDeg, Zoom, Focus')
        for iCol in range(PanoCols):
            for jRow in range(PanoRows):
                PanDeg  = TopLeftCorner[0] + iCol*HFoV*(1.0 - Overlap/100.0)
                TiltDeg = TopLeftCorner[1] - jRow*VFoV*(1.0 - Overlap/100.0)
                RunConfig['Index'].append(Index)
                RunConfig['Col'].append(iCol)
                RunConfig['Row'].append(jRow)
                RunConfig['PanDeg'].append(PanDeg)
                RunConfig['TiltDeg'].append(TiltDeg)
                RunConfig['Zoom'].append(Zoom)
                RunConfig['Focus'].append(Focus)
                print('{},{},{},{},{},{},{}'.format(Index, iCol, jRow, PanDeg, TiltDeg, Zoom, Focus))
                Index += 1
    while True:
        Start = datetime.now()
        WithinHourRange = (Start.hour >= StartHour and
                           Start.hour <= EndHour)
        if WithinHourRange:
            # wait until camera is available
            while not isCameraAvailable():
                print('Camera is not available. Check again in 15 min.')
                time.sleep(15*60)  # sleep 15 minute

            # make sure zoom is set at begining
            while True:
                try:
                    setZoom(RunConfig["Zoom"][0])
                    break
                except:
                    print('Sleep 1 secs to set zoom')
                    time.sleep(1)
            while True:
                try:
                    Zoom0 = getZoom()
                    break
                except:
                    print('Sleep 1 secs to get zoom')
                    time.sleep(1)

            # set focus at the middle of field of view
            PanDegMin = min(RunConfig["PanDeg"])
            PanDegMax = max(RunConfig["PanDeg"])
            TiltDegMin = min(RunConfig["TiltDeg"])
            TiltDegMax = max(RunConfig["TiltDeg"])
            PanMiddle = (PanDegMin+PanDegMax)/2
            TiltMiddle= (TiltDegMin+TiltDegMax)/2
            while True:
                try:
                    setFocusAt(PanMiddle, TiltMiddle, RunConfig["Zoom"][0])
                    break
                except:
                    print('Failed to focus the camera. Camera is likely down.')
                    print('Try focusing again in 5 minutes')
                    time.sleep(5*60)

            if MultiRunPerHour:
                for h in range(10):
                    PanoFolder = getPanoFolder(RootFolder, CameraName, h)
                    if PanoFolder is not None:
                        break
            else:
                PanoFolder = getPanoFolder(RootFolder, CameraName)

            setPanTiltZoom(RunConfig["PanDeg"][0], RunConfig["TiltDeg"][0],
                           RunConfig["Zoom"][0])
            time.sleep(3)
            RunConfig['FileName'] = []
            for i in RunConfig["Index"]:
                ImageFileName = getFileName(PanoFolder, CameraName, i, 'jpg')
                RunConfig['FileName'].append(ImageFileName)
                j = 0
                while j < max_no_tries:
                    if setPanTiltZoom(RunConfig["PanDeg"][i],
                                      RunConfig["TiltDeg"][i],
                                      RunConfig["Zoom"][i]):
                        break
                    else:
                        j += 1
                        time.sleep(1)

                # check if it is moving to the next column
                if i > 0 and RunConfig["Col"][i-1] != RunConfig["Col"][i]:
                    # move to next column needs more time
                    time.sleep(DelayBetweenColumns)
                    print('Sleep {} secs between columns'.format(DelayBetweenColumns))
                else:
                    time.sleep(DelayBetweenImages)

                while j < max_no_tries:
#                    if captureImage2File(ImageFileName):  # crash reset the camera after certain number of images
                    if captureJPGImage2File(ImageFileName):
                        break
                    else:
                        j += 1
                        print('Failed to capture an image. Try again.')
                        time.sleep(1)
                if j >= max_no_tries:
                    print('Fail to capture an image after {} tries.'
                          ' Save a black image.'.format(max_no_tries))
                    saveBlackImage2File(ImageFileName)

            # write panoram config file
            os.makedirs(os.path.join(PanoFolder, '_data'))
            RunConfigFile = os.path.join(PanoFolder, '_data', 'RunInfo.csv')
            writeRunInfo(RunConfigFile, RunConfig)
            createPanoramaSummary(PanoFolder)

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
