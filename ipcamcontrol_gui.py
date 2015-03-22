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
import csv
import logging
import disk_usage
import subprocess
import glob

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
                MyWindowClass.printError("Unhandled case {}". format(Str))
        if len(Vals) == 1:
            return Vals[0]
#        print(Vals)
        return Vals

CWD = os.path.dirname(os.path.realpath(__file__))
form_class = uic.loadUiType(os.path.join(CWD, "controller2.ui"))[0]


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        # Pan-tilt tab
        self.pushButtonStartPanTilt.clicked.connect(self.startPanTilt)
        self.pushButtonStopPanTilt.clicked.connect(self.stopPanTilt)
        self.pushButtonLoadPanTiltConfigFile.clicked.connect(
            self.loadPanTiltConfig)

        self.lineEditPanTiltAddress.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanTiltUsername.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanTiltPassword.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanTiltConfigFilename.textChanged.connect(self.PanoConfigUpdated)

        # Camera tab
        self.pushButtonStartCamera.clicked.connect(self.startCamera)
        self.lineEditZoom.textChanged.connect(self.lineEditZoom2.setText)
        self.pushButtonApplyZoom.clicked.connect(self.applyZoom)
        self.comboBoxFocusMode.currentIndexChanged.connect(self.setFocusMode)
        self.pushButtonSnapPhoto.clicked.connect(self.snapPhoto)
        self.pushButtonStopCamera.clicked.connect(self.stopCamera)
        self.pushButtonLoadCameraConfigFile.clicked.connect(
            self.loadCameraConfig)

        self.lineEditIPCamAddress.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditIPCamUsername.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditIPCamPassword.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditCameraConfigFilename.textChanged.connect(self.PanoConfigUpdated)
        self.comboBoxImageSize.currentIndexChanged.connect(self.PanoConfigUpdated)
        self.lineEditZoom.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditFocus.textChanged.connect(self.PanoConfigUpdated)
#        self.comboBoxFocusMode.currentIndexChanged.connect(self.PanoConfigUpdated)

        # FoV tab
        self.horizontalSliderPan.valueChanged.connect(self.setPan)
        self.horizontalSliderTilt.valueChanged.connect(self.setTilt)
        self.horizontalSliderZoom.valueChanged.connect(self.setZoom2)
        self.pushButtonCurrentAsViewFirstCorner.clicked.connect(
            self.setCurrentAsViewFirstCorner)
        self.pushButtonCurrentAsViewSecondCorner.clicked.connect(
            self.setCurrentAsViewSecondCorner)
        self.pushButtonCalculateFoV.clicked.connect(self.calculateFoV)

        self.lineEditFieldOfView_2.textChanged.connect(self.PanoConfigUpdated)

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
        self.pushButtonRunConfigInFileName.clicked.connect(self.selectRunConfig)
        self.checkBoxUserRunConfigIn.stateChanged.connect(self.useRunConfig)
        self.pushButtonPanoMainFolder.clicked.connect(self.selectPanoMainFolder)
        self.lineEditPanoMainFolder.textChanged.connect(
            self.lineEditPanoMainFolder2.setText)
        self.pushButtonLoadPanoConfig.clicked.connect(
            partial(self.loadPanoConfig, None))
        self.pushButtonSavePanoConfig.clicked.connect(
            partial(self.savePanoConfig, None))
        self.pushButtonTakeOnePano.clicked.connect(self.takeOnePanorama)
        self.pushButtonLoopPanorama.clicked.connect(self.loopPanorama)
        self.pushButtonPausePanorama.clicked.connect(self.pausePanorama)
        self.pushButtonStopPanorama.clicked.connect(self.stopPanorama)

        self.lineEditFieldOfView.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditZoom2.textChanged.connect(self.PanoConfigUpdated)
        self.spinBoxPanoOverlap.valueChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoFirstCorner.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoSecondCorner.textChanged.connect(self.PanoConfigUpdated)
        self.comboBoxPanoScanOrder.currentIndexChanged.connect(self.PanoConfigUpdated)
        self.lineEditRunConfigInFileName.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoMainFolder.textChanged.connect(self.PanoConfigUpdated)
        self.spinBoxPanoLoopInterval.valueChanged.connect(self.PanoConfigUpdated)
        self.spinBoxStartHour.valueChanged.connect(self.PanoConfigUpdated)
        self.spinBoxEndHour.valueChanged.connect(self.PanoConfigUpdated)

        # storage tab
        self.pushButtonMapRemoteFolder.clicked.connect(self.mapRemoteFolder)
        self.pushButtonPanoMainFolder2.clicked.connect(self.selectPanoMainFolder)
        self.lineEditPanoMainFolder2.textChanged.connect(
            self.lineEditPanoMainFolder.setText)
        self.pushButtonPanoMainFolderFallBack.clicked.connect(
            self.selectFallbackFolder)

        self.lineEditStorageAddress.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditStorageUsername.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditStoragePassword.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoRemoteFolder.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoLocalFolder.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditCameraName.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoMainFolder2.textChanged.connect(self.PanoConfigUpdated)
        self.lineEditPanoMainFolderFallBack.textChanged.connect(self.PanoConfigUpdated)
        self.spinBoxMaxPanoNoImages.valueChanged.connect(self.PanoConfigUpdated)
        self.lineEditMinFreeDiskSpace.textChanged.connect(self.PanoConfigUpdated)

        # initial values
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
        self.RunConfig = None
        self.PanoStartMin = 60
        self.PanoWaitMin = 15
        self.PanoConfigChanged = False

        # create logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def PanoConfigUpdated(self):
        self.PanoConfigChanged = True

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
        except:
            HFoV = abs(float(Pan1)-float(Pan2))
            VFoV = abs(float(Tilt1)-float(Tilt2))

        if HFoV >= VFoV and HFoV <= 2*VFoV:
            self.HFoV = HFoV
            self.VFoV = VFoV
        else:
            self.printMessage("Invalid selection of field of view ({}, {})".format(
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
                    self.printError("Failed to load ScanOrders.png")

        dialog = MyDialog(self)
        dialog.setWindowTitle('Scanning orders')
        dialog.show()

    def selectRunConfig(self):
        FileName = QtGui.QFileDialog.getOpenFileName(
            self, "Open run config", os.path.curdir, "CVS Files (*.cvs)")
        if len(FileName) == 0:
            return
        else:
            self.lineEditRunConfigInFileName.setText(FileName)
            self.checkBoxUserRunConfigIn.setCheckState(QtCore.Qt.Checked)

    def useRunConfig(self):
        if self.checkBoxUserRunConfigIn.checkState() == QtCore.Qt.Checked:
            with open(str(self.lineEditRunConfigInFileName.text())) as File:
                csvread = csv.DictReader(File)
                self.RunConfig = {"Index": [], "Col": [], "Row": [],
                                  "PanDeg": [], "TiltDeg": [],
                                  "Zoom": [], "Focus": []}
                for row in csvread:
                    self.RunConfig["Index"].append(int(row["Index"]))
                    self.RunConfig["Col"].append(int(row["Col"]))
                    self.RunConfig["Row"].append(int(row["Row"]))
                    self.RunConfig["PanDeg"].append(float(row["PanDeg"]))
                    self.RunConfig["TiltDeg"].append(float(row["TiltDeg"]))
                    self.RunConfig["Zoom"].append(int(row["Zoom"]))
                    self.RunConfig["Focus"].append(int(float(row["Focus"])))
                index = self.comboBoxFocusMode.findText("MANUAL")
                if index >= 0:
                    self.comboBoxFocusMode.setCurrentIndex(index)
                    self.setFocusMode()

        else:
            self.RunConfig = None

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
        self.PanoRows = int(round((TopTilt - BottomTilt)/self.VFoV/(1.0-self.Overlap)))
        self.PanoCols = int(round((RightPan - LeftPan)/self.HFoV/(1.0-self.Overlap)))
        self.PanoTotal = self.PanoRows*self.PanoCols

        # Gigapan Sticher only works with 2000 images max
        if self.PanoTotal > self.spinBoxMaxPanoNoImages.value():
            QtGui.QMessageBox.about(
                self, "Warning",
                "Total number of image {} is more than {}".format(
                    self.PanoTotal,
                    self.spinBoxMaxPanoNoImages.value()))

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

    def mapRemoteFolder(self):
        if os.system == "Windows":
            self.printError("This mapping needs to be done by win-sshfs")
            return False

        HostName = str(self.lineEditStorageAddress.text())
        UserName = str(self.lineEditStorageUsername.text())
        Password = str(self.lineEditStoragePassword.text())
        RemoteFolder = str(self.lineEditPanoRemoteFolder.text())
        LocalFolder = str(self.lineEditPanoLocalFolder.text())
        if len(glob.glob(os.path.join(LocalFolder, "*"))) > 0:
            self.printMessage("Remote folder seemed to be already mapped")
            return True
        elif len(HostName) > 0 and len(UserName) > 0 and \
                len(RemoteFolder) > 0 and len(LocalFolder) > 0:
            Command = ["sshfs {}@{}:{} {}".format(UserName, HostName,
                       RemoteFolder, LocalFolder)]
            self.printMessage('Command = ' + ' '.join(Command))
            if len(Password) > 0:
                import pexpect
                try:
                    child = pexpect.spawn(Command[0])
                    ExpectedString = "{}@{}'s password:".format(UserName, HostName)
                    self.printMessage('ExpectedString = ' + ExpectedString)
                    child.expect(ExpectedString)
                    time.sleep(0.1)
                    child.sendline(Password)
                    time.sleep(10)
                    child.expect (pexpect.EOF)
                    self.printMessage("Successfully mapped network drive")
                    return True
                except:
                    self.printError("Failed to map network drive")
                    return False
            else:
                process = subprocess.Popen(Command, shell=True)
                sts = os.waitpid(process.pid, 0)
                if sts[1] != 0:
                    self.printError("Cannot map remote folder")
                    return False
                else:
                    self.printMessage("Successfully mapped network drive")
                    return True

    def selectPanoMainFolder(self):
        PanoMainFolder = str(self.lineEditPanoMainFolder.text())
        PanoLocalFolder = str(self.lineEditPanoLocalFolder.text())
        PanoMainFolder.replace("$LOCAL_FOLDER", PanoLocalFolder)
        Folder = QtGui.QFileDialog.getExistingDirectory(
            self, "Select Directory", PanoMainFolder)
        if len(Folder) > 0:
            self.lineEditPanoMainFolder.setText(Folder)
            return True
        else:
            return False

    def selectFallbackFolder(self):
        PanoFallbackFolder = self.lineEditPanoMainFolderFallBack.text()
        Folder = QtGui.QFileDialog.getExistingDirectory(self,
                                                        "Select Directory",
                                                        PanoFallbackFolder)
        if len(Folder) > 0:
            self.lineEditPanoMainFolderFallBack.setText(Folder)

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
        if self.checkBoxUserRunConfigIn.checkState() == QtCore.Qt.Checked:
            PanoConfigDic["RunConfigInFile"] = \
                str(self.lineEditRunConfigInFileName.text())
        PanoConfigDic["FieldOfView"] = str(self.lineEditFieldOfView.text())
        PanoConfigDic["Overlap"] = self.spinBoxPanoOverlap.value()
        PanoConfigDic["Zoom"] = int(self.lineEditZoom.text())
        PanoConfigDic["Focus"] = int(self.lineEditZoom.text())
        PanoConfigDic["1stCorner"] = str(self.lineEditPanoFirstCorner.text())
        PanoConfigDic["2ndCorner"] = str(self.lineEditPanoSecondCorner.text())
        PanoConfigDic["UseFocusAtCenter"] = \
            self.checkBoxUseFocusAtCenter.checkState() == QtCore.Qt.Checked
        PanoConfigDic["ScanOrder"] = str(self.comboBoxPanoScanOrder.currentText())
        PanoConfigDic["PanoGridSize"] = str(self.lineEditPanoGridSize.text())
        PanoConfigDic["PanoMainFolder"] = str(self.lineEditPanoMainFolder.text())
        PanoConfigDic["PanoLoopInterval"] = self.spinBoxPanoLoopInterval.value()
        PanoConfigDic["PanoStartHour"] = self.spinBoxStartHour.value()
        PanoConfigDic["PanoEndHour"] = self.spinBoxEndHour.value()
        PanoConfigDic["PanoStartMin"] = self.PanoStartMin
        PanoConfigDic["PanoWaitMin"] = self.PanoWaitMin

        PanoConfigDic["RemoteStorageAddress"] = str(self.lineEditStorageAddress.text())
        PanoConfigDic["RemoteStorageUsername"] = str(self.lineEditStorageUsername.text())
        PanoConfigDic["RemoteStoragePassword"] = str(self.lineEditStoragePassword.text())
        PanoConfigDic["RemoteFolder"] = str(self.lineEditPanoRemoteFolder.text())
        PanoConfigDic["LocalFolder"] = str(self.lineEditPanoLocalFolder.text())
        PanoConfigDic["CameraName"] = str(self.lineEditCameraName.text())
        PanoConfigDic["PanoFallbackFolder"] = str(self.lineEditPanoMainFolderFallBack.text())
        PanoConfigDic["MaxPanoNoImages"] = self.spinBoxMaxPanoNoImages.value()
        PanoConfigDic["MinFreeSpace"] = int(self.lineEditMinFreeDiskSpace.text())

        with open(FileName, 'w') as YAMLFile:
            YAMLFile.write(yaml.dump(PanoConfigDic, default_flow_style=False))
            Message = "Saved {}:\n".format(FileName) + \
                      "----------\n" + \
                      yaml.dump(PanoConfigDic, default_flow_style=False)
            self.printMessage(Message)

    def loadPanoConfig(self, FileName=None):
        if FileName is None:
            FileName = QtGui.QFileDialog.getOpenFileName(
                self, "Load config", os.path.curdir, "YAML Files (*.yml)")
            if len(FileName) == 0:
                return
        self.PanoConfigFileName = FileName
        with open(FileName, 'r') as YAMLFile:
            PanoConfigDic = yaml.load(YAMLFile)
            Message = "Loaded {}:\n".format(FileName) + \
                      "----------\n" + \
                      yaml.dump(PanoConfigDic)
            self.printMessage(Message)

            if "CameraConfigFile" in PanoConfigDic.keys():
                self.lineEditCameraConfigFilename.setText(
                    PanoConfigDic["CameraConfigFile"])
                self.loadCameraConfig()
            if "PanTiltConfigFile" in PanoConfigDic.keys():
                self.lineEditPanTiltConfigFilename.setText(
                    str(PanoConfigDic["PanTiltConfigFile"]))
                self.loadPanTiltConfig()
            if "RunConfigInFile" in PanoConfigDic.keys():
                self.lineEditRunConfigInFileName.setText(
                    PanoConfigDic["RunConfigInFile"])

            self.lineEditFieldOfView.setText(PanoConfigDic["FieldOfView"])
            self.spinBoxPanoOverlap.setValue(PanoConfigDic["Overlap"])
            self.lineEditZoom.setText(str(PanoConfigDic["Zoom"]))
            self.lineEditPanoFirstCorner.setText(PanoConfigDic["1stCorner"])
            self.lineEditPanoSecondCorner.setText(PanoConfigDic["2ndCorner"])
            if PanoConfigDic["UseFocusAtCenter"]:
                self.checkBoxUseFocusAtCenter.setCheckState(QtCore.Qt.Checked)
            else:
                self.checkBoxUseFocusAtCenter.setCheckState(QtCore.Qt.Unchecked)
            Index = self.comboBoxPanoScanOrder.findText(PanoConfigDic["ScanOrder"])
            if Index >= 0:
                self.comboBoxPanoScanOrder.setCurrentIndex(Index)
            else:
                self.printError("Error when applying ScanOrder = {}".format(
                    PanoConfigDic["ScanOrder"]))
            self.lineEditPanoGridSize.setText(PanoConfigDic["PanoGridSize"])
            self.lineEditPanoMainFolder.setText(PanoConfigDic["PanoMainFolder"])
            self.spinBoxPanoLoopInterval.setValue(PanoConfigDic["PanoLoopInterval"])
            self.spinBoxStartHour.setValue(PanoConfigDic["PanoStartHour"])
            self.spinBoxEndHour.setValue(PanoConfigDic["PanoEndHour"])
            self.PanoStartMin = PanoConfigDic["PanoStartMin"]
            self.PanoWaitMin = PanoConfigDic["PanoWaitMin"]
            self.lineEditStorageAddress.setText(
                PanoConfigDic["RemoteStorageAddress"])
            self.lineEditStorageUsername.setText(
                PanoConfigDic["RemoteStorageUsername"])
            self.lineEditStoragePassword.setText(
                PanoConfigDic["RemoteStoragePassword"])
            self.lineEditCameraName.setText(PanoConfigDic["CameraName"])
            self.lineEditPanoRemoteFolder.setText(PanoConfigDic["RemoteFolder"])
            self.lineEditPanoLocalFolder.setText(PanoConfigDic["LocalFolder"])
            self.lineEditPanoMainFolderFallBack.setText(
                PanoConfigDic["PanoFallbackFolder"])
            self.spinBoxMaxPanoNoImages.setValue(
                PanoConfigDic["MaxPanoNoImages"])
            self.lineEditMinFreeDiskSpace.setText(
                str(PanoConfigDic["MinFreeSpace"]))

            self.calculatePanoGrid()
            self.startPanTilt()
            self.startCamera()
            self.PanoConfigChanged = False

    def takePanorama(self, IsOneTime=True):
        if not self.initilisedCamera:
            self.initCamera()
        if not self.initilisedPanTilt:
            self.initPanTilt()

        self.calculatePanoGrid()  # make sure everything is up-to-date
        self.PanoImageNo = 0

        # select root folder
        PanoMainFolder = str(self.lineEditPanoMainFolder.text())
        PanoLocalFolder = str(self.lineEditPanoLocalFolder.text())
        PanoMainFolder = PanoMainFolder.replace(
            "$LOCAL_FOLDER", PanoLocalFolder)
        PanoFallBackFolder = \
            str(self.lineEditPanoMainFolderFallBack.text())
        if os.path.exists(PanoMainFolder):
            self.RootFolder = PanoMainFolder
        elif os.path.exists(PanoFallBackFolder):
            self.RootFolder = PanoFallBackFolder
            self.printMessage("Use fallback folder")
        else:
            QtGui.QMessageBox.information(
                self, "Warning",
                "Failed to open:\n{}\nor:\n{}".format(PanoMainFolder,
                                                      PanoFallBackFolder),
                QtGui.QMessageBox.Ok)
            return

        if self.checkBoxUseFocusAtCenter.checkState() == QtCore.Qt.Checked:
            index = self.comboBoxFocusMode.findText("AUTO")
            if index >= 0:
                self.comboBoxFocusMode.setCurrentIndex(index)
                self.setFocusMode()  # make sure this change applies
            PANVAL0, TILTVAL0 = self.lineEditPanoFirstCorner.text().split(",")
            PANVAL1, TILTVAL1 = self.lineEditPanoSecondCorner.text().split(",")
            self.setPanTilt(0.5*(float(PANVAL0) + float(PANVAL1)),
                            0.5*(float(TILTVAL0) + float(TILTVAL1)))
            self.snapPhoto()
            self.updateImage()
            time.sleep(2)
            self.snapPhoto()
            self.updateImage()
            index = self.comboBoxFocusMode.findText("MANUAL")
            if index >= 0:
                self.comboBoxFocusMode.setCurrentIndex(index)
                self.setFocusMode()  # make sure this change applies
            time.sleep(2)
            self.snapPhoto()
            self.updateImage()

        self.CameraName = str(self.lineEditCameraName.text())
        self.PausePanorama = False
        self.StopPanorama = False

        LoopIntervalMinute = int(self.spinBoxPanoLoopInterval.text())
        StartHour = self.spinBoxStartHour.value()
        EndHour = self.spinBoxEndHour.value()

        createdPanoThread = False
        for i in range(len(self.threadPool)):
            if self.threadPool[i].Name == "PanoThread":
                createdPanoThread = True
                if not self.threadPool[i].isRunning():
                    self.threadPool[i].run()
        if not createdPanoThread:
            self.threadPool.append(PanoThread(self, IsOneTime, LoopIntervalMinute,
                                              StartHour, EndHour))
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('PanoImageSnapped()'),
                         self.updatePanoImage)
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('ColRowPanTiltPos(QString)'),
                         self.updateColRowPanTiltInfo)
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
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('Message(QString)'),
                         self.printMessage)
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
        Now = datetime.now()
        FileName = os.path.join(self.PanoFolder,
                                "{}_{}_00_00_{:04}.jpg".format(
                                    self.CameraName,
                                    Now.strftime("%Y_%m_%d_%H_%M"),
                                    self.PanoImageNo))
        misc.imsave(FileName, self.Image)

        if os.path.getsize(FileName) > 1000:
            self.printMessage("Wrote image " + FileName)
        else:
            self.printError("Warning: failed to snap an image")

        RunConfigOutFileName = os.path.join(
            self.PanoFolder, "_data", "RunInfo.cvs")
        if not os.path.exists(RunConfigOutFileName):
            with open(RunConfigOutFileName, 'w') as File:
                File.write("Index,Col,Row,PanDeg,TiltDeg,Zoom,Focus\n")
        with open(RunConfigOutFileName, 'a') as File:
            File.write("{},{},{},{},{},{},{}\n".format(
                self.PanoImageNo, self.PanoCol, self.PanoRow,
                self.PanPos, self.TiltPos, self.ZoomPos, self.FocusPos))

        self.PanoImageNo += 1

    def initialisePanoOverView(self):
        # clear log message for last panorama
        self.clearMessages()

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
#            self.printError("Cannot save PanoConfig.yml")
            pass

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
            self.printError("Cannot save PanoOverView image")

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
                    self.printMessage("Warning: pan-tilt fails to move to correct location")
                    self.printMessage("  Desired position: PanPos={}, TiltPos={}".format(
                        Pan, Tilt))
                    self.printMessage("  Current position: PanPos={}, TiltPos={}".format(
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

    def setFocus(self, FOCUSVAL):
        URL = self.CamConfigUpdated["URL_SetFocus"].replace("FOCUSVAL",
                                                            str(FOCUSVAL))
        executeURL(URL)
        self.FocusPos = int(FOCUSVAL)

    def setFocusMode(self):
        if self.CamConfigUpdated is not None:
            if str(self.comboBoxFocusMode.currentText()) == "AUTO":
                URL = self.CamConfigUpdated["URL_SetFocusAuto"]
                executeURL(URL)
            elif str(self.comboBoxFocusMode.currentText()) == "MANUAL":
                URL = self.CamConfigUpdated["URL_SetFocusManual"]
                executeURL(URL)

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
            Message = "Loaded {}:\n".format(Filename) + \
                      "----------\n" + \
                      yaml.dump(self.PanTiltConfig)
            self.printMessage(Message)

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
        Message = "Updated pan-tilt configs:\n" + \
                  "----------\n" + \
                  yaml.dump(self.PanTiltConfigUpdated)
        self.printMessage(Message)

    def loadCameraConfig(self):
        Filename = self.lineEditCameraConfigFilename.text()
        if len(Filename) == 0 or not os.path.exists(Filename):
            Filename = QtGui.QFileDialog.getOpenFileName(
                self, 'Open camera config file', Filename)
        with open(Filename, 'r') as ConfigFile:
            self.lineEditCameraConfigFilename.setText(Filename)
            self.CamConfig = yaml.load(ConfigFile)
            Message = "Loaded {}:\n".format(Filename) + \
                      "----------\n" + \
                      yaml.dump(self.CamConfig)
            self.printMessage(Message)
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
                    self.printError("FocusMode must be AUTO or MANUAL")
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
        Message = "Updated camera configs:\n" + \
                  "----------\n" + \
                  yaml.dump(self.CamConfigUpdated)
        self.printMessage(Message)

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

        self.printMessage("Initialised camera.")

        self.ZoomPos = self.getZoom()
        Zoom = self.lineEditZoom.text()
        if len(Zoom) > 0 and int(Zoom) != self.ZoomPos:
            self.setZoom(int(Zoom))
            self.horizontalSliderZoom.setValue(int(Zoom))

        self.FocusPos = self.getFocus()
        Focus = self.lineEditFocus.text()
        if len(Focus) > 0 and int(Focus) != self.FocusPos:
#            self.Camera.setFocusPosition(int(Focus))
            self.setFocus(int(Focus))

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
            self.connect(self.threadPool[len(self.threadPool)-1],
                         QtCore.SIGNAL('Message(QString)'),
                         self.printMessage)
            self.threadPool[len(self.threadPool)-1].start()

    def stopCamera(self):
        for i in range(len(self.threadPool)):
            self.printMessage(self.threadPool[i].Name)
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
        self.printMessage("Initialised pan-tilt.")

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
            self.printMessage(self.threadPool[i].Name)
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
            float(self.PanPos), float(self.TiltPos), self.ZoomPos, self.FocusPos))
        if self.PanoImageNo > 0:
            self.labelCurrentLiveView.setText(
                "Current image of {}/{} ".format(self.PanoImageNo,
                                                           self.PanoTotal))
        else:
            self.labelCurrentLiveView.setText("Current live view")

    def updatePanTiltInfo(self, PanTiltPos):
        self.PanPos, self.TiltPos = PanTiltPos.split(",")
        self.updatePositions()

    def updateColRowPanTiltInfo(self, ColRowPanTiltPos):
        self.PanoCol, self.PanoRow, self.PanPos, self.TiltPos = \
            ColRowPanTiltPos.split(",")
        self.PanoCol, self.PanoRow = int(self.PanoCol), int(self.PanoRow)
        self.updatePositions()

    def updateZoomFocusInfo(self, ZoomFocusPos):
        self.ZoomPos, self.FocusPos = ZoomFocusPos.split(",")
        self.updatePositions()

    def keyPressEvent(self, event):
        Key = event.key()
        if Key == QtCore.Qt.Key_Escape:
            self.stopPanorama()
            self.close()
#        elif Key == QtCore.Qt.DownArrow:
#            self.PanTilt.panStep("down", 10)
#            event.accept()
#        elif Key == QtCore.Qt.UpArrow:
#            self.PanTilt.panStep("up", 10)
#            event.accept()
#        elif Key == QtCore.Qt.LeftArrow:
#            self.PanTilt.panStep("left", 10)
#            event.accept()
#        elif Key == QtCore.Qt.RightArrow:
#            self.PanTilt.panStep("right", 10)
#            event.accept()
#        elif Key == QtCore.Qt.Key_PageDown:
#            self.Camera.zoomStep("out", 50)
#            event.accept()
#        elif Key == QtCore.Qt.Key_PageUp:
#            self.Camera.zoomStep("in", 50)
#            event.accept()

    def closeEvent(self, event):
        if self.PanoConfigChanged:
            Answer = QtGui.QMessageBox.question(
                self, "Warning",
                "Panoram config changed. Do you want to save changes?",
                QtGui.QMessageBox.Ignore | QtGui.QMessageBox.Save |
                QtGui.QMessageBox.SaveAll, QtGui.QMessageBox.Save)
            if Answer == QtGui.QMessageBox.Save and \
                    os.path.exists(self.PanoConfigFileName):
                self.savePanoConfig(self.PanoConfigFileName)
            elif Answer == QtGui.QMessageBox.SaveAll or \
                    (Answer == QtGui.QMessageBox.Save and
                     not os.path.exists(self.PanoConfigFileName)):
                FileName = str(QtGui.QFileDialog.getSaveFileName(
                               self, 'Save panorama config',
                               self.lineEditRunConfigInFileName.text(),
                               filter='*.yml'))
                if len(os.path.basename(FileName)) > 0:
                    self.savePanoConfig(FileName)

        Answer2 = QtGui.QMessageBox.question(
            self, "Warning", "Are you sure to quit?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
            QtGui.QMessageBox.Yes)
        if Answer2 == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

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
            # pan and tilt camera if click on areas around the edge or drag
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
                self.printMessage("Pan/tilt camera {},{} degrees".format(
                    dp, dt))
                self.PanPosDesired = self.PanPosDesired - dp
                self.TiltPosDesired = self.TiltPosDesired + dt
                self.setPanTilt(self.PanPosDesired, self.TiltPosDesired)
        elif event.button() == QtCore.Qt.MidButton:
            objectSelected = self.childAt(event.pos())
            if objectSelected == self.labelCurrentViewImage:
                # convert Shift/Ctrl + Mouse Mid-Click to image pixel position
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
            elif objectSelected == self.labelPanoOverviewImage:
                # show panorama view of Mid-Click on panorama grid
                self.mousePos = self.labelPanoOverviewImage.mapFromGlobal(
                    event.globalPos())
                size = self.labelPanoOverviewImage.size()
                clickedX = self.mousePos.x()/size.width()
                clickedY = self.mousePos.y()/size.height()
                if clickedX >= 0 and clickedX < self.PanoOverViewWidth and \
                        clickedY >= 0 and clickedY < self.PanoOverViewHeight:
                    Pan = self.TopLeftCorner[0] + clickedX*abs(
                        self.BottomRightCorner[0]-self.TopLeftCorner[0])
                    Tilt = self.TopLeftCorner[1] - clickedY*abs(
                        self.BottomRightCorner[1]-self.TopLeftCorner[1])
                    self.setPanTilt(Pan, Tilt)

    def printMessage(self, Message):
        self.textEditMessages.append(Message)
        self.logger.info(Message)

    def printError(self, Message):
        self.textEditMessages.append("Error: " + Message)
        self.logger.error(Message)
        
    def clearMessages(self):
    	self.textEditMessages.clear()


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
        self.emit(QtCore.SIGNAL('Message(QString)'),
                  "Started {}".format(self.Name))
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
        self.emit(QtCore.SIGNAL('Message(QString)'), "Stopped CameraThread")
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
        self.emit(QtCore.SIGNAL('Message(QString)'),
                  "Started {}".format(self.Name))
        self.stopped = False
        while not self.stopped:
            time.sleep(0.5)  # time delay between queries
            PanPos, TiltPos = self.Pano.getPanTilt()
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
        self.emit(QtCore.SIGNAL('Message(QString)'), "Stopped PanTiltThread")
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


class PanoThread(QtCore.QThread):
    def __init__(self, Pano, IsOneTime=True,
                 LoopIntervalMinute=60, StartHour=0, EndHour=0):
        QtCore.QThread.__init__(self)
        self.Pano = Pano
        self.IsOneTime = IsOneTime
        self.LoopIntervalMinute = LoopIntervalMinute
        self.StartHour = StartHour
        self.EndHour = EndHour
        self.NoImages = self.Pano.PanoCols*self.Pano.PanoRows
        self.Name = "PanoThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def _moveAndSnap(self, iCol, jRow, DelaySeconds=0.1):
        if self.Pano.RunConfig is not None and \
                len(self.Pano.RunConfig["Index"]) == self.NoImages:
            self.Pano.setPanTilt(
                self.Pano.RunConfig["PanDeg"][self.Pano.PanoImageNo],
                self.Pano.RunConfig["TiltDeg"][self.Pano.PanoImageNo])
            self.Pano.setZoom(
                self.Pano.RunConfig["Zoom"][self.Pano.PanoImageNo])
            self.Pano.setFocus(
                self.Pano.RunConfig["Focus"][self.Pano.PanoImageNo])
        else:
            self.Pano.setPanTilt(
                self.Pano.TopLeftCorner[0] +
                iCol*self.Pano.HFoV*(1.0 - self.Pano.Overlap),
                self.Pano.TopLeftCorner[1] -
                jRow*self.Pano.VFoV*(1.0 - self.Pano.Overlap))
        PanPos, TiltPos = self.Pano.getPanTilt()

        # extra time to settle down
        if DelaySeconds != 0:
            time.sleep(DelaySeconds)

        while True:
            Image = self.Pano.snapPhoto().next()
            if Image is not None:
                break
            else:
                self.emit(QtCore.SIGNAL('Message(QString)'),
                          "Try recapturing image")
        ScaledHeight = int(self.Pano.PanoOverViewScale*self.Pano.ImageHeight)
        ScaledWidth = int(self.Pano.PanoOverViewScale*self.Pano.ImageWidth)
        ImageResized = misc.imresize(Image,
                                     (ScaledHeight, ScaledWidth,
                                      Image.shape[2]))
        self.Pano.PanoOverView[
            ScaledHeight*jRow:ScaledHeight*(jRow+1),
            ScaledWidth*iCol:ScaledWidth*(iCol+1), :] = ImageResized
        self.emit(QtCore.SIGNAL('ColRowPanTiltPos(QString)'),
                  "{},{},{},{}".format(iCol, jRow, PanPos, TiltPos))
        self.emit(QtCore.SIGNAL('PanoImageSnapped()'))

    def run(self):
        self.emit(QtCore.SIGNAL('Message(QString)'),
                  "Started {}".format(self.Name))
        self.emit(QtCore.SIGNAL('PanoThreadStarted()'))
        self.stopped = False

#        # make sure panoram loop start within "StartMin" from zero minute
#        Start = datetime.now()
#        WaitSeconds = 60*(self.Pano.PanoStartMin - Start.minute) - Start.second
#        if not self.IsOneTime and \
#                WaitSeconds > 0 and WaitSeconds < self.Pano.PanoWaitMin*60:
#            self.emit(QtCore.SIGNAL('Message(QString)'),
#                      "It's {}. Wait for {} minutes before start.".format(
#                          Start.strftime("%H:%M"), WaitSeconds/60))
#            time.sleep(WaitSeconds)

        self.emit(QtCore.SIGNAL('Message(QString)'),
                  "Save panorma images to {} ".format(self.Pano.RootFolder))

        while not self.Pano.StopPanorama:
            while self.Pano.PausePanorama:
                time.sleep(5)

            # test if there's enough
            Usage = disk_usage.disk_usage(self.Pano.RootFolder)
            if Usage.free < 1e6*int(self.Pano.lineEditMinFreeDiskSpace.text()):
                self.Pano.StopPanorama = True
                self.emit(QtCore.SIGNAL('Message(QString)'),
                      "There's only {} bytes left. Stop".format(Usage.free))
                break

            Start = datetime.now()
            IgnoreHourRange = (self.StartHour > self.EndHour)
            WithinHourRange = (Start.hour >= self.StartHour and \
                               Start.hour <= self.EndHour)
            if self.IsOneTime or IgnoreHourRange or WithinHourRange:
                self.emit(QtCore.SIGNAL('Message(QString)'),
                          "Take a panorama from {}".format(
                              Start.strftime("%H:%M")))
                # create a new panorama folder with increasing index
                NoPanoInSameHour = 1
                while True:
                    self.Pano.PanoFolder = os.path.join(
                        self.Pano.RootFolder,
                        self.Pano.CameraName,
                        Start.strftime("%Y"),
                        Start.strftime("%Y_%m"),
                        Start.strftime("%Y_%m_%d"),
                        Start.strftime("%Y_%m_%d_%H"),
                        "{}_{}_{:02}".format(self.Pano.CameraName,
                                          Start.strftime("%Y_%m_%d_%H"),
                                          NoPanoInSameHour))
                    if not os.path.exists(self.Pano.PanoFolder):
                        os.makedirs(self.Pano.PanoFolder)
                        break
                    else:
                        NoPanoInSameHour += 1

                self.emit(QtCore.SIGNAL('OnePanoStarted()'))
                self.Pano.PanoImageNo = 0
                ScanOrder = str(self.Pano.comboBoxPanoScanOrder.currentText())
                DelaySeconds = 1  # delay to reduce blurring

                if self.Pano.RunConfig is not None:
                    for k in self.Pano.RunConfig["Index"]:
                        i = self.Pano.RunConfig["Col"][self.Pano.PanoImageNo]
                        j = self.Pano.RunConfig["Row"][self.Pano.PanoImageNo]
                        self._moveAndSnap(i, j)
                else:
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

                self.emit(QtCore.SIGNAL('OnePanoDone()'))

                # go to middle point when finish
                if self.Pano.checkBoxUseFocusAtCenter.checkState() == QtCore.Qt.Checked:
                    PANVAL0, TILTVAL0 = self.Pano.lineEditPanoFirstCorner.text().split(",")
                    PANVAL1, TILTVAL1 = self.Pano.lineEditPanoSecondCorner.text().split(",")
                    self.Pano.setPanTilt(0.5*(float(PANVAL0) + float(PANVAL1)),
                                         0.5*(float(TILTVAL0) + float(TILTVAL1)))

            elif not IgnoreHourRange and not WithinHourRange:
                self.emit(QtCore.SIGNAL('Message(QString)'),
                          "Outside hour range ({} to {})".format(self.StartHour,
                                                                 self.EndHour))
                # sleep until start of hour range
                Now = datetime.now()
                DueTime = (24 + self.StartHour)*60
                WaitMin = DueTime - (Now.hour*60 + Now.minute)
                Hours, Mins = divmod(WaitMin, 60)
                self.emit(QtCore.SIGNAL('Message(QString)'),
                          "Wait {} hours and {} minutes".format(Hours, Mins))
                time.sleep(WaitMin*60)

            if self.IsOneTime:
                break
            else:
                # wait until the start of the next hour
                while True:
                    End = datetime.now()
                    Quotient, Remainder = divmod((End.hour*60 + End.minute),
                                                 self.LoopIntervalMinute)
                    if Remainder <= self.Pano.PanoWaitMin:
                        break
                    DueTime = (Quotient+1)*self.LoopIntervalMinute
                    WaitMin = DueTime - (End.hour*60 + End.minute)
                    self.emit(QtCore.SIGNAL('Message(QString)'),
                              "Wait for {} minutes before start.".format(
                                  WaitMin))
                    time.sleep(WaitMin*60)

        self.emit(QtCore.SIGNAL('PanoThreadDone()'))
        return

    def stop(self):
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Now run interactive mode")
        print("Usage:")
        print("    python ipcamcontrol_gui.py # run interactively")
        print("    python ipcamcontrol_gui.py --autorun PanoConfig_AxisCamera.yml # run automatically")
        print("    python ipcamcontrol_gui.py --autorun PanoConfig_ActiCamera.yml # run automatically")
    app = QtGui.QApplication(sys.argv)
    myWindow = MyWindowClass(None)
    myWindow.setWindowTitle("Panorama control using IP Pan-Tilt-Zoom camera")
    myWindow.setWindowIcon(QtGui.QIcon("PanoControl.png"))
    myWindow.show()
    for i in range(len(sys.argv)):
        if sys.argv[i] == "--autorun":
            myWindow.loadPanoConfig(sys.argv[i+1])
            myWindow.mapRemoteFolder()
            myWindow.loopPanorama()
    app.exec_()
