# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
"""

import sys
import cv2
import urllib
import numpy as np
import time
import re


class IPCamera(object):
    """
    Control ACTi Camera
    Ref: http://www2.acti.com/getfile/KnowledgeBase_UploadFile/ACTi_Camera_URL_Commands_20120327_002.pdf
    """
    def __init__(self, IP, User, Password, ImageSize=None):
        self.IP = IP
        self.HTTPLogin = "http://{}/cgi-bin/encoder?"\
            "USER={}&PWD={}".format(IP, User, Password)
        self.IMAGE_SIZES = [[1920, 1080], [1280, 720], [640, 480]]
        if ImageSize:
            assert(ImageSize in self.IMAGE_SIZES)
            self.ImageSize = ImageSize
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

        self.Commands["snap_photo"] = "&SNAPSHOT=N{}x{},100&DUMMY={}"

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

    def snapPhoto(self, ImageSize=None):
        if ImageSize and ImageSize in self.IMAGE_SIZES:
            stream = urllib.urlopen(self.HTTPLogin +
                                    self.Commands["snap_photo"].format(
                                        ImageSize[0], ImageSize[1],
                                        self.PhotoIndex))
        else:
            stream = urllib.urlopen(self.HTTPLogin +
                                    self.Commands["snap_photo"].format(
                                        self.ImageSize[0], self.ImageSize[1],
                                        self.PhotoIndex))
        jpg_bytearray = np.asarray(bytearray(stream.read()), dtype=np.uint8)
        self.Image = cv2.imdecode(jpg_bytearray, cv2.CV_LOAD_IMAGE_COLOR)
        self.PhotoIndex += 1
        return self.Image

    def getValue(self, Text):
        Text = Text.split("=")
        TextValue = re.sub("'", "", Text[1])
        ValueList = TextValue.split(",")
        ValueList = [float(Value) if Value.isdigit() else Value
                     for Value in ValueList]
        return ValueList

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
                                    "Direct", AbsPosition))
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
#            if Value.isdigit():
#                return float(Value)
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
        return Info

    def setPanPosition(self, Degree):
        Info = self.setPanTiltPosition(PanDegree=Degree)
#        Url = self.Link + "/CP_Update.xml"
#        stream = urllib.urlopen(Url)
#        Output = stream.read(1024)
#        self.PanPos = self.getKeyValue(Output, "PanPos")  # degrees
#        while self.PanPos != "{f}"Degree
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


def liveViewDemo(Camera, PanTil):
    WindowName = "Live view from {}".format(Camera.IP)
    while True:
        Image = Camera.snapPhoto()
        if Image is not None:
            cv2.imshow(WindowName, Image)
        time.sleep(0.1)
        if sys.platform == 'win32':
            Key = cv2.waitKey(50)
        else:
            Key = 0xFF & cv2.waitKey(50)

        Info = ""
        if Key == 27:
            break
        elif Key == 81 or Key == 2424832:  # arrow left key
            Info = PanTil.panStep("left", 10)
            Info = PanTil.getPanPosition()
        elif Key == 83 or Key == 2555904:  # arrow right key
            Info = PanTil.panStep("right", 10)
            Info = PanTil.getPanPosition()
        elif Key == 82 or Key == 2490368:  # arrow up key
            Info = PanTil.tiltStep("up", 10)
            Info = PanTil.getTiltPosition()
        elif Key == 84 or Key == 2621440:  # arrow down key
            Info = PanTil.tiltStep("down", 10)
            Info = PanTil.getTiltPosition()
        elif Key == 85 or Key == 2162688:  # page up key
            Info = Camera.zoomStep("in", 100)
            Info = Camera.getZoomPosition()
        elif Key == 86 or Key == 2228224:  # page down key
            Info = Camera.zoomStep("out", 100)
            Info = Camera.getZoomPosition()
        elif Key == 115:  # s key
            Info = PanTil.status()
            Info += "\n" + Cam.status()
        elif Key != 255:
            print("Key = {} is not recognised".format(Key))

        if len(Info) > 0:
            print(Info)


def liveViewDemo2(Camera, PanTil):
    PanRange = [19, 337]
    TiltRange = [-85, 24]
    ZoomRange = [30, 1000]  # actual range
    PanPos = 150
    TiltPos = 0
    ZoomPos = 30

    def pan(PanIntValue):
        PanPos = PanRange[0] + PanIntValue
        print("PanPos={}, TiltPos={}".format(PanPos, TiltPos))
        PanTil.setPanTiltPosition(PanPos, TiltPos)

    def tilt(TiltIntValue):
        TiltPos = TiltRange[0] + TiltIntValue
        print("PanPos={}, TiltPos={}".format(PanPos, TiltPos))
        PanTil.setPanTiltPosition(PanPos, TiltPos)

    def zoom(ZoomIntValue):
        ZoomPos = ZoomRange[0] + ZoomIntValue
        Camera.setZoomPosition(ZoomPos)

    WindowName = "Live view from {}".format(Camera.IP)
    TrackbarNamePan = "Pan"
    TrackbarNameTilt = "Tilt"
    TrackbarNameZoom = "Zoom"
    cv2.namedWindow(WindowName)
    cv2.createTrackbar(TrackbarNamePan, WindowName,
                       PanPos - PanRange[0], PanRange[1]-PanRange[0], pan)
    cv2.createTrackbar(TrackbarNameTilt, WindowName,
                       TiltPos - TiltRange[0], TiltRange[1]-TiltRange[0], tilt)
    cv2.createTrackbar(TrackbarNameZoom, WindowName,
                       ZoomPos - ZoomRange[0], ZoomRange[1]-ZoomRange[0], zoom)
    pan(PanPos - PanRange[0])
    tilt(TiltPos - TiltRange[0])
    zoom(ZoomPos - ZoomRange[0])
    while True:
        Image = Camera.snapPhoto()
        if Image is not None:
            cv2.imshow(WindowName, Image)
        if sys.platform == 'win32':
            Key = cv2.waitKey(100)
        else:
            Key = 0xFF & cv2.waitKey(100)

        Info = ""
        if Key == 27:
            break
        elif Key == 115:  # s key
            Info = PanTil.status()
            Info += "\n" + Cam.status()
        elif Key != 255:
            print("Key = {} is not recognised".format(Key))

        if len(Info) > 0:
            print(Info)


def testFoV(Camera, PanTil):
    ZoomRange = [30, 1000]  # actual range
    ZoomList   = [ 0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    PanFoVList = [44,  37,  31,  25,  19,  15,  12,   8,   5,   3]
#    PixPerDegree = [12.227, 15.514, 18.774, 23.00, 28.895, 37.267,
#                    49.417, 67.375, 100.2, 149.0]
#    FoVAngle = [Camera.ImageSize[0]/val for val in PixPerDegree]
    PanPos0 = 150
    TiltPos0 = 0
    Folder = "/home/chuong/Workspace/ackwEYEr/images/"
    Camera.setZoomPosition(ZoomList[0] + ZoomRange[0])
    cv2.waitKey(5000)
    Image = Camera.snapPhoto()
    Image = Camera.snapPhoto()
    Image = Camera.snapPhoto()
    for ZoomPos, PanFoV in zip(ZoomList, PanFoVList):
        ZoomPos = ZoomPos + ZoomRange[0]
        Camera.setZoomPosition(ZoomPos)
        cv2.waitKey(5000)
        PanPos = PanPos0
        # add nearby position to reduce backlash
        PanTil.setPanTiltPosition(PanPos-20, TiltPos0)
        cv2.waitKey(5000)
        PanTil.setPanTiltPosition(PanPos, TiltPos0)
        cv2.waitKey(5000)
        while True:
            # make sure camera finishes refocusing
            Image = Camera.snapPhoto()
            Image = Camera.snapPhoto()
            Image = Camera.snapPhoto()
            if Image is not None:
                FileName = Folder + "image_{}_{}.jpg".format(ZoomPos, PanPos)
                cv2.imwrite(FileName, Image)
                print("Wrote image " + FileName)
                break
        PanPos = PanPos0 + PanFoV
        PanTil.setPanTiltPosition(PanPos, TiltPos0)
        cv2.waitKey(5000)
        while True:
            # make sure camera finishes refocusing
            Image = Camera.snapPhoto()
            Image = Camera.snapPhoto()
            Image = Camera.snapPhoto()
            if Image is not None:
                FileName = Folder + "image_{}_{}.jpg".format(ZoomPos, PanPos)
                cv2.imwrite(FileName, Image)
                print("Wrote image " + FileName)
                break


def getFieldOfView(Camera, PanTil,
                   PanPosList=range(0, 10, 2),
                   TiltPosList=range(0, 10, 2),
                   ZoomList=range(50, 1000, 100)):
    """
    This can take a long time to run
    """
    Camera.setZoomPosition(ZoomList[0]-10)
    PanTil.setPanTiltPosition(PanPosList[0]-10, TiltPosList[0]-10)
    cv2.waitKey(5000)


def panorama(Camera, PanTil, Zoom=300,
             PanRange=[80, 220], TiltRange=[-20, 20],
             Folder="/home/chuong/Workspace/ackwEYEr/images/panorama/",
             Overlap=0.5):
#    ZoomList = [ 0, 100, 200, 300, 400, 500, 600, 700, 800, 900]  # +30
    PixPerDegree = [12.227, 15.514, 18.774, 23.00, 28.895, 37.267,
                    49.417, 67.375, 100.2, 149.0]
    PanStep = int((1-Overlap)*Camera.ImageSize[0]/PixPerDegree[3])
    TiltStep = int((1-Overlap)*Camera.ImageSize[1]/PixPerDegree[3])
    print("PanStep = {}, TiltStep = {}".format(PanStep, TiltStep))

    Camera.setZoomPosition(Zoom - 5)
    Image = Camera.snapPhoto()
    Image = Camera.snapPhoto()
    Image = Camera.snapPhoto()
    cv2.waitKey(5000)
    PanTil.setPanTiltPosition(PanRange[0]-5, TiltRange[0]-5)
    cv2.waitKey(10000)

    # scan top down from left to right
    for i, PanPos in enumerate(range(PanRange[0], PanRange[1], PanStep)):
        for j, TiltPos in enumerate(range(TiltRange[1], TiltRange[0]-TiltStep,
                                          -TiltStep)):
            PanTil.setPanTiltPosition(PanPos, TiltPos)
            cv2.waitKey(5000)
            while True:
                # make sure camera finishes refocusing
                Image = Camera.snapPhoto()
                if Image is not None:
                    FileName = Folder + "image_{}_{}_{}.jpg".format(
                        Zoom, i, j)
                    cv2.imwrite(FileName, Image)
                    print("Wrote image " + FileName)
                    break
        # move backward a bit over to avoid back lash
        PanTil.setPanTiltPosition(PanRange[0]-5, TiltPos)
        cv2.waitKey(10000)

if __name__ == "__main__":
    Camera_IP = "192.168.1.100"
    Camera_User = "Admin"
    Camera_Password = "123456"
    Camera_ImageSize = [1920, 1080]  # [640, 480]  #
    Cam = IPCamera(Camera_IP, Camera_User, Camera_Password, Camera_ImageSize)

    PanTil_IP = "192.168.1.101"
    PanTil = PanTilt(PanTil_IP)

#    liveViewDemo(Cam, PanTil)
#    liveViewDemo2(Cam, PanTil)
#    testFoV(Cam, PanTil)
    panorama(Cam, PanTil)

