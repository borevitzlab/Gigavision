# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong
"""

from __future__ import absolute_import, division, print_function

import sys
import time
from PyQt4 import QtGui, QtCore, uic
from pantiltzoomlib import IPCamera, PanTilt
import yaml
import os
import numpy as np

form_class = uic.loadUiType("controller2.ui")[0]


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.pushButtonStartCamera.clicked.connect(self.initCamera)
        self.pushButtonStopCamera.clicked.connect(self.stopCamera)
        self.pushButtonStartPanTilt.clicked.connect(self.initPanTilt)
        self.pushButtonStopPanTilt.clicked.connect(self.stopPanTilt)
        self.pushButtonLoadCameraConfigFile.clicked.connect(self.loadCameraConfig)
        self.PanPos = 0
        self.TiltPos = 0
        self.ZoomPos = 0
        self.FocusPos = 0
        self.threadPool = []

    def loadCameraConfig(self):
        Filename = self.lineEditConfigFilename.text()
        if len(Filename) == 0 or not os.path.exists(Filename):
            Filename = QtGui.QFileDialog.getOpenFileName(
                self, 'Open camera config file', Filename)
        with open(Filename, 'r') as ConfigFile:
            self.lineEditConfigFilename.setText(Filename)
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

        self.Camera = IPCamera(self.CameraIP, self.CameraUsername,
                               self.CameraPassword, self.ImageSize)
        self.textEditMessages.append("Initialised camera.")

        self.ZoomPos = self.Camera.getZoomPosition()
        Zoom = self.lineEditZoom.text()
        if len(Zoom) > 0 and int(Zoom) != self.ZoomPos:
            self.Camera.setZoomPosition(int(Zoom))

        self.FocusPos = self.Camera.getFocusPosition()
        Focus = self.lineEditFocus.text()
        if len(Focus) > 0 and int(Focus) != self.FocusPos:
            self.Camera.setZoomPosition(int(Focus))

        self.updatePositions()

        ZoomList = self.CamConfigUpdated["Zoom_HorFoVList"][0]
        HFoVList = self.CamConfigUpdated["Zoom_HorFoVList"][1]
        VFoVList = self.CamConfigUpdated["Zoom_VirFoVList"][1]
        self.HFoV = np.interp(int(Zoom), ZoomList, HFoVList)
        self.VFoV = np.interp(int(Zoom), ZoomList, VFoVList)

        # start polling images and show
        self.threadPool.append(CameraThread(self.Camera))
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
        self.PanTilt = PanTilt(self.PanTiltIP, self.PanTiltUsername,
                               self.PanTiltPassword)
        self.textEditMessages.append("Initialised pan-tilt.")
        PanPosStr, TiltPosStr = self.PanTilt.getPanTiltPosition()
        self.PanPosDesired = float(PanPosStr)
        self.TiltPosDesired = float(TiltPosStr)
        self.updatePositions()

        # start polling pan-tilt values and show
        self.threadPool.append(PanTiltThread(self.PanTilt))
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
        Image = np.zeros_like(self.Camera.Image)
        Image[:, :, :] = self.Camera.Image[:, :, :]
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
                    x *= self.Camera.Image.shape[1]
                    y *= self.Camera.Image.shape[0]
                    if x <= 100:
                        dp = 1
                    elif x >= self.Camera.Image.shape[1]-100:
                        dp = -1
                    if y <= 100:
                        dt = 1
                    elif y >= self.Camera.Image.shape[0]-100:
                        dt = -1
                print("Pan/tilt camera {},{} degrees".format(dp, dt))
                self.PanPosDesired = self.PanPosDesired - dp
                self.TiltPosDesired = self.TiltPosDesired + dt
                self.PanTilt.setPanTiltPosition(
                    self.PanPosDesired, self.TiltPosDesired)


class CameraThread(QtCore.QThread):
    def __init__(self, Camera):
        QtCore.QThread.__init__(self)
        self.Camera = Camera
        self.NoImages = 0
        self.Name = "CameraThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def run(self):
        self.stopped = False
        while not self.stopped:
            self.Camera.snapPhoto()
            self.emit(QtCore.SIGNAL('ImageSnapped()'))
            ZoomPos = self.Camera.getZoomPosition()
            FocusPos = self.Camera.getFocusPosition()
            self.emit(QtCore.SIGNAL('ZoomFocusPos(QString)'),
                      "{},{}".format(ZoomPos, FocusPos))
        return

    def stop(self):
        print("Stop CameraThread")
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True


class PanTiltThread(QtCore.QThread):
    def __init__(self, PanTil):
        QtCore.QThread.__init__(self)
        self.PanTil = PanTil
        self.Name = "PanTiltThread"
        self.stopped = False
        self.mutex = QtCore.QMutex()

    def __del__(self):
        self.wait()

    def run(self):
        self.stopped = False
        while not self.stopped:
            time.sleep(0.3)  # time delay between queries
            PanPos, TiltPos = self.PanTil.getPanTiltPosition()
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
