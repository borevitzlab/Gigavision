# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
"""

import sys
import os
from datetime import datetime
from io import BytesIO
import urllib
import numpy as np
import time
import re
import glob
import shutil
import csv
from skimage import io
from skimage.feature import (match_descriptors, ORB, plot_matches)
from skimage.color import rgb2gray
from scipy.spatial.distance import hamming


def getDisplacement(Image0, Image1):
    Image0Gray = rgb2gray(Image0)
    Image1Gray = rgb2gray(Image1)
    descriptor_extractor = ORB(n_keypoints=200)

    descriptor_extractor.detect_and_extract(Image0Gray)
    keypoints1 = descriptor_extractor.keypoints
    descriptors1 = descriptor_extractor.descriptors

    descriptor_extractor.detect_and_extract(Image1Gray)
    keypoints2 = descriptor_extractor.keypoints
    descriptors2 = descriptor_extractor.descriptors

    matches12 = match_descriptors(descriptors1, descriptors2, cross_check=True)

    # Sort the matches based on distance.  Least distance
    # is better
    distances12 = []
    for match in matches12:
        distance = hamming(descriptors1[match[0]], descriptors2[match[1]])
        distances12.append(distance)

    indices = np.range(len(matches12))
    indices = [index for (_, index) in sorted(zip(distances12, indices))]
    matches12 = matches12[indices]

    # collect displacement from the first 10 matches
    dxList = []
    dyList = []
    for mat in matches12[:10]:
        # Get the matching keypoints for each of the images
        img1_idx = mat[0]
        img2_idx = mat[1]

        # x - columns
        # y - rows
        (x1, y1) = keypoints1[img1_idx]
        (x2, y2) = keypoints2[img2_idx]
        dxList.append(abs(x1 - x2))
        dyList.append(abs(y1 - y2))

    dxMedian = np.median(np.asarray(dxList, dtype=np.double))
    dyMedian = np.median(np.asarray(dyList, dtype=np.double))
    plot_matches(Image0, Image1, descriptors1, descriptors2, matches12[:10])
    return dxMedian, dyMedian


class IPCamera(object):
    """
    Control ACTi Camera
    Ref: http://www2.acti.com/getfile/KnowledgeBase_UploadFile/ACTi_Camera_URL_Commands_20120327_002.pdf

    For high zoom, zoom value needs to change slowly for the camera to auto focus

    """
    def __init__(self, IP, User, Password, ImageSize=None, ImageQuality=100):
        self.IP = IP
        self.HTTPLogin = "http://{}/cgi-bin/encoder?"\
            "USER={}&PWD={}".format(IP, User, Password)
        self.IMAGE_SIZES = [[1920, 1080], [1280, 720], [640, 480]]
        if ImageSize:
            self.setImageSize(ImageSize)
        self.Image = None
        self.PhotoIndex = 0

        self.Commands = {}
        self.Commands["zoom_range"] = "&ZOOM_CAP_GET"
        self.Commands["zoom_curpos"] = "&ZOOM_POSITION"
        self.Commands["zoom_mode"] = "&ZOOM={}"
        self.Commands["zoom_set"] = "&ZOOM={},{}"
        self.Commands["zoom_step"] = "&STEPPED_ZOOM={},{}"

        self.Commands["focus_range"] = "&FOCUS_CAP_GET"
        self.Commands["focus_curpos"] = "&FOCUS_POSITION"
        self.Commands["focus_mode"] = "&FOCUS={}"
        self.Commands["focus_set"] = "&FOCUS={},{}"
        self.Commands["focus_step"] = "&STEPPED_FOCUS={},{}"

        self.Commands["image_resolution"] = "&VIDEO_RESOLUTION=N{}x{}"
        self.Commands["image_quality"] = "&VIDEO_MJPEG_QUALITY={}"
        self.Commands["snap_photo"] = "&SNAPSHOT&DUMMY={}"
        self.Commands["snap_photo2"] = "&SNAPSHOT=N{}x{},100&DUMMY={}"

        # Valid values for ACTi camera
        self.ZOOM_MODES = ["STOPS"]
        self.ZOOM_STATES = ["DIRECT", "TELE"]
        self.ZOOM_STEP_DIRECTIONS = ["TELE", "WIDE"]
        self.ZOOM_STEP_RANGE = [1, 255]
        self.ZOOM_DIRECT_RANGE = self.getZoomRange()

        self.FOCUS_MODES = ["STOP", "FAR", "NEAR", "AUTO", "MANUAL", "ZOOM_AF",
                            "REFOCUS"]
        self.FOCUS_STATES = ["DIRECT"]
        self.FOCUS_STEP_DIRECTIONS = ["NEAR", "FAR"]
        self.FOCUS_STEP_RANGE = [1, 255]
        self.FOCUS_DIRECT_RANGE = self.getFocusRange()

        print(self.status())
        self.setImageQuality(ImageQuality)

    def setImageQuality(self, ImageQuality):
        assert(ImageQuality >= 1 and ImageQuality <= 100)
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["image_quality"].format(
                                    ImageQuality))

        Output = stream.read(1024).strip()
        return Output

    def setImageSize(self, ImageSize):
        assert(ImageSize in self.IMAGE_SIZES)
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["image_resolution"].format(
                                    ImageSize[0], ImageSize[1]))

        Output = stream.read(1024).strip()
        self.ImageSize = ImageSize
        return Output

    def getImageSize(self, ImageSize):
        return self.ImageSize

    def snapPhoto(self, ImageSize=None):
        if ImageSize and ImageSize in self.IMAGE_SIZES:
            URL = self.HTTPLogin + self.Commands["snap_photo2"].format(
                ImageSize[0], ImageSize[1], self.PhotoIndex)
        else:
            URL = self.HTTPLogin + self.Commands["snap_photo"].format(
                self.PhotoIndex)
        try:
            import PIL
            stream = urllib.urlopen(URL)
            byte_array = BytesIO(stream.read())
            self.Image = np.array(PIL.Image.open(byte_array))
        except:
            # fallback slow solution
            Filename = self.snapPhoto2File(None, ImageSize)
            self.Image = io.imread(Filename)
        self.PhotoIndex += 1
        return self.Image

    def snapPhoto2File(self, Filename, ImageSize=None):
        if ImageSize and ImageSize in self.IMAGE_SIZES:
            URL = self.HTTPLogin + self.Commands["snap_photo2"].format(
                ImageSize[0], ImageSize[1], self.PhotoIndex)
        else:
            URL = self.HTTPLogin + self.Commands["snap_photo"].format(
                self.PhotoIndex)
        try:
            filename, _ = urllib.urlretrieve(URL, Filename)
            self.PhotoIndex += 1
            return filename
        except:
            return None

    def getValue(self, Text):
        Text = Text.split("=")
        if len(Text) >= 2:
            TextValue = re.sub("'", "", Text[1])
            ValueList = TextValue.split(",")
            ValueList = [float(Value) if Value.replace(".", "", 1).isdigit()
                         else Value for Value in ValueList]
            return ValueList
        else:
            return None

    def zoomStep(self, Direction, StepSize):
        if Direction.lower() == "in":
            Direction = "TELE"
        elif Direction.lower() == "out":
            Direction = "WIDE"
        assert(Direction in self.ZOOM_STEP_DIRECTIONS and
               StepSize >= self.ZOOM_STEP_RANGE[0] and
               StepSize <= self.ZOOM_STEP_RANGE[1])
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_step"].format(
                                    Direction, StepSize))
        Output = stream.read(1024).strip()
        return Output

    def setZoomPosition(self, AbsPosition):
        assert(AbsPosition >= self.ZOOM_DIRECT_RANGE[0] and
               AbsPosition <= self.ZOOM_DIRECT_RANGE[1])
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_set"].format(
                                    "DIRECT", AbsPosition))
        Output = stream.read(1024).strip()
        return Output

    def setFocusPosition(self, AbsPosition):
        assert(AbsPosition >= self.FOCUS_DIRECT_RANGE[0] and
               AbsPosition <= self.FOCUS_DIRECT_RANGE[1])
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["focus_set"].format(
                                    "DIRECT", AbsPosition))
        Output = stream.read(1024).strip()
        return Output

    def getZoomPosition(self):
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["zoom_curpos"])
        Output = stream.read(1024).strip()
        Position = self.getValue(Output)
        return Position[0]

    def getZoomRange(self):
        stream = urllib.urlopen(self.HTTPLogin + self.Commands["zoom_range"])
        Outptput = stream.read(1024).strip()
        return self.getValue(Outptput)

    def refocus(self):
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["focus_mode"].format("REFOCUS"))
        Outptput = stream.read(1024).strip()
        return self.getValue(Outptput)

    def getFocusPosition(self):
        stream = urllib.urlopen(self.HTTPLogin +
                                self.Commands["focus_curpos"])
        Output = stream.read(1024).strip()
        Position = self.getValue(Output)
        return Position[0]

    def getFocusRange(self):
        stream = urllib.urlopen(self.HTTPLogin + self.Commands["focus_range"])
        Outptput = stream.read(1024).strip()
        Values = self.getValue(Outptput)
        # ex: Values = ["Motorized", 1029.0, 221.0]
        Range = Values[2:0:-1]
        return Range

    def updateStatus(self):
        self.zoomPos = self.getZoomPosition()
        self.zoomRange = self.getZoomRange()
        self.focusPos = self.getFocusPosition()
        self.focusRange = self.getFocusRange()

    def status(self):
        self.updateStatus()
        Status = "ZoomPos = {}. FocusPos = {}.".format(self.zoomPos,
                                                       self.focusPos)
        Status += "\nZoom range = {}".format(self.ZOOM_DIRECT_RANGE)
        Status += "\nFocus range = {}".format(self.FOCUS_DIRECT_RANGE)
        return Status


class PanTilt(object):
    """
    Control J-Systems PTZ

    For new sysem or new firmware, the system needs calibration as follows:
    - Open URL of the PTZ on a web browser
    - Click on "Calibration" tab, enter username and password if necessary
    - On Calibration window, click on "Open-loop" and then "Set Mode"
    - Use joystick controller to rotate the pan axis to minimum position
    - Click on 'Pan Axis Min' line, enter '2.0', and click "Set Calibration"
    - Use joystick controller to rotate the pan axis to maximum position
    - Click on 'Pan Axis Max' line, enter '358.0', and click "Set Calibration"
    - Use joystick controller to rotate the tilt axis to minimum position
    - Click on 'Tilt Axis Min' line, enter '-90.0', and click "Set Calibration"
    - Use joystick controller to rotate the tilt axis to maximum position
    - Click on 'Tilt Axis Max' line, enter '30.0', and click "Set Calibration"
    - Click on "Closed-loop" and then "Set Mode"
    - Close Calibration window
    """
    def __init__(self, IP, User=None, Password=None):
        self.IP = IP
        self.User = User
        self.Password = Password
        self.Link = "http://{}".format(self.IP)
        print(self.status())

    def getKeyValue(self, MessageXML, Key):
        KeyStart = "<{}>".format(Key)
        KeyEnd = "</{}>".format(Key)
        Start = MessageXML.find(KeyStart)
        # Sometimes KeyStart is missing
        if Start < 0:
            Start = 0
        else:
            Start = Start + len(KeyStart)
        End = MessageXML.find(KeyEnd, Start)
        if End > Start:
            Value = MessageXML[Start:End].strip()
            try:
                return float(Value)
            except:
                return Value
        else:
            return ""

    def panStep(self, Direction, Steps):
        assert(abs(Steps) <= 127)
        Dir = 1
        if Direction.lower() == "left":
            Dir = -1
        Url = self.Link + "/Bump.xml?PCmd={}".format(Dir*Steps)
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def tiltStep(self, Direction, Steps):
        assert(abs(Steps) <= 127)
        Dir = 1
        if Direction.lower() == "down":
            Dir = -1
        Url = self.Link + "/Bump.xml?TCmd={}".format(Dir*Steps)
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def setPanTiltPosition(self, PanDegree=0, TiltDegree=0):
        Url = self.Link + "/Bump.xml?GoToP={}&GoToT={}".format(
            int(PanDegree*10), int(TiltDegree*10))
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        Info = self.getKeyValue(Output, "Text")
        NoLoops = 0
        # loop until within 1 degree
        while True:
            PanPos, TiltPos = self.getPanTiltPosition()
            PanDiff = int(abs(PanPos - PanDegree))
            TiltDiff = int(abs(TiltPos - TiltDegree))
            if PanDiff <= 1 and TiltDiff <= 1:
                break
            time.sleep(0.1)
            NoLoops += 1
            if NoLoops > 50:
                print("Warning: pan-tilt fails to move to correct location")
                print("  Desire position: PanPos={}, TiltPos={}".format(
                    PanDegree, TiltDegree))
                print("  Current position: PanPos={}, TiltPos={}".format(
                    PanPos, TiltPos))
                break
        #loop until smallest distance is reached
        while True:
            PanPos, TiltPos = self.getPanTiltPosition()
            PanDiffNew = abs(PanPos - PanDegree)
            TiltDiffNew = abs(TiltPos - TiltDegree)
            if PanDiffNew >= PanDiff or TiltDiffNew >= TiltDiff:
                break
            else:
                PanDiff = PanDiffNew
                TiltDiff = TiltDiffNew
            time.sleep(0.1)
            NoLoops += 1
            if NoLoops > 50:
                break

        return Info

    def setPanPosition(self, Degree):
        Info = self.setPanTiltPosition(PanDegree=Degree)
        return Info

    def setTiltPosition(self, Degree):
        Info = self.setPanTiltPosition(TiltDegree=Degree)
        return Info

    def getPanPosition(self):
        self.updateStatus()
        return self.PanPos

    def getTiltPosition(self):
        self.updateStatus()
        return self.TiltPos

    def getPanTiltPosition(self):
        self.updateStatus()
        return self.PanPos, self.TiltPos

    def holdPanTilt(self, State):
        if State is True:
            Url = self.Link + "/Calibration.xml?Action=0"
        else:
            Url = self.Link + "/Calibration.xml?Action=C"
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)
        print(Output)
        Info = self.getKeyValue(Output, "Text")
        return Info

    def updateStatus(self):
        Url = self.Link + "/CP_Update.xml"
        stream = urllib.urlopen(Url)
        Output = stream.read(1024)

        self.PanPos = self.getKeyValue(Output, "PanPos")  # degrees
        self.TiltPos = self.getKeyValue(Output, "TiltPos")  # degrees

        # Limit switch states
        self.PCCWLS = self.getKeyValue(Output, "PCCWLS")
        self.PCWLS = self.getKeyValue(Output, "PCWLS")
        self.TDnLS = self.getKeyValue(Output, "TDnLS")
        self.TUpLS = self.getKeyValue(Output, "TUpLS")

        self.BattV = self.getKeyValue(Output, "BattV")  # Volt
        self.Heater = self.getKeyValue(Output, "Heater")
        self.Temp = self.getKeyValue(Output, "Temp")  # F degrees

        self.ListState = self.getKeyValue(Output, "ListState")
        self.ListIndex = self.getKeyValue(Output, "ListIndex")
        self.CtrlMode = self.getKeyValue(Output, "CtrlMode")

        self.AutoPatrol = self.getKeyValue(Output, "AutoPatrol")
        self.Dwell = self.getKeyValue(Output, "Dwell")  # seconds

    def status(self):
        self.updateStatus()
        Status = "PanPos = {} degrees. TiltPos = {} degrees.".format(
            self.PanPos, self.TiltPos)
        Status += "PCCWLS = {}, PCCWLS = {}, TDnLS = {}, TDnLS = {}".format(
            self.PCCWLS, self.PCWLS, self.TDnLS, self.TUpLS)
        return Status


class Panorama(object):
    def __init__(self,
                 CameraURL, CameraUsername, CameraPassword,
                 PanTiltURL, PanTiltUsername=None, PanTiltPassword=None):
        self.Cam = IPCamera(CameraURL, CameraUsername, CameraPassword)
        self.PanTil = PanTilt(PanTiltURL, PanTiltUsername, PanTiltPassword)
        self.CamZoom = None
        self.CamHFoV = None
        self.CamVFoV = None
        self.CamZoomList = None
        self.CamHFoVList = None
        self.CamVFoVList = None
        self.PanRange = None
        self.TiltRange = None
        self.ImageOverlap = 0.5

    def setImageSize(self, ImageSize):
        self.Cam.setImageSize(ImageSize)

    def setImageOverlap(self, ImageOverlap):
        self.ImageOverlap = ImageOverlap

    def setZoom(self, Zoom):
        self.Cam.setZoomPosition(Zoom)
        self.CamZoom = Zoom

    def setFoVFromZoom(self, Zoom=None):
        if Zoom is not None and self.CamZoom is None:
            self.Zoom = Zoom
        elif Zoom is None and self.CamZoom is None:
            print("Zoom is not set")
            raise
        elif self.CamZoomList is None and self.CamFoVList is None:
            print("Field of view is not set")
            raise
        self.CamHFoV = np.interp(self.CamZoom,
                                 self.CamZoomList, self.CamHFoVList)
        if self.CamVFoVList is None:
            self.CamVFoV = self.CamHFoV * \
                self.Cam.ImageSize[1]/self.Cam.ImageSize[0]
        else:
            self.CamVFoV = np.interp(self.CamZoom,
                                     self.CamZoomList, self.CamVFoVList)

    def setCameraFoV(self, CamHFoV, CamVFoV):
        self.CamHFoV = CamHFoV
        self.CamVFoV = CamVFoV

    def setCameraFovDist(self, ZoomList, HFoVList, VFoVList=None):
        self.CamZoomList = ZoomList
        self.CamHFoVList = HFoVList
        self.CamVFoVList = VFoVList

    def getCameraFoV(self, Zoom=None):
        if Zoom is None and \
                self.CamHFoV is not None and self.CamVFoV is not None:
            return self.CamHFoV, self.CamVFoV
        elif self.CamZoomList is not None and self.CamFoVList is not None:
            CamHFoV = np.interp(Zoom, self.CamZoomList, self.CamHFoVList)
            CamVFoV = np.interp(Zoom, self.CamZoomList, self.CamVFoVList)
            return CamHFoV, CamVFoV
        else:
            return None, None

    def setPanoramaFoV(self, PanFoV, TiltFoV, PanCentre, TiltCentre):
        self.PanRange = [PanFoV - PanCentre, PanFoV + PanCentre]
        self.TiltRange = [TiltFoV - TiltCentre, TiltFoV + TiltCentre]

    def setPanoramaFoVRange(self, PanRange, TiltRange):
        self.PanRange = PanRange
        self.TiltRange = TiltRange

    def calibrateFoVList(self, ZoomList=range(50, 1000, 100),
                         PanPos0=150, TiltPos0=0,
                         PanInc=2, TiltInc=0):
        CamHFoVList = []
        CamVFoVList = []
        self.Cam.setZoomPosition(ZoomList[0]-5)
        time.sleep(1)
        for ZoomPos in ZoomList:
            self.Cam.setZoomPosition(ZoomPos)
            CamHFoV, CamVFoV = self.calibrateFoV(ZoomPos, PanPos0, TiltPos0,
                                                 PanInc, TiltInc)
            CamHFoVList.append(CamHFoV)
            CamVFoVList.append(CamVFoV)

        return CamHFoVList, CamVFoVList

    def calibrateFoV(self, ZoomPos, PanPos0=150, TiltPos0=0,
                     PanInc=2, TiltInc=0):
        """
        Capture images at different pan/tilt angles, then measure the pixel
        displacement between the images to estimate the field-of-view angle.
        """
        self.Cam.setZoomPosition(ZoomPos)
        self.Cam.snapPhoto()
        # add nearby position to reduce backlash
        self.PanTil.setPanTiltPosition(PanPos0, TiltPos0)

        # capture image with pan motion
        ImagePanList = []
        for i in range(100):
            self.PanTil.setPanTiltPosition(PanPos0+PanInc*i,
                                           TiltPos0+TiltInc*i)
            # change zoom to force refocusing
            self.Cam.refocus()
            time.sleep(0.1)
            while True:
                Image = self.Cam.snapPhoto()
                if Image is not None:
                    ImagePanList.append(Image)
                    break
            if i == 0:
                continue
            Image0 = ImagePanList[0]
            Image1 = ImagePanList[i]
            dx, dy = getDisplacement(Image0, Image1)
            if PanInc != 0:
                CamHFoV = Image0.shape[1]*PanInc*i/dx
            if TiltInc != 0:
                CamVFoV = Image0.shape[0]*TiltInc*i/dy
            if dx > 100 or dy > 100:
                break

        # make an increment equal to 1/4 of FoV
        if PanInc != 0:
            PanFoVSmall = 0.25*CamHFoV
        else:
            PanFoVSmall = 0.25*CamVFoV*self.Cam.ImageSize[0]/self.Cam.ImageSize[1]
        self.PanTil.setPanTiltPosition(PanPos0 + PanFoVSmall, TiltPos0)
        while True:
            # make sure camera finishes refocusing
            Image1 = self.Cam.snapPhoto()
            if Image1 is not None:
                break
        dx, dy = getDisplacement(Image0, Image1)
        CamHFoV = Image0.shape[1]*PanFoVSmall/dx

        if TiltInc != 0:
            TiltFoVSmall = 0.25*CamVFoV
        else:
            TiltFoVSmall = 0.25*CamHFoV*self.Cam.ImageSize[1]/self.Cam.ImageSize[0]
        self.PanTil.setPanTiltPosition(PanPos0 + PanFoVSmall,
                                       TiltPos0 + TiltFoVSmall)
        while True:
            # make sure camera finishes refocusing
            Image2 = self.Cam.snapPhoto()
            if Image2 is not None:
                break
        dx, dy = getDisplacement(Image1, Image2)
        CamVFoV = Image0.shape[0]*TiltFoVSmall/dy

        return CamHFoV, CamVFoV

    def run(self, OutputFolder, Prefix="ARB-HILL-GV01", LastImageIndex=0,
            RecoveryFilename=None, ConfigFilename=None, Config=None,
            SecondsPerImage=7):
        if not os.path.exists(OutputFolder):
            os.makedirs(OutputFolder)
        if RecoveryFilename is not None and \
                not os.path.exists(os.path.dirname(RecoveryFilename)):
            os.makedirs(os.path.dirname(RecoveryFilename))
        if ConfigFilename is not None and \
                not os.path.exists(os.path.dirname(ConfigFilename)):
            os.makedirs(os.path.dirname(ConfigFilename))

        PanStep = (1-self.ImageOverlap)*self.CamHFoV
        TiltStep = (1-self.ImageOverlap)*self.CamVFoV
        PanPosList = np.arange(self.PanRange[0], self.PanRange[1], PanStep)
        TiltPosList = np.arange(self.TiltRange[1], self.TiltRange[0]-TiltStep,
                                -TiltStep)

        MaxNoImages = len(PanPosList)*len(TiltPosList)
        print("This panorama has {}(H) x {}(V) = {} images".format(
            len(PanPosList), len(TiltPosList), MaxNoImages))
        if LastImageIndex == 0:
            Minutes, Seconds = divmod(SecondsPerImage*MaxNoImages, 60)
            print("This will complete in about {} min:{} sec".format(
                Minutes, Seconds))
            print("PanStep = {} degree, TiltStep = {} degree".format(
                PanStep, TiltStep))
        else:
            NoImages = MaxNoImages - LastImageIndex
            print("Recover from last run.")
            print("This will take remaining {} images".format(NoImages))
            Minutes, Seconds = divmod(SecondsPerImage*NoImages, 60)
            print("This will complete in about {} min:{} sec".format(
                Minutes, Seconds))

        self.setZoom(self.CamZoom)
        time.sleep(0.2)
        StartTime = time.time()
        ImageCaptured = 0
        for i, PanPos in enumerate(PanPosList):
            for j, TiltPos in enumerate(TiltPosList):
                ImageIndex = i*len(TiltPosList) + j
                if ImageIndex < LastImageIndex:
                    continue

                Info = self.PanTil.setPanTiltPosition(PanPos, TiltPos)
                if len(Info) > 0:
                    print("Info: {}".format(Info))

                if Config is None:
                    FocusPos = self.Cam.refocus()
                else:
                    FocusPos = self.Cam.setFocusPosition(
                        Config["FocusPos"][ImageIndex])
                    if int(FocusPos) != Config["FocusPos"][ImageIndex]:
                        print("Warning: cannot set focus to {}".format(
                            Config["FocusPos"][ImageIndex]))
                time.sleep(0.1)

                if ConfigFilename is not None:
                    if not os.path.exists(ConfigFilename):
                        with open(ConfigFilename, 'w') as File:
                            File.write("ImgIndex,PanDeg,TiltDeg,Zoom,FocusPos\n")
                    with open(ConfigFilename, 'a') as File:
                        File.write("{},{},{},{},{}\n".format(
                            ImageIndex, PanPos, TiltPos, self.CamZoom,
                            self.Cam.getFocusPosition()))

                if RecoveryFilename is not None:
                    with open(RecoveryFilename, 'w') as File:
                        File.write("NoCols,NoRows,CurImgIndex,SecPerImg\n")
                        File.write("{},{},{},{}\n".format(
                            len(PanPosList), len(TiltPosList), ImageIndex,
                            SecondsPerImage))

                while True:
                    Now = datetime.now()
                    FileName = os.path.join(OutputFolder,
                                            "{}_{}_00_00_{:04}.jpg".format(
                                            Prefix,
                                            Now.strftime("%Y_%m_%d_%H_%M"),
                                            ImageIndex))
                    FileName2 = self.Cam.snapPhoto2File(FileName)

                    if FileName2 == FileName and \
                            os.path.getsize(FileName) > 1000:
                        print("Wrote image " + FileName)
                        break
                    else:
                        os.remove(FileName)
                        print("Warning: invalid image file size. Try again.")

                # update time per image
                CurrentTime = time.time()
                ImageCaptured += 1
                SecondsPerImage = (CurrentTime - StartTime)/ImageCaptured
        # finally remove this file
        os.remove(RecoveryFilename)


def PanoDemo(Camera_IP, Camera_User, Camera_Password,
             PanTil_IP,
             OutputFolder, ConfigFilename=None):
    ImageSize = [1920, 1080]
    Zoom = 800  # 1050
    ZoomList = range(50, 1100, 100)
    CamHFoVList = [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126,
                   12.782, 9.217, 7.050, 5.824]
    CamVFoVList = [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324,
                   7.7136, 4.787, 3.729, 2.448]
    PanRange = [80, 200]
    TiltRange = [-20, 20]

    Pano = Panorama(Camera_IP, Camera_User, Camera_Password, PanTil_IP)
    Pano.setImageSize(ImageSize)
    Pano.setCameraFovDist(ZoomList, CamHFoVList, CamVFoVList)
    Pano.setZoom(Zoom)
    Pano.setFoVFromZoom(Zoom)
    Pano.setPanoramaFoVRange(PanRange, TiltRange)
    print("CamHFoV = {}, CamVFoV = {}".format(Pano.CamHFoV, Pano.CamVFoV))

    if ConfigFilename is not None:
        with open(ConfigFilename) as File:
            Fields = ["ImgIndex", "PanDeg", "TiltDeg", "Zoom", "FocusPos"]
            csvread = csv.DictReader(ConfigFilename, Fields)
            Config = {"ImgIndex": [], "PanDeg": [], "TiltDeg": [],
                      "Zoom": [], "FocusPos": []}
            for row in csvread:
                Config["ImgIndex"].append(int(row["ImgIndex"]))
                Config["PanDeg"].append(float(row["PanDeg"]))
                Config["TiltDeg"].append(float(row["TiltDeg"]))
                Config["Zoom"].append(int(row["Zoom"]))
                Config["FocusPos"].append(int(row["FocusPos"]))

    Config = None
    while True and os.path.exists(OutputFolder):
        Now = datetime.now()
        PanoFolder = os.path.join(OutputFolder,
                                  Now.strftime("%Y"),
                                  Now.strftime("%Y_%m"),
                                  Now.strftime("%Y_%m_%d"),
                                  Now.strftime("%Y_%m_%d_%H"))
        RecoveryFilename = os.path.join(PanoFolder, "_data", "recovery.csv")
        ConfigFilename = os.path.join(PanoFolder, "_data", "config.csv")
        if os.path.exists(RecoveryFilename):
            with open(RecoveryFilename, "r") as File:
                # header "NoCols,NoRows,CurImgIndex,SecPerImg"
                try:
                    line = File.readline()  # skip header
                    line = File.readline()
                    nums = [float(num) for num in line.split(",")]
                except:
                    nums = None
            if nums is not None and len(nums) == 4:
                RemainingSeconds = (nums[0]*nums[1] - nums[2])*nums[3]
                if RemainingSeconds//60 + int(Now.strftime("%M")) <= 60:
                    # remove last file that may be corrupted
                    FileList = glob.glob(
                        os.path.join(PanoFolder, "{:04}.jpg".format(nums[2])))
                    if len(FileList) > 0:
                        for Filename in FileList:
                            os.remove(Filename)

                    Pano.run(PanoFolder, LastImageIndex=nums[2],
                             RecoveryFilename=RecoveryFilename,
                             ConfigFilename=ConfigFilename, Config=Config)
                    continue
                else:
                    print("Found recovery data but it's too late to recover.")

        Now = datetime.now()
        PanoFolder = os.path.join(OutputFolder,
                                  Now.strftime("%Y"),
                                  Now.strftime("%Y_%m"),
                                  Now.strftime("%Y_%m_%d"),
                                  Now.strftime("%Y_%m_%d_%H"))
        RecoveryFilename = os.path.join(PanoFolder, "_data", "recovery.csv")
        ConfigFilename = os.path.join(PanoFolder, "_data", "config.csv")
        if int(Now.strftime("%M")) <= 10:
            print("Started recording new panorama at {}".format(PanoFolder))
#            Pano.test()
            if os.path.exists(PanoFolder):
                shutil.rmtree(PanoFolder)
            Pano.run(PanoFolder, RecoveryFilename=RecoveryFilename,
                     ConfigFilename=ConfigFilename, Config=Config)

        Now = datetime.now()
        RemainingMinutes = 60-int(Now.strftime("%M"))
        print("It's {}.".format(Now.strftime("%H:%M"))),
        print("Wait for {} minutes before start.".format(RemainingMinutes))
        time.sleep(RemainingMinutes*60)


if __name__ == "__main__":
    Camera_IP = "192.168.1.100"
    Camera_User = "Admin"
    Camera_Password = "123456"
    PanTil_IP = "192.168.1.101:81"
    OutputFolder = "/home/chuong/Data/a_data/Gigavision/chuong_tests/"
    ConfigFileName = None

    PanoDemo(Camera_IP, Camera_User, Camera_Password, PanTil_IP,
             OutputFolder, ConfigFileName)
