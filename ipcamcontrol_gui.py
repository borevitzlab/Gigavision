# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong
"""

from __future__ import absolute_import, division, print_function

import sys
import time
from PyQt4 import QtGui, QtCore, uic
from functools import partial
import yaml
import os
import numpy as np
import scipy.misc as misc
import urllib
import io
from datetime import datetime

"""
IPCAMCONTROL_GUI.PY controls ip cameras with pan-tilt-zoom features.
Different cameras and pan-tilt unit need different config file in YAML format.
See ActiCamera.yml, JSystem.yml and AxisCamera.yml for examples of config files
"""

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

        # Pan-tilt tab
        self.pushButtonStartPanTilt.clicked.connect(self.startPanTilt)
        self.pushButtonStopPanTilt.clicked.connect(self.stopPanTilt)
        self.pushButtonLoadPanTiltConfigFile.clicked.connect(
            self.loadPanTiltConfig)

        # Camera tab
        self.pushButtonStartCamera.clicked.connect(self.startCamera)
        self.lineEditZoom.textChanged.connect(self.lineEditZoom2.setText)
        self.pushButtonApplyZoom.clicked.connect(self.applyZoom)
        self.pushButtonSnapPhoto.clicked.connect(self.snapPhoto)
        self.pushButtonStopCamera.clicked.connect(self.stopCamera)
        self.pushButtonLoadCameraConfigFile.clicked.connect(
            self.loadCameraConfig)

        # FoV tab
        self.horizontalSliderPan.valueChanged.connect(self.setPan)
        self.horizontalSliderTilt.valueChanged.connect(self.setTilt)
        self.horizontalSliderZoom.valueChanged.connect(self.setZoom2)
        self.pushButtonCurrentAsViewFirstCorner.clicked.connect(
            self.setCurrentAsViewFirstCorner)
        self.pushButtonCurrentAsViewSecondCorner.clicked.connect(
            self.setCurrentAsViewSecondCorner)
        self.pushButtonCalculateFoV.clicked.connect(self.calculateFoV)

        # panorama tab
        self.lineEditZoom2.textChanged.connect(self.lineEditZoom.setText)
        self.pushButtonCurrentAsPanoFirstCorner.clicked.connect(
            self.setCurrentAsFirstCorner)
        self.pushButtonGotoFirstCorner.clicked.connect(
            self.gotoFirstCorner)
        self.pushButtonCurrentAsPanoSecondCorner.clicked.connect(
            self.setCurrentAsSecondCorner)
        ScanOrders = ["Cols, right", "Cols, left", "Rows, down", "Rows, up"]
        self.comboBoxPanoScanOrder.addItems(ScanOrders)
        self.pushButtonGotoSecondCorner.clicked.connect(
            self.gotoSecondCorner)
        self.pushButtonExplainScanOrder.clicked.connect(self.explaintScanOrders)
        self.pushButtonCalculatePanoGrid.clicked.connect(self.calculatePanoGrid)
        self.pushButtonPanoRootFolder.clicked.connect(self.selectPanoRootFolder)
        self.pushButtonLoadPanoConfig.clicked.connect(
            partial(self.loadPanoConfig, None))
        self.pushButtonSavePanoConfig.clicked.connect(
            partial(self.savePanoConfig, None))
        self.pushButtonTakeOnePano.clicked.connect(self.takeOnePanorama)
        self.pushButtonLoopPanorama.clicked.connect(self.loopPanorama)
        self.pushButtonPausePanorama.clicked.connect(self.pausePanorama)
        self.pushButtonStopPanorama.clicked.connect(self.stopPanorama)

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
        self.PanoTotal = 0
        self.threadPool = []
        self.hasMJPGVideo = False
        self.PausePanorama = False
        self.StopPanorama = False
        self.PanoOverView = None
        self.CamConfigUpdated = None
        self.PanTiltConfigUpdated = None

    def applyZoom(self):
        Zoom = int(self.lineEditZoom.text())
        self.setZoom(Zoom)

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
        try:
            PanPix1, TiltPix1 = self.lineEditViewFirstCornerPixels.text().split(",")
            PanPix2, TiltPix2 = self.lineEditViewSecondCornerPixels.text().split(",")
            HFoV = abs(float(Pan1)-float(Pan2))/ \
                abs(float(PanPix1)-float(PanPix2))*self.ImageWidth
            VFoV = abs(float(Tilt1)-float(Tilt2))/ \
                abs(float(TiltPix1)-float(TiltPix2))*self.ImageHeight
        except: #4.4,2.5
            HFoV = abs(float(Pan1)-float(Pan2))
            VFoV = abs(float(Tilt1)-float(Tilt2))

        if HFoV >= VFoV and HFoV <= 2*VFoV:
            self.HFoV = HFoV
            self.VFoV = VFoV
        else:
            print("Invalid selection of field of view ({}, {})".format(
                HFoV, VFoV))
        self.lineEditFieldOfView.setText("{},{}".format(HFoV, VFoV))
        self.lineEditFieldOfView_2.setText("{},{}".format(HFoV, VFoV))

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

    def explaintScanOrders(self):
        class MyDialog(QtGui.QDialog):
            def __init__(self, parent=None):
                super(MyDialog, self).__init__(parent)

                pic = QtGui.QLabel(self)
                try:
                    pixmap = QtGui.QPixmap("ScanOrders.png")
                    pic.setGeometry(0, 0, pixmap.width(), pixmap.height())
                    pic.setPixmap(pixmap)
                except:
                    print("Failed to load ScanOrders.png")

        dialog = MyDialog(self)
        dialog.setWindowTitle('Scanning orders')
        dialog.show()

    def calculatePanoGrid(self):
        Pan0, Tilt0 = self.lineEditPanoFirstCorner.text().split(",")
        Pan1, Tilt1 = self.lineEditPanoSecondCorner.text().split(",")
        HFoV, VFoV = self.lineEditFieldOfView.text().split(",")
        self.HFoV = float(HFoV)
        self.VFoV = float(VFoV)
        self.Overlap = float(self.spinBoxPanoOverlap.value())/100
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
        self.PanoRows = int(round((TopTilt - BottomTilt)/self.VFoV/self.Overlap))
        self.PanoCols = int(round((RightPan - LeftPan)/self.HFoV/self.Overlap))
        self.PanoTotal = self.PanoRows*self.PanoCols
        self.lineEditPanoGridSize.setText("{}x{}".format(
            self.PanoRows, self.PanoCols))
        if self.PanoRows >= 0 or self.PanoCols >= 0:
            self.pushButtonTakeOnePano.setEnabled(True)
            self.pushButtonLoopPanorama.setEnabled(True)
            Scale = 2
            ImageWidthStr, ImageHeightStr = \
                self.comboBoxImageSize.currentText().split(",")
            self.ImageHeight = int(ImageHeightStr)
            self.ImageWidth = int(ImageWidthStr)
            while Scale > 0:
                ScaledHeight = int(Scale*self.ImageHeight)
                ScaledWidth = int(Scale*self.ImageWidth)
                if ScaledHeight*self.PanoRows <= 1080 and \
                        ScaledWidth*self.PanoCols <= 1920:
                    break
                Scale = Scale - 0.001
            self.PanoOverViewScale = Scale
            self.PanoOverViewHeight = ScaledHeight*self.PanoRows
            self.PanoOverViewWidth = ScaledWidth*self.PanoCols
            self.initialisePanoOverView()

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

    def selectPanoRootFolder(self):
        Folder = QtGui.QFileDialog.getExistingDirectory(self, "Select Directory")
        if len(Folder) > 0:
            self.lineEditPanoRootFolder.setText(Folder)

    def savePanoConfig(self, FileName=None):
        if FileName is None:
            FileName = QtGui.QFileDialog.getSaveFileName(
                self, "Save config", os.path.curdir, "YAML Files (*.yml)")
            if len(FileName) == 0:
                return

        PanoConfigDic = {}
        PanoConfigDic["CameraConfigFile"] = \
            str(self.lineEditCameraConfigFilename.text())
        PanoConfigDic["PanTiltConfigFile"] = \
            str(self.lineEditPanTiltConfigFilename.text())
        PanoConfigDic["FieldOfView"] = str(self.lineEditFieldOfView.text())
        PanoConfigDic["Overlap"] = self.spinBoxPanoOverlap.value()
        PanoConfigDic["Zoom"] = int(self.lineEditZoom.text())
        PanoConfigDic["1stCorner"] = str(self.lineEditPanoFirstCorner.text())
        PanoConfigDic["2ndCorner"] = str(self.lineEditPanoSecondCorner.text())
        PanoConfigDic["ScanOrder"] = str(self.comboBoxPanoScanOrder.currentText())
        PanoConfigDic["PanoGridSize"] = str(self.lineEditPanoGridSize.text())
        PanoConfigDic["PanoRootFolder"] = str(self.lineEditPanoRootFolder.text())
        PanoConfigDic["PanoLoopInterval"] = self.spinBoxPanoLoopInterval.value()
        PanoConfigDic["PanoStartHour"] = self.spinBoxStartHour.value()
        PanoConfigDic["PanoEndHour"] = self.spinBoxEndHour.value()

        with open(FileName, 'w') as YAMLFile:
            YAMLFile.write(yaml.dump(PanoConfigDic, default_flow_style=False))
            self.textEditMessages.append("Saved {}:".format(FileName))
            self.textEditMessages.append("----------")
            self.textEditMessages.append(yaml.dump(self.PanTiltConfig))

    def loadPanoConfig(self, FileName=None):
        if FileName is None:
            FileName = QtGui.QFileDialog.getOpenFileName(
                self, "Load config", os.path.curdir, "YAML Files (*.yml)")
            if len(FileName) == 0:
                return

        with open(FileName, 'r') as YAMLFile:
            PanoConfigDic = yaml.load(YAMLFile)
            self.textEditMessages.append("Loaded {}:".format(FileName))
            self.textEditMessages.append("----------")
            self.textEditMessages.append(yaml.dump(PanoConfigDic))

            if "CameraConfigFile" in PanoConfigDic.keys():
                self.lineEditCameraConfigFilename.setText(
                    PanoConfigDic["CameraConfigFile"])
                self.loadCameraConfig()
            if "PanTiltConfigFile" in PanoConfigDic.keys():
                self.lineEditPanTiltConfigFilename.setText(
                    str(PanoConfigDic["PanTiltConfigFile"]))
                self.loadPanTiltConfig()

            self.lineEditFieldOfView.setText(PanoConfigDic["FieldOfView"])
            self.spinBoxPanoOverlap.setValue(PanoConfigDic["Overlap"])
            self.lineEditZoom.setText(str(PanoConfigDic["Zoom"]))
            self.lineEditPanoFirstCorner.setText(PanoConfigDic["1stCorner"])
            self.lineEditPanoSecondCorner.setText(PanoConfigDic["2ndCorner"])
            Index = self.comboBoxPanoScanOrder.findText(PanoConfigDic["ScanOrder"])
            if Index >= 0:
                self.comboBoxPanoScanOrder.setCurrentIndex(Index)
            else:
                print("Error when applying ScanOrder = {}".format(
                    PanoConfigDic["ScanOrder"]))
            self.lineEditPanoGridSize.setText(PanoConfigDic["PanoGridSize"])
            self.lineEditPanoRootFolder.setText(PanoConfigDic["PanoRootFolder"])
            self.spinBoxPanoLoopInterval.setValue(PanoConfigDic["PanoLoopInterval"])
            self.spinBoxStartHour.setValue(PanoConfigDic["PanoStartHour"])
            self.spinBoxEndHour.setValue(PanoConfigDic["PanoEndHour"])

    def takePanorama(self, IsOneTime=True):
        if not self.initilisedCamera:
            self.initCamera()
        if not self.initilisedPanTilt:
            self.initPanTilt()

        self.calculatePanoGrid()  # make sure everything is up-to-date
        self.PanoImageNo = 0
        if not os.path.exists(str(self.lineEditPanoRootFolder.text())):
            self.selectPanoRootFolder()

        self.PausePanorama = False
        self.StopPanorama = False

        LoopInterval = 60*int(self.spinBoxPanoLoopInterval.text())
        StartHour = self.spinBoxStartHour.value()
        EndHour = self.spinBoxEndHour.value()

        createdPanoThread = False
        for i in range(len(self.threadPool)):
            if self.threadPool[i].Name == "PanoThread":
                createdPanoThread = True
                if not self.threadPool[i].isRunning():
                    self.threadPool[i].run()
        if not createdPanoThread:
            self.threadPool.append(PanoThread(self, IsOneTime, LoopInterval,
                                              StartHour, EndHour))
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanoImageSnapped()'),
                         self.updatePanoImage)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanTiltPos(QString)'),
                         self.updatePanTiltInfo)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanoThreadStarted()'),
                         self.deactivateLiveView)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanoThreadDone()'),
                         self.activateLiveView)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('OnePanoStarted()'),
                         self.initialisePanoOverView)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('OnePanoDone()'),
                         self.savePanoOverView)
            self.threadPool[len(self.threadPool)-1].start()

    def takeOnePanorama(self):
        self.takePanorama(IsOneTime=True)

    def loopPanorama(self):
        self.takePanorama(IsOneTime=False)

    def pausePanorama(self):
        self.PausePanorama = not(self.PausePanorama)

        if self.PausePanorama:
            self.pushButtonPausePanorama.setText("Resume")
        else:
            self.pushButtonPausePanorama.setText("Pause")

    def stopPanorama(self):
        self.StopPanorama = True

    def activateLiveView(self):
        self.startPanTilt()
        self.startCamera()
        self.pushButtonTakeOnePano.setEnabled(True)
        self.pushButtonLoopPanorama.setEnabled(True)

        # update current pan-tilt position
        self.horizontalSliderPan.setValue(int(self.PanPosDesired))
        self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))

    def deactivateLiveView(self):
        self.stopPanTilt()
        self.stopCamera()
        self.pushButtonTakeOnePano.setEnabled(False)
        self.pushButtonLoopPanorama.setEnabled(False)

#        for i in range(len(self.threadPool)):
#            print(self.threadPool[i].Name)
#            if self.threadPool[i].Name == "PanoThread":
##                self.threadPool[i].stop()
#                self.threadPool[i].wait()
#                del self.threadPool[i]
#                break

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

    def initialisePanoOverView(self):
        ScaledHeight = int(self.PanoOverViewScale*self.ImageHeight)
        ScaledWidth = int(self.PanoOverViewScale*self.ImageWidth)
        self.PanoOverView = np.zeros((self.PanoOverViewHeight,
                                      self.PanoOverViewWidth, 3),
                                     dtype=np.uint8)
        # add lines shows rows and columns
        for i in range(self.PanoCols):
            self.PanoOverView[:, ScaledWidth*i: ScaledWidth*i+1, :] = 255
        for j in range(self.PanoRows):
            self.PanoOverView[ScaledHeight*j:ScaledHeight*j+1, :, :] = 255
        try:
            # try saving panorama config
            DataFolder = os.path.join(self.PanoFolder, "_data")
            if not os.path.exists(DataFolder):
                os.mkdir(DataFolder)
            self.savePanoConfig(os.path.join(DataFolder, "PanoConfig.yml"))
        except:
            print("Cannot save PanoConfig.yml")

    def savePanoOverView(self):
        try:
            # try saving PanoOverView
            DataFolder = os.path.join(self.PanoFolder, "_data")
            if not os.path.exists(DataFolder):
                os.mkdir(DataFolder)
            Prefix = "PanoOverView"
            Now = datetime.now()
            FileName = os.path.join(DataFolder,
                                    "{}_{}_00_00.jpg".format(
                                        Prefix,
                                        Now.strftime("%Y_%m_%d_%H_%M")))
            misc.imsave(FileName, self.PanoOverView)
        except:
            print("Cannot save PanoOverView image")

    def setPan(self, Pan):
        self.setPanTilt(Pan, self.TiltPosDesired)

    def setTilt(self, Tilt):
        self.setPanTilt(self.PanPosDesired, Tilt)

    def setZoom2(self, Zoom):
        if self.CamConfigUpdated is not None:
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

    def setPanTilt(self, Pan, Tilt):
        if "PanTiltScale" in self.PanTiltConfigUpdated.keys():
            # this is for Acti camera
            PanTiltScale = self.PanTiltConfigUpdated["PanTiltScale"]
            PANVAL = str(int(float(Pan)*PanTiltScale))
            TILTVAL = str(int(float(Tilt)*PanTiltScale))
        else:
            PANVAL = str(float(Pan))
            TILTVAL = str(float(Tilt))
        URL = self.PanTiltConfigUpdated["URL_SetPanTilt"].replace("PANVAL",
                                                                  PANVAL)
        URL = URL.replace("TILTVAL", TILTVAL)
        executeURL(URL)

        if self.PanTiltConfigUpdated["Type"] == "ServoMotors":
            NoLoops = 0
            # loop until within 1 degree
            while True:
                PanCur, TiltCur = self.getPanTilt()
                PanDiff = int(abs(float(PanCur) - float(Pan)))
                TiltDiff = int(abs(float(TiltCur) - float(Tilt)))
                if PanDiff <= 1 and TiltDiff <= 1:
                    break
                time.sleep(0.2)
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
                time.sleep(0.2)
                NoLoops += 1
                if NoLoops > 50:
                    break
            self.PanPos, self.TiltPos = PanPos, TiltPos
            # TODO: check if this is necessary
            time.sleep(2)  # Acti camera need this extra time
        else:
            PanCur, TiltCur = self.getPanTilt()
            self.PanPos, self.TiltPos = PanCur, TiltCur
            time.sleep(0.2)  # Acti camera need this extra time

        self.PanPosDesired = float(Pan)
        self.TiltPosDesired = float(Tilt)
        self.updatePositions()

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
                text = text.replace("WIDTHVAL", str(self.ImageWidth))
                text = text.replace("HEIGHTVAL", str(self.ImageHeight))
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
        ImageWidthStr, ImageHeightStr = \
            self.comboBoxImageSize.currentText().split(",")
        self.ImageHeight = int(ImageHeightStr)
        self.ImageWidth = int(ImageWidthStr)
        self.updateCameraURLs()
        if "URL_Login" in self.CamConfigUpdated.keys():
            URL_Str = self.CamConfigUpdated["URL_Login"]
            executeURL(URL_Str)

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

        self.Image = self.snapPhoto().next()
        self.updateImage()
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
                if not self.threadPool[i].isRunning():
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
        if "URL_Login" in self.PanTiltConfigUpdated.keys():
            URL_Str = self.PanTiltConfigUpdated["URL_Login"]
            executeURL(URL_Str)

        PanPosStr, TiltPosStr = self.getPanTilt()
        self.setPanTilt(float(PanPosStr), float(TiltPosStr))
        time.sleep(1)  # make sure it wakes up
        self.PanPosDesired = float(PanPosStr)
        self.TiltPosDesired = float(TiltPosStr)
        self.horizontalSliderPan.setValue(int(self.PanPosDesired))
        self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))
        self.initilisedPanTilt = True
        self.textEditMessages.append("Initialised pan-tilt.")

    def startPanTilt(self):
        if not self.initilisedPanTilt:
            self.initPanTilt()
        createdPanTiltThread = False
        for i in range(len(self.threadPool)):
            if self.threadPool[i].Name == "PanTiltThread":
                createdPanTiltThread = True
                if not self.threadPool[i].isRunning():
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

    def updatePositions(self):
        self.labelPositions.setText("P={:.2f}, T={:.2f}, Z={}, F={}".format(
            self.PanPos, self.TiltPos, self.ZoomPos, self.FocusPos))
        if self.PanoImageNo > 0:
            self.labelCurrentLiveView.setText(
                "Current image of {}/{} ".format(self.PanoImageNo,
                                                           self.PanoTotal))
        else:
            self.labelCurrentLiveView.setText("Current live view")

    def updatePanTiltInfo(self, PanTiltPos):
        self.PanPos, self.TiltPos = PanTiltPos.split(",")
        self.updatePositions()

    def updateZoomFocusInfo(self, ZoomFocusPos):
        self.ZoomPos, self.FocusPos = ZoomFocusPos.split(",")
        self.updatePositions()

    def keyPressEvent(self, event):
        Key = event.key()
#        print("Key = {}".format(Key))
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
        modifiers = QtGui.QApplication.keyboardModifiers()
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
                        dp = float(self.lineEditPanStep.text())
                    elif x >= self.Image.shape[1]-100:
                        dp = -float(self.lineEditPanStep.text())
                    if y <= 100:
                        dt = float(self.lineEditTiltStep.text())
                    elif y >= self.Image.shape[0]-100:
                        dt = -float(self.lineEditTiltStep.text())
                print("Pan/tilt camera {},{} degrees".format(dp, dt))
                self.PanPosDesired = self.PanPosDesired - dp
                self.TiltPosDesired = self.TiltPosDesired + dt
                self.setPanTilt(self.PanPosDesired, self.TiltPosDesired)
        elif event.button() == QtCore.Qt.MidButton:
            self.mousePos = self.labelCurrentViewImage.mapFromGlobal(
                event.globalPos())
            size = self.labelCurrentViewImage.size()
            if modifiers == QtCore.Qt.ShiftModifier:
                self.lineEditViewFirstCornerPixels.setText("{},{}".format(
                    self.mousePos.x()/size.width()*self.ImageWidth,
                    self.mousePos.y()/size.height()*self.ImageHeight))
            elif modifiers == QtCore.Qt.ControlModifier:
                self.lineEditViewSecondCornerPixels.setText("{},{}".format(
                    self.mousePos.x()/size.width()*self.ImageWidth,
                    self.mousePos.y()/size.height()*self.ImageHeight))


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
            time.sleep(0.5)  # time delay between queries
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
            time.sleep(0.5)  # time delay between queries
            PanPos, TiltPos = self.Pano.getPanTilt()
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
        print("Stopped PanTiltThread")
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


class PanoThread(QtCore.QThread):
    def __init__(self, Pano, IsOneTime=True, LoopInterval=60, StartHour=0, EndHour=0):
        QtCore.QThread.__init__(self)
        self.Pano = Pano
        self.IsOneTime = IsOneTime
        self.LoopInterval = LoopInterval
        self.StartHour = StartHour
        self.EndHour = EndHour
        self.NoImages = 0
        self.Name = "PanoThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def _moveAndSnap(self, iCol, jRow, DelaySeconds=0.1):
        self.Pano.setPanTilt(
            self.Pano.TopLeftCorner[0] + iCol*self.Pano.HFoV*self.Pano.Overlap,
            self.Pano.TopLeftCorner[1] - jRow*self.Pano.VFoV*self.Pano.Overlap)
        PanPos, TiltPos = self.Pano.getPanTilt()
        if DelaySeconds != 0:
            time.sleep(DelaySeconds)

        while True:
            Image = self.Pano.snapPhoto().next()
            if Image is not None:
                break
            else:
                print("Try recapturing image")
        ScaledHeight = int(self.Pano.PanoOverViewScale*self.Pano.ImageHeight)
        ScaledWidth = int(self.Pano.PanoOverViewScale*self.Pano.ImageWidth)
        ImageResized = misc.imresize(Image,
                                     (ScaledHeight, ScaledWidth,
                                      Image.shape[2]))
        self.Pano.PanoOverView[
            ScaledHeight*jRow:ScaledHeight*(jRow+1),
            ScaledWidth*iCol:ScaledWidth*(iCol+1), :] = ImageResized
        self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                  "{},{}".format(PanPos, TiltPos))
        self.emit(QtCore.SIGNAL('PanoImageSnapped()'))

    def run(self):
        print("Started {}".format(self.Name))
        self.emit(QtCore.SIGNAL('PanoThreadStarted()'))
        self.stopped = False

        while not self.Pano.StopPanorama:
            while self.Pano.PausePanorama:
                time.sleep(5)
            Start = datetime.now()
            IgnoreHourRange = (self.StartHour >= self.EndHour)
            WithinHourRange = (Start.hour >= self.StartHour and \
                               Start.hour < self.EndHour)
            if self.IsOneTime or IgnoreHourRange or WithinHourRange:
                PanoRootFolder = str(self.Pano.lineEditPanoRootFolder.text())
                self.Pano.PanoFolder = os.path.join(PanoRootFolder,
                                                    Start.strftime("%Y"),
                                                    Start.strftime("%Y_%m"),
                                                    Start.strftime("%Y_%m_%d"),
                                                    Start.strftime("%Y_%m_%d_%H"))
                if not os.path.exists(self.Pano.PanoFolder):
                    os.makedirs(self.Pano.PanoFolder)

                self.emit(QtCore.SIGNAL('OnePanoStarted()'))
                self.Pano.PanoImageNo = 0
                ScanOrder = str(self.Pano.comboBoxPanoScanOrder.currentText())
                DelaySeconds = 1  # delay to reduce blurring
                if ScanOrder == "Cols, right":
                    for i in range(self.Pano.PanoCols):
                        for j in range(self.Pano.PanoRows):
                            while self.Pano.PausePanorama:
                                time.sleep(5)
                            if self.stopped or self.Pano.StopPanorama:
                                break
                            if j == 0:
                                self._moveAndSnap(i, j, DelaySeconds)
                            else:
                                self._moveAndSnap(i, j)
                elif ScanOrder == "Cols, left":
                    for i in range(self.Pano.PanoCols-1, -1, -1):
                        for j in range(self.Pano.PanoRows):
                            while self.Pano.PausePanorama:
                                time.sleep(5)
                            if self.stopped or self.Pano.StopPanorama:
                                break
                            if j == 0:
                                self._moveAndSnap(i, j, DelaySeconds)
                            else:
                                self._moveAndSnap(i, j)
                elif ScanOrder == "Rows, down":
                    for j in range(self.Pano.PanoRows):
                        for i in range(self.Pano.PanoCols):
                            while self.Pano.PausePanorama:
                                time.sleep(5)
                            if self.stopped or self.Pano.StopPanorama:
                                break
                            if i == 0:
                                self._moveAndSnap(i, j, DelaySeconds)
                            else:
                                self._moveAndSnap(i, j)
                else:  # ScanOrder == "Rows, up"
                    for j in range(self.Pano.PanoRows-1, -1, -1):
                        for i in range(self.Pano.PanoCols):
                            while self.Pano.PausePanorama:
                                time.sleep(5)
                            if self.stopped or self.Pano.StopPanorama:
                                break
                            if i == 0:
                                self._moveAndSnap(i, j, DelaySeconds)
                            else:
                                self._moveAndSnap(i, j)
                self.Pano.PanoImageNo = 0
                self.emit(QtCore.SIGNAL('OnePanoDone()'))

            elif not IgnoreHourRange and not WithinHourRange:
                print("Outside hour range ({} to {})".format(self.StartHour,
                                                             self.EndHour))

            if self.IsOneTime:
                break
            else:
                End = datetime.now()
                Elapse = End - Start
                ElapseSeconds = Elapse.days*86400 + Elapse.seconds
                if self.LoopInterval > ElapseSeconds:
                    WaitTime = self.LoopInterval - ElapseSeconds
                else:
                    print("Warning: it takes more time than loop interval")
                    WaitTime = 0
                print("It's {}.".format(End.strftime("%H:%M"))),
                print("Wait for {} minutes before start.".format(WaitTime/60))
                time.sleep(WaitTime)

        self.emit(QtCore.SIGNAL('PanoThreadDone()'))
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.setWindowTitle("Panorama control using IP Pan-Tilt-Zoom camera")
myWindow.show()
app.exec_()
