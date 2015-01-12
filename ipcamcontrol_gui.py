# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong
"""

from __future__ import absolute_import, division, print_function

import sys
import time
from PyQt4 import QtGui, QtCore, uic
import yaml
import os
import numpy as np
import scipy.misc as misc
import urllib
import io
from datetime import datetime


def executeURL(URL_Str, RET_Str=None):
    if "http://" not in URL_Str:
        URL_Str = "http://" + URL_Str
#    print(URL_Str)
#    print(RET_Str)
    if RET_Str is None:
        stream = urllib.urlopen(URL_Str)
    elif RET_Str == "RAW_JPG" or RET_Str == "RAW_BMP":
        try:
            import PIL.Image
            stream = urllib.urlopen(URL_Str)
            byte_array = io.BytesIO(stream.read())
            Image = np.array(PIL.Image.open(byte_array))
            return Image
        except:
            import tempfile
            from scipy import misc
            ImageFilename = os.path.join(tempfile.gettempdir(), "image.jpg")
            urllib.urlretrieve(URL_Str, ImageFilename)
            Image = misc.imread(ImageFilename)
            return Image
    else:
        stream = urllib.urlopen(URL_Str)
        Output = stream.read(1024).strip()
#        print(Output)
        StrList = RET_Str.split("*")
        StrList = [Str for Str in StrList if len(Str) > 0]
#        print(StrList)
        Vals = []
        for Str in StrList:
            WordList = Str.split("{}")
            WordList = [Word for Word in WordList if len(Word) > 0]
#            print(WordList)
            if len(WordList) == 1:
                Pos = Output.find(WordList[0])
                if Pos >= 0:
                    Val = Output[Pos + len(WordList[0]):]
                    ValList = Val.split("\n")
                    Vals.append(ValList[0].strip())
            elif len(WordList) == 2:
                Pos1 = Output.find(WordList[0])
                Pos2 = Output.find(WordList[1], Pos1 + len(WordList[0]))
                if Pos1 >= 0 and Pos2 >= Pos1:
                    Vals.append(Output[Pos1 + len(WordList[0]):Pos2])
            else:
                print("Unhandled case {}". format(Str))
        if len(Vals) == 1:
            return Vals[0]
#        print(Vals)
        return Vals

form_class = uic.loadUiType("controller2.ui")[0]


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.pushButtonStartCamera.clicked.connect(self.startCamera)
        self.pushButtonSnapPhoto.clicked.connect(self.snapPhoto)
        self.pushButtonStopCamera.clicked.connect(self.stopCamera)
        self.pushButtonLoadCameraConfigFile.clicked.connect(
            self.loadCameraConfig)

        self.pushButtonStartPanTilt.clicked.connect(self.startPanTilt)
        self.pushButtonStopPanTilt.clicked.connect(self.stopPanTilt)
        self.pushButtonLoadPanTiltConfigFile.clicked.connect(
            self.loadPanTiltConfig)

        self.horizontalSliderPan.valueChanged.connect(self.setPan)
        self.horizontalSliderTilt.valueChanged.connect(self.setTilt)
        self.horizontalSliderZoom.valueChanged.connect(self.setZoom2)
        self.pushButtonCurrentAsViewFirstCorner.clicked.connect(
            self.setCurrentAsViewFirstCorner)
        self.pushButtonCurrentAsViewSecondCorner.clicked.connect(
            self.setCurrentAsViewSecondCorner)
        self.pushButtonCalculateFoV.clicked.connect(self.calculateFoV)

        self.pushButtonCurrentAsPanoFirstCorner.clicked.connect(
            self.setCurrentAsFirstCorner)
        self.pushButtonGotoFirstCorner.clicked.connect(
            self.gotoFirstCorner)
        self.pushButtonCurrentAsPanoSecondCorner.clicked.connect(
            self.setCurrentAsSecondCorner)
        self.pushButtonGotoSecondCorner.clicked.connect(
            self.gotoSecondCorner)
        self.pushButtonCalculatePanoGrid.clicked.connect(self.calculatePanoGrid)
        self.pushButtonPanoFolder.clicked.connect(self.selectPanoFolder)
        self.pushButtonTakeOnePano.clicked.connect(self.takeOnePanorama)

        self.initilisedCamera = False
        self.initilisedPanTilt = False
        self.PanPos = 0
        self.TiltPos = 0
        self.ZoomPos = 0
        self.FocusPos = 0
        self.HFoV = 0
        self.VFoV = 0
        self.Overlap = 0.0
        self.TopLeftCorner = []
        self.BottomRIghtCorner = []
        self.PanoImageNo = 0
        self.threadPool = []
        self.hasMJPGVideo = False

    def snapPhoto(self):
        while True:
            URL_Str = self.CamConfigUpdated["URL_GetImage"]
            RET_Str = self.CamConfigUpdated["RET_GetImage"]
            self.Image = executeURL(URL_Str, RET_Str)
            yield self.Image

    def streamVideo(self):
        import PIL.Image
#        import cv2
        URL_Str = self.CamConfigUpdated["URL_GetVideo"]
        if "http://" not in URL_Str:
            URL_Str = "http://" + URL_Str
        stream = urllib.urlopen(URL_Str)
        byte = ''
        while True:
            byte += stream.read(1024)
            a = byte.find('\xff\xd8')
            b = byte.find('\xff\xd9')
            if a != -1 and b != -1:
                jpg = byte[a:b+2]
                byte = byte[b+2:]
                byte_array = io.BytesIO(jpg)
                self.Image = np.array(PIL.Image.open(byte_array))
#                Image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.CV_LOAD_IMAGE_COLOR)
                yield self.Image

    def setCurrentAsViewFirstCorner(self):
        self.lineEditViewFirstCorner.setText("{},{}".format(self.PanPos,
                                                            self.TiltPos))

    def setCurrentAsViewSecondCorner(self):
        self.lineEditViewSecondCorner.setText("{},{}".format(self.PanPos,
                                                             self.TiltPos))

    def calculateFoV(self):
        Pan1, Tilt1 = self.lineEditViewFirstCorner.text().split(",")
        Pan2, Tilt2 = self.lineEditViewSecondCorner.text().split(",")
        HFoV = abs(float(Pan1)-float(Pan2))
        VFoV = abs(float(Tilt1)-float(Tilt2))
        if HFoV >= VFoV and HFoV <= 2*VFoV:
            self.HFoV = HFoV
            self.VFoV = VFoV
            self.lineEditFieldOfView.setText("{},{}".format(HFoV, VFoV))
            self.lineEditFieldOfView_2.setText("{},{}".format(HFoV, VFoV))
        else:
            print("Invalid selection of field of view")

    def setCurrentAsFirstCorner(self):
        self.lineEditPanoFirstCorner.setText("{},{}".format(self.PanPos,
                                                            self.TiltPos))

    def setCurrentAsSecondCorner(self):
        self.lineEditPanoSecondCorner.setText("{},{}".format(self.PanPos,
                                                             self.TiltPos))

    def gotoFirstCorner(self):
        PANVAL, TILTVAL = self.lineEditPanoFirstCorner.text().split(",")
        self.setPanTilt(PANVAL, TILTVAL)

    def gotoSecondCorner(self):
        PANVAL, TILTVAL = self.lineEditPanoSecondCorner.text().split(",")
        self.setPanTilt(PANVAL, TILTVAL)

    def calculatePanoGrid(self):
        Pan0, Tilt0 = self.lineEditPanoFirstCorner.text().split(",")
        Pan1, Tilt1 = self.lineEditPanoSecondCorner.text().split(",")
        HFoV, VFoV = self.lineEditFieldOfView.text().split(",")
        self.Overlap = float(self.comboBoxPanoOverlap.currentText())/100
        if float(Pan0) <= float(Pan1):
            LeftPan = float(Pan0)
            RightPan = float(Pan1)
        else:
            LeftPan = float(Pan1)
            RightPan = float(Pan0)
        if float(Tilt0) >= float(Tilt1):
            TopTilt = float(Tilt0)
            BottomTilt = float(Tilt1)
        else:
            TopTilt = float(Tilt1)
            BottomTilt = float(Tilt0)
        self.TopLeftCorner = [LeftPan, TopTilt]
        self.BottomRightCorner = [RightPan, BottomTilt]
        self.PanoRows = int(round((TopTilt - BottomTilt)/float(VFoV)/self.Overlap))
        self.PanoCols = int(round((RightPan - LeftPan)/float(HFoV)/self.Overlap))
        self.lineEditPanoGridSize.setText("{}x{}".format(
            self.PanoRows, self.PanoCols))
        if self.PanoRows >= 0 or self.PanoCols >= 0:
            self.pushButtonTakeOnePano.setEnabled(True)
            self.pushButtonLoopPanorama.setEnabled(True)
            Scale = 2
            while Scale > 0:
                ScaledHeight = int(Scale*self.Image.shape[0])
                ScaledWidth = int(Scale*self.Image.shape[1])
                if ScaledHeight*self.PanoRows <= 1080 and \
                        ScaledWidth*self.PanoCols <= 1920:
                    break
                Scale = Scale - 0.001
            print(ScaledHeight*self.PanoRows, ScaledWidth*self.PanoCols, Scale)
            self.PanoOverViewScale = Scale
            self.PanoOverView = np.zeros_like(self.Image)
            self.PanoOverView = np.resize(self.PanoOverView,
                                          (ScaledHeight*self.PanoRows,
                                           ScaledWidth*self.PanoCols,
                                           self.Image.shape[2]))
            # add lines shows rows and columns
            for i in range(self.PanoCols):
                self.PanoOverView[:, ScaledWidth*i: ScaledWidth*i+1, :] = 255
            for j in range(self.PanoRows):
                self.PanoOverView[ScaledHeight*j:ScaledHeight*j+1, :, :] = 255

            self.updatePanoOverView()

    def updatePanoOverView(self):
        height, width, bytesPerComponent = self.PanoOverView.shape
        bytesPerLine = bytesPerComponent * width
        QI = QtGui.QImage(self.PanoOverView.data,
                          self.PanoOverView.shape[1],
                          self.PanoOverView.shape[0],
                          bytesPerLine, QtGui.QImage.Format_RGB888)
        self.labelPanoOverviewImage.setPixmap(
            QtGui.QPixmap.fromImage(QI))
        self.labelPanoOverviewImage.setScaledContents(True)
        self.labelPanoOverviewImage.setGeometry(
            QtCore.QRect(0, 0, self.PanoOverView.shape[1],
                         self.PanoOverView.shape[0]))

    def selectPanoFolder(self):
        Folder = QtGui.QFileDialog.getExistingDirectory(self, "Select Directory")
        if len(Folder) > 0:
            self.lineEditPanoFolder.setText(Folder)

    def takeOnePanorama(self):
        self.calculatePanoGrid()  # make sure everything is up-to-date
        self.PanoImageNo = 0
        if not os.path.exists(str(self.lineEditPanoFolder.text())):
            self.lineEditPanoFolder.setText(self.selectPanoFolder())

        Now = datetime.now()
        self.PanoFolder = os.path.join(str(self.lineEditPanoFolder.text()),
                                       Now.strftime("%Y"),
                                       Now.strftime("%Y_%m"),
                                       Now.strftime("%Y_%m_%d"),
                                       Now.strftime("%Y_%m_%d_%H"))
        if not os.path.exists(self.PanoFolder):
            os.makedirs(self.PanoFolder)

        self.threadPool.append(PanoThread(self))
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('PanoImageSnapped()'), self.updatePanoImage)
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('PanTiltPos(QString)'),
                     self.updatePanTiltInfo)
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('PanoThreadStarted()'),
                     self.deactivateLiveView)
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('PanoThreadDone()'),
                     self.activateLiveView)
        self.threadPool[len(self.threadPool)-1].start()

    def activateLiveView(self):
        self.startPanTilt()
        self.startCamera()

    def deactivateLiveView(self):
        self.stopPanTilt()
        self.stopCamera()

    def updatePanoImage(self):
        self.updateImage()
        self.updatePanoOverView()
        Prefix = "Image"
        Now = datetime.now()
        FileName = os.path.join(self.PanoFolder,
                                "{}_{}_00_00_{:04}.jpg".format(
                                Prefix,
                                Now.strftime("%Y_%m_%d_%H_%M"),
                                self.PanoImageNo))
        misc.imsave(FileName, self.Image)

        if os.path.getsize(FileName) > 1000:
            print("Wrote image " + FileName)
        else:
            print("Warning: failed to snap an image")

        self.PanoImageNo += 1

    def setPan(self, Pan):
        self.setPanTilt(Pan, self.TiltPosDesired)

    def setTilt(self, Tilt):
        self.setPanTilt(self.PanPosDesired, Tilt)

    def setZoom2(self, Zoom):
        self.setZoom(Zoom)
        self.lineEditZoom.setText(str(Zoom))
        self.updateFoVFromZoom(Zoom)

    def updateFoVFromZoom(self, Zoom):
        if "Zoom_HorFoVList" in self.CamConfigUpdated.keys():
            ZoomList = self.CamConfigUpdated["Zoom_HorFoVList"][0]
            HFoVList = self.CamConfigUpdated["Zoom_HorFoVList"][1]
            self.HFoV = np.interp(int(Zoom), ZoomList, HFoVList)
        if "Zoom_VirFoVList" in self.CamConfigUpdated.keys():
            ZoomList = self.CamConfigUpdated["Zoom_VirFoVList"][0]
            VFoVList = self.CamConfigUpdated["Zoom_VirFoVList"][1]
            self.VFoV = np.interp(int(Zoom), ZoomList, VFoVList)
        if self.HFoV != 0 and self.VFoV != 0:
            self.lineEditFieldOfView.setText("{},{}".format(self.HFoV, self.VFoV))
            self.lineEditFieldOfView_2.setText("{},{}".format(self.HFoV, self.VFoV))

    def setPanTilt(self, Pan, Tilt, Verified=False):
        PanTiltScale = 1
        if "PanTiltScale" in self.PanTiltConfigUpdated.keys():
            PanTiltScale = self.PanTiltConfigUpdated["PanTiltScale"]
        PANVAL = str(int(float(Pan)*PanTiltScale))
        TILTVAL = str(int(float(Tilt)*PanTiltScale))
        URL = self.PanTiltConfigUpdated["URL_SetPanTilt"].replace("PANVAL",
                                                                  PANVAL)
        URL = URL.replace("TILTVAL", TILTVAL)
        executeURL(URL)

        if Verified:
            NoLoops = 0
            # loop until within 1 degree
            while True:
                PanCur, TiltCur = self.getPanTilt()
                PanDiff = int(abs(float(PanCur) - float(Pan)))
                TiltDiff = int(abs(float(TiltCur) - float(Tilt)))
                if PanDiff <= 1 and TiltDiff <= 1:
                    break
                time.sleep(0.1)
                NoLoops += 1
                if NoLoops > 50:
                    print("Warning: pan-tilt fails to move to correct location")
                    print("  Desired position: PanPos={}, TiltPos={}".format(
                        Pan, Tilt))
                    print("  Current position: PanPos={}, TiltPos={}".format(
                        PanCur, TiltCur))
                    break
            #loop until smallest distance is reached
            while True:
                PanPos, TiltPos = self.getPanTilt()
                PanDiffNew = abs(float(PanCur) - float(Pan))
                TiltDiffNew = abs(float(TiltCur) - float(Tilt))
                if PanDiffNew <= 0.1 and TiltDiffNew <= 0.1:
                    break
                elif PanDiffNew >= PanDiff or TiltDiffNew >= TiltDiff:
                    break
                else:
                    PanDiff = PanDiffNew
                    TiltDiff = TiltDiffNew
                time.sleep(0.1)
                NoLoops += 1
                if NoLoops > 50:
                    break

        self.PanPosDesired = float(Pan)
        self.TiltPosDesired = float(Tilt)
        self.horizontalSliderPan.setValue(int(self.PanPosDesired))
        self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))

    def getPanTilt(self):
        URL = self.PanTiltConfigUpdated["URL_GetPanTilt"]
        RET = self.PanTiltConfigUpdated["RET_GetPanTilt"]
        Pan, Tilt = executeURL(URL, RET)
        return Pan, Tilt

    def setZoom(self, ZOOMVAL):
        URL = self.CamConfigUpdated["URL_SetZoom"].replace("ZOOMVAL",
                                                           str(ZOOMVAL))
        executeURL(URL)
        self.ZoomPos = int(ZOOMVAL)

    def getZoom(self):
        URL = self.CamConfigUpdated["URL_GetZoom"]
        RET = self.CamConfigUpdated["RET_GetZoom"]
        ZOOMVAL = executeURL(URL, RET)
        ZoomScale = 1
        if "ZoomScale" in self.CamConfigUpdated.keys():
            ZoomScale = self.CamConfigUpdated["ZoomScale"]
        ZOOMVAL = int(float(ZOOMVAL)*ZoomScale)
        return ZOOMVAL

    def getFocus(self):
        URL = self.CamConfigUpdated["URL_GetFocus"]
        RET = self.CamConfigUpdated["RET_GetFocus"]
        FOCUSVAL = executeURL(URL, RET)
        return FOCUSVAL

    def loadPanTiltConfig(self):
        Filename = self.lineEditPanTiltConfigFilename.text()
        if len(Filename) == 0 or not os.path.exists(Filename):
            Filename = QtGui.QFileDialog.getOpenFileName(
                self, 'Open pan-tilt config file', Filename)
        with open(Filename, 'r') as ConfigFile:
            self.lineEditPanTiltConfigFilename.setText(Filename)
            self.PanTiltConfig = yaml.load(ConfigFile)
            self.textEditMessages.append("Loaded {}:".format(Filename))
            self.textEditMessages.append("----------")
            self.textEditMessages.append(yaml.dump(self.PanTiltConfig))
            if "IPVAL" in self.PanTiltConfig.keys():
                self.lineEditPanTiltAddress.setText(
                    self.PanTiltConfig["IPVAL"])
            if "USERVAL" in self.PanTiltConfig.keys():
                self.lineEditPanTiltUsername.setText(
                    self.PanTiltConfig["USERVAL"])
            if "PASSVAL" in self.PanTiltConfig.keys():
                self.lineEditPanTiltPassword.setText(
                    self.PanTiltConfig["PASSVAL"])
            if "PanRange" in self.PanTiltConfig.keys():
                self.horizontalSliderPan.setMinimum(
                    self.PanTiltConfig["PanRange"][0])
                self.horizontalSliderPan.setMaximum(
                    self.PanTiltConfig["PanRange"][1])
            if "TiltRange" in self.PanTiltConfig.keys():
                self.horizontalSliderTilt.setMinimum(
                    self.PanTiltConfig["TiltRange"][0])
                self.horizontalSliderTilt.setMaximum(
                    self.PanTiltConfig["TiltRange"][1])

    def updatePanTiltURLs(self):
        self.PanTiltConfigUpdated = {}
        for Key in self.PanTiltConfig.keys():
            if "URL" in Key:
                text = self.PanTiltConfig[Key]
                text = text.replace("IPVAL", self.PanTiltIP)
                text = text.replace("USERVAL", self.PanTiltUsername)
                text = text.replace("PASSVAL", self.PanTiltPassword)
                self.PanTiltConfigUpdated[Key] = text
            else:
                self.PanTiltConfigUpdated[Key] = self.PanTiltConfig[Key]
        self.textEditMessages.append("Updated pan-tilt configs:")
        self.textEditMessages.append("----------")
        self.textEditMessages.append(yaml.dump(self.PanTiltConfigUpdated))

    def loadCameraConfig(self):
        Filename = self.lineEditCameraConfigFilename.text()
        if len(Filename) == 0 or not os.path.exists(Filename):
            Filename = QtGui.QFileDialog.getOpenFileName(
                self, 'Open camera config file', Filename)
        with open(Filename, 'r') as ConfigFile:
            self.lineEditCameraConfigFilename.setText(Filename)
            self.CamConfig = yaml.load(ConfigFile)
            self.textEditMessages.append("Loaded {}:".format(Filename))
            self.textEditMessages.append("----------")
            self.textEditMessages.append(yaml.dump(self.CamConfig))
            if "IPVAL" in self.CamConfig.keys():
                self.lineEditIPCamAddress.setText(self.CamConfig["IPVAL"])
            if "USERVAL" in self.CamConfig.keys():
                self.lineEditIPCamUsername.setText(self.CamConfig["USERVAL"])
            if "PASSVAL" in self.CamConfig.keys():
                self.lineEditIPCamPassword.setText(self.CamConfig["PASSVAL"])
            if "ImageSizeList" in self.CamConfig.keys():
                for ImageSize in self.CamConfig["ImageSizeList"]:
                    self.comboBoxImageSize.addItem(
                        "{},{}".format(ImageSize[0], ImageSize[1]))
            if "ZoomVal" in self.CamConfig.keys():
                self.lineEditZoom.setText(str(self.CamConfig["ZoomVal"]))
            if "ZoomRange" in self.CamConfig.keys():
                self.horizontalSliderZoom.setRange(
                    int(self.CamConfig["ZoomRange"][0]),
                    int(self.CamConfig["ZoomRange"][1]))
            if "URL_SetFocusAuto" in self.CamConfig.keys():
                self.comboBoxFocusMode.addItem("AUTO")
            if "URL_SetFocusManual" in self.CamConfig.keys():
                self.comboBoxFocusMode.addItem("MANUAL")
            if "FocusVal" in self.CamConfig.keys():
                self.lineEditFocus.setText(str(self.CamConfig["FocusVal"]))
                # MANUAL mode is assumed as focus value is given
                index = self.comboBoxFocusMode.findText("MANUAL")
                if index >= 0:
                    self.comboBoxFocusMode.setCurrentIndex(index)
            if "FocusMode" in self.CamConfig.keys():
                index = self.comboBoxFocusMode.findText(
                    self.CamConfig["FocusMode"])
                if index >= 0:
                    self.comboBoxFocusMode.setCurrentIndex(index)
                else:
                    print("Error: FocusMode must be AUTO or MANUAL")
                if index == 0:  # AUTO
                    self.lineEditFocus.setText("")
            if "URL_GetVideo" in self.CamConfig.keys():
                self.hasMJPGVideo = True

    def updateCameraURLs(self):
        self.CamConfigUpdated = {}
        for Key in self.CamConfig.keys():
            if "URL" in Key:
                text = self.CamConfig[Key]
                text = text.replace("IPVAL", self.CameraIP)
                text = text.replace("USERVAL", self.CameraUsername)
                text = text.replace("PASSVAL", self.CameraPassword)
                text = text.replace("WIDTHVAL", str(self.ImageSize[0]))
                text = text.replace("HEIGHTVAL", str(self.ImageSize[1]))
                self.CamConfigUpdated[Key] = text
            else:
                self.CamConfigUpdated[Key] = self.CamConfig[Key]
        self.textEditMessages.append("Updated camera configs:")
        self.textEditMessages.append("----------")
        self.textEditMessages.append(yaml.dump(self.CamConfigUpdated))

    def initCamera(self):
        self.CameraIP = self.lineEditIPCamAddress.text()
        self.CameraUsername = self.lineEditIPCamUsername.text()
        self.CameraPassword = self.lineEditIPCamPassword.text()
        ImageSizeQStr = self.comboBoxImageSize.currentText()
        self.ImageSize = [int(size) for size in str(ImageSizeQStr).split(",")]
        self.updateCameraURLs()

        self.textEditMessages.append("Initialised camera.")

        self.ZoomPos = self.getZoom()
        Zoom = self.lineEditZoom.text()
        if len(Zoom) > 0 and int(Zoom) != self.ZoomPos:
            self.setZoom(int(Zoom))
            self.horizontalSliderZoom.setValue(int(Zoom))

        self.FocusPos = self.getFocus()
        Focus = self.lineEditFocus.text()
        if len(Focus) > 0 and int(Focus) != self.FocusPos:
            self.Camera.setFocusPosition(int(Focus))

        self.updatePositions()
        self.updateFoVFromZoom(Zoom)
        self.initilisedCamera = True

    def startCamera(self):
        if not self.initilisedCamera:
            self.initCamera()
        createdCameraThread = False
        for i in range(len(self.threadPool)):
            if self.threadPool[i].Name == "CameraThread":
                createdCameraThread = True
                self.threadPool[i].run()
        if not createdCameraThread:
            # start polling images and show
            self.threadPool.append(CameraThread(self))
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('ImageSnapped()'), self.updateImage)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('ZoomFocusPos(QString)'),
                         self.updateZoomFocusInfo)
            self.threadPool[len(self.threadPool)-1].start()

    def stopCamera(self):
        for i in range(len(self.threadPool)):
            print(self.threadPool[i].Name)
            if self.threadPool[i].Name == "CameraThread":
                self.threadPool[i].stop()
                self.threadPool[i].wait()
                del self.threadPool[i]
                break

    def initPanTilt(self):
        self.PanTiltIP = self.lineEditPanTiltAddress.text()
        self.PanTiltUsername = self.lineEditPanTiltUsername.text()
        self.PanTiltPassword = self.lineEditPanTiltPassword.text()
        self.updatePanTiltURLs()
#        self.PanTilt = PanTilt(self.PanTiltIP, self.PanTiltUsername,
#                               self.PanTiltPassword)
        self.textEditMessages.append("Initialised pan-tilt.")
        PanPosStr, TiltPosStr = self.getPanTilt()
        self.PanPosDesired = float(PanPosStr)
        self.TiltPosDesired = float(TiltPosStr)
        self.horizontalSliderPan.setValue(int(self.PanPosDesired))
        self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))
        self.initilisedPanTilt = True

    def startPanTilt(self):
        if not self.initilisedPanTilt:
            self.initPanTilt()
        createdPanTiltThread = False
        for i in range(len(self.threadPool)):
            if self.threadPool[i].Name == "PanTiltThread":
                createdPanTiltThread = True
                self.threadPool[i].run()
        if not createdPanTiltThread:
            # start polling pan-tilt values and show
            self.threadPool.append(PanTiltThread(self))
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanTiltPos(QString)'),
                         self.updatePanTiltInfo)
            self.threadPool[len(self.threadPool)-1].start()

    def stopPanTilt(self):
        for i in range(len(self.threadPool)):
            print(self.threadPool[i].Name)
            if self.threadPool[i].Name == "PanTiltThread":
                self.threadPool[i].stop()
                self.threadPool[i].wait()
                del self.threadPool[i]
                break

    def updateImage(self):
        if self.Image is None:
            return
        Image = np.zeros_like(self.Image)
        Image[:, :, :] = self.Image[:, :, :]
        Image[100, :, :] = 255
        Image[:, 100, :] = 255
        Image[-100, :, :] = 255
        Image[:, -100, :] = 255
        # Convert to RGB for QImage.
        if Image is not None:
            height, width, bytesPerComponent = Image.shape
            bytesPerLine = bytesPerComponent * width
            QI = QtGui.QImage(Image.data, Image.shape[1], Image.shape[0],
                              bytesPerLine, QtGui.QImage.Format_RGB888)
            self.labelCurrentViewImage.setPixmap(QtGui.QPixmap.fromImage(QI))
            self.labelCurrentViewImage.setScaledContents(True)
            self.labelCurrentViewImage.setGeometry(
                QtCore.QRect(0, 0, Image.shape[1], Image.shape[0]))
#            self.scrollAreaWidgetContentsCurrentView.setGeometry(
#                QtCore.QRect(0, 0, Image.shape[1], Image.shape[0]))

    def updatePositions(self):
        self.labelPositions.setText(
            "P={}, T={}, Z={}, F={}".format(
                self.PanPos, self.TiltPos, self.ZoomPos, self.FocusPos))

    def updatePanTiltInfo(self, PanTiltPos):
        self.PanPos, self.TiltPos = PanTiltPos.split(",")
        self.updatePositions()

    def updateZoomFocusInfo(self, ZoomFocusPos):
        self.ZoomPos, self.FocusPos = ZoomFocusPos.split(",")
        self.updatePositions()

    def keyPressEvent(self, event):
        Key = event.key()
        print("Key = {}".format(Key))
        if Key == QtCore.Qt.Key_Escape:
            self.close()
        elif Key == QtCore.Qt.DownArrow:
            self.PanTilt.panStep("down", 10)
            event.accept()
        elif Key == QtCore.Qt.UpArrow:
            self.PanTilt.panStep("up", 10)
            event.accept()
        elif Key == QtCore.Qt.LeftArrow:
            self.PanTilt.panStep("left", 10)
            event.accept()
        elif Key == QtCore.Qt.RightArrow:
            self.PanTilt.panStep("right", 10)
            event.accept()
        elif Key == QtCore.Qt.Key_PageDown:
            self.Camera.zoomStep("out", 50)
            event.accept()
        elif Key == QtCore.Qt.Key_PageUp:
            self.Camera.zoomStep("in", 50)
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.objectSelected = self.childAt(event.pos())
            if self.objectSelected == self.labelCurrentViewImage:
                QtGui.QApplication.setOverrideCursor(
                    QtGui.QCursor(QtCore.Qt.SizeAllCursor))
            self.mouseStartPos = self.labelCurrentViewImage.mapFromGlobal(
                event.globalPos())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.mouseEndPos = self.labelCurrentViewImage.mapFromGlobal(
                event.globalPos())
            if self.objectSelected == self.labelCurrentViewImage:
                QtGui.QApplication.restoreOverrideCursor()
                dx = self.mouseEndPos.x() - self.mouseStartPos.x()
                dy = self.mouseEndPos.y() - self.mouseStartPos.y()
                self.mousePressed = False
                dp = self.HFoV*dx/self.labelCurrentViewImage.width()
                dt = self.VFoV*dy/self.labelCurrentViewImage.height()
                if dp == 0.0 and dt == 0.0:
                    # pan/tilt one degree at a time if right clicked at edge
                    x = self.mouseEndPos.x()/self.labelCurrentViewImage.width()
                    y = self.mouseEndPos.y()/self.labelCurrentViewImage.height()
                    x *= self.Image.shape[1]
                    y *= self.Image.shape[0]
                    if x <= 100:
                        dp = 1
                    elif x >= self.Image.shape[1]-100:
                        dp = -1
                    if y <= 100:
                        dt = 1
                    elif y >= self.Image.shape[0]-100:
                        dt = -1
                print("Pan/tilt camera {},{} degrees".format(dp, dt))
                self.PanPosDesired = self.PanPosDesired - dp
                self.TiltPosDesired = self.TiltPosDesired + dt
                self.setPanTilt(self.PanPosDesired, self.TiltPosDesired)


class CameraThread(QtCore.QThread):
    def __init__(self, Pano):
        QtCore.QThread.__init__(self)
        self.Pano = Pano
        self.NoImages = 0
        self.Name = "CameraThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def run(self):
        print("Started {}".format(self.Name))
        self.stopped = False
        if self.Pano.hasMJPGVideo:
            ImageSource = self.Pano.streamVideo()
        else:
            ImageSource = self.Pano.snapPhoto()
        for Image in ImageSource:
            if self.stopped:
                break
            time.sleep(0.3)  # time delay between queries
            self.emit(QtCore.SIGNAL('ImageSnapped()'))
            ZoomPos = self.Pano.getZoom()
            FocusPos = self.Pano.getFocus()
            self.emit(QtCore.SIGNAL('ZoomFocusPos(QString)'),
                      "{},{}".format(ZoomPos, FocusPos))
        print("Stopped CameraThread")
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


class PanTiltThread(QtCore.QThread):
    def __init__(self, Pano):
        QtCore.QThread.__init__(self)
        self.Pano = Pano
        self.Name = "PanTiltThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def run(self):
        print("Started {}".format(self.Name))
        self.stopped = False
        while not self.stopped:
            time.sleep(0.3)  # time delay between queries
            PanPos, TiltPos = self.Pano.getPanTilt()
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
        print("Stopped PanTiltThread")
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


class PanoThread(QtCore.QThread):
    def __init__(self, Pano):
        QtCore.QThread.__init__(self)
        self.Pano = Pano
        self.NoImages = 0
        self.Name = "PanoThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def run(self):
        print("Started {}".format(self.Name))
        self.emit(QtCore.SIGNAL('PanoThreadStarted()'))
        self.stopped = False
        ScaledHeight = int(self.Pano.PanoOverViewScale*self.Pano.Image.shape[0])
        ScaledWidth = int(self.Pano.PanoOverViewScale*self.Pano.Image.shape[1])

        def acquireImage(i, j):
            self.Pano.setPanTilt(
                self.Pano.TopLeftCorner[0] + i*self.Pano.HFoV*self.Pano.Overlap,
                self.Pano.TopLeftCorner[1] - j*self.Pano.VFoV*self.Pano.Overlap,
                Verified=True)
            time.sleep(2) # need this extra time
            while True:
                Image = self.Pano.snapPhoto().next()
                if Image is not None:
                    break
                else:
                    print("Try recapturing image")
            PanPos, TiltPos = self.Pano.getPanTilt()
            ImageResized = misc.imresize(Image,
                                         (ScaledHeight, ScaledWidth,
                                          Image.shape[2]))
            self.Pano.PanoOverView[
                ScaledHeight*j:ScaledHeight*(j+1),
                ScaledWidth*i: ScaledWidth*(i+1), :] = ImageResized
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
            self.emit(QtCore.SIGNAL('PanoImageSnapped()'))

        if str(self.Pano.comboBoxPanoScanOrder.currentText()) == "column wise":
            for i in range(self.Pano.PanoCols):
                for j in range(self.Pano.PanoRows):
                    if self.stopped:
                        break
                    acquireImage(i, j)
        else:  # row wise
            for j in range(self.Pano.PanoRows):
                for i in range(self.Pano.PanoCols):
                    if self.stopped:
                        break
                    acquireImage(i, j)

        self.emit(QtCore.SIGNAL('PanoThreadDone()'))
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True



app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
