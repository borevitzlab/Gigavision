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
import urllib
import io


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
        self.pushButtonStartCamera.clicked.connect(self.initCamera)
        self.pushButtonSnapPhoto.clicked.connect(self.snapPhoto)
        self.pushButtonStopCamera.clicked.connect(self.stopCamera)
        self.pushButtonLoadCameraConfigFile.clicked.connect(
            self.loadCameraConfig)

        self.pushButtonStartPanTilt.clicked.connect(self.initPanTilt)
        self.pushButtonStopPanTilt.clicked.connect(self.stopPanTilt)
        self.pushButtonLoadPanTiltConfigFile.clicked.connect(
            self.loadPanTiltConfig)

        self.horizontalSliderPan.valueChanged.connect(self.setPan)
        self.horizontalSliderTilt.valueChanged.connect(self.setTilt)
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

        self.PanPos = 0
        self.TiltPos = 0
        self.ZoomPos = 0
        self.FocusPos = 0
        self.threadPool = []
        self.hasMJPGVideo = False

    def snapPhoto(self):
        while True:
            URL_Str = self.CamConfigUpdated["URL_GetImage"]
            RET_Str = self.CamConfigUpdated["RET_GetImage"]
            Image = executeURL(URL_Str, RET_Str)
            yield Image

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
                Image = np.array(PIL.Image.open(byte_array))
#                Image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.CV_LOAD_IMAGE_COLOR)
                yield Image

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

    def setPan(self, Pan):
        self.setPanTilt(Pan, self.TiltPosDesired)

    def setTilt(self, Tilt):
        self.setPanTilt(self.PanPosDesired, Tilt)

    def setPanTilt(self, Pan, Tilt):
        PanTiltScale = 1
        if "PanTiltScale" in self.PanTiltConfigUpdated.keys():
            PanTiltScale = self.PanTiltConfigUpdated["PanTiltScale"]
        PANVAL = str(int(float(Pan)*PanTiltScale))
        TILTVAL = str(int(float(Tilt)*PanTiltScale))
        URL = self.PanTiltConfigUpdated["URL_SetPanTilt"].replace("PANVAL",
                                                                  PANVAL)
        URL = URL.replace("TILTVAL", TILTVAL)
        executeURL(URL)

#        NoLoops = 0
#        # loop until within 1 degree
#        while True:
#            PanCur, TiltCur = self.getPanTilt()
#            PanDiff = int(abs(float(PanCur) - float(Pan)))
#            TiltDiff = int(abs(float(TiltCur) - float(Tilt)))
#            if PanDiff <= 1 and TiltDiff <= 1:
#                break
#            time.sleep(0.1)
#            NoLoops += 1
#            if NoLoops > 50:
#                print("Warning: pan-tilt fails to move to correct location")
#                print("  Desired position: PanPos={}, TiltPos={}".format(
#                    Pan, Tilt))
#                print("  Current position: PanPos={}, TiltPos={}".format(
#                    PanCur, TiltCur))
#                break
#        #loop until smallest distance is reached
#        while True:
#            PanPos, TiltPos = self.getPanTilt()
#            PanDiffNew = abs(float(PanCur) - float(Pan))
#            TiltDiffNew = abs(float(TiltCur) - float(Tilt))
#            if PanDiffNew <= 0.1 and TiltDiffNew <= 0.1:
#                break
#            elif PanDiffNew >= PanDiff or TiltDiffNew >= TiltDiff:
#                break
#            else:
#                PanDiff = PanDiffNew
#                TiltDiff = TiltDiffNew
#            time.sleep(0.1)
#            NoLoops += 1
#            if NoLoops > 50:
#                break

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

        self.FocusPos = self.getFocus()
        Focus = self.lineEditFocus.text()
        if len(Focus) > 0 and int(Focus) != self.FocusPos:
            self.Camera.setZoomPosition(int(Focus))

        self.updatePositions()

        if "Zoom_HorFoVList" in self.CamConfigUpdated.keys():
            ZoomList = self.CamConfigUpdated["Zoom_HorFoVList"][0]
            HFoVList = self.CamConfigUpdated["Zoom_HorFoVList"][1]
            self.HFoV = np.interp(int(Zoom), ZoomList, HFoVList)
        if "Zoom_VirFoVList" in self.CamConfigUpdated.keys():
            ZoomList = self.CamConfigUpdated["Zoom_VirFoVList"][0]
            VFoVList = self.CamConfigUpdated["Zoom_VirFoVList"][1]
            self.VFoV = np.interp(int(Zoom), ZoomList, VFoVList)
#        self.lineEditFieldOfView.setText("{},{}".format(self.HFoV, self.VFoV))

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
                del self.threadPool[i]
                break

    def updateImage(self):
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
        self.stopped = False
        if self.Pano.hasMJPGVideo:
            ImageSource = self.Pano.streamVideo()
#            self.Pano.textEditMessages.append("Show video stream")
        else:
            ImageSource = self.Pano.snapPhoto()
#            self.Pano.textEditMessages.append("Show image snapshots")
        for Image in ImageSource:
            time.sleep(0.3)  # time delay between queries
            self.Pano.Image = Image
            self.emit(QtCore.SIGNAL('ImageSnapped()'))
            ZoomPos = self.Pano.getZoom()
            FocusPos = self.Pano.getFocus()
            self.emit(QtCore.SIGNAL('ZoomFocusPos(QString)'),
                      "{},{}".format(ZoomPos, FocusPos))
        return

    def stop(self):
        print("Stop CameraThread")
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
        self.stopped = False
        while not self.stopped:
            time.sleep(0.3)  # time delay between queries
            PanPos, TiltPos = self.Pano.getPanTilt()
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
        return

    def stop(self):
        print("Stop PanTiltThread")
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True

app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
