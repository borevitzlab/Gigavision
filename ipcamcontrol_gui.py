# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong
"""

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
        self.pushButtonStartPanTilt.clicked.connect(self.initPanTilt)
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
            print(yaml.dump(self.CamConfig))
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
        print(yaml.dump(self.CamConfigUpdated))

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

    def initPanTilt(self):
        self.PanTiltIP = self.lineEditPanTiltAddress.text()
        self.PanTiltUsername = self.lineEditPanTiltUsername.text()
        self.PanTiltPassword = self.lineEditPanTiltPassword.text()
        self.PanTilt = PanTilt(self.PanTiltIP, self.PanTiltUsername,
                               self.PanTiltPassword)
        self.textEditMessages.append("Initialised pan-tilt.")
        self.PanPos, self.TiltPos = self.PanTilt.getPanTiltPosition()
        self.updatePositions()

        # start polling pan-tilt values and show
        self.threadPool.append(PanTiltThread(self.PanTilt))
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('PanTiltPos(QString)'),
                     self.updatePanTiltInfo)
        self.threadPool[len(self.threadPool)-1].start()

    def updateImage(self):
        Image = self.Camera.Image
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
        elif Key == QtCore.Qt.UpArrow:
            self.PanTilt.panStep("up", 10)
        elif Key == QtCore.Qt.LeftArrow:
            self.PanTilt.panStep("left", 10)
        elif Key == QtCore.Qt.RightArrow:
            self.PanTilt.panStep("right", 10)
        elif Key == QtCore.Qt.Key_PageDown:
            self.Camera.zoomStep("out", 50)
        elif Key == QtCore.Qt.Key_PageUp:
            self.Camera.zoomStep("in", 50)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.objectSelected = self.childAt(event.pos())
            self.mousePressed = True
            self.mouseReleased = False
            self.mouseStartPos = self.labelCurrentViewImage.mapFromGlobal(
                event.globalPos())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.mouseReleased = True
            self.mouseEndPos = self.labelCurrentViewImage.mapFromGlobal(
                event.globalPos())
        if self.mousePressed and self.mouseReleased and \
                self.objectSelected == self.labelCurrentViewImage:
            dx = self.mouseEndPos.x() - self.mouseStartPos.x()
            dy = self.mouseEndPos.y() - self.mouseStartPos.y()
            print("Need to pan/tilt camera {},{}".format(dx, dy))
            self.mousePressed = False
            self.mouseReleased = False
            pan = self.HFoV*dx*self.Image.shape[1]/self.labelCurrentViewImage.Width
            tilt = self.VFoV*dy*self.Image.shape[0]/self.labelCurrentViewImage.Height
            self.PanTilt.setPanTiltPosition(pan, tilt)

class CameraThread(QtCore.QThread):
    def __init__(self, Camera):
        QtCore.QThread.__init__(self)
        self.Camera = Camera
        self.NoImages = 0

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            self.Camera.snapPhoto()
            self.emit(QtCore.SIGNAL('ImageSnapped()'))
            ZoomPos = self.Camera.getZoomPosition()
            FocusPos = self.Camera.getFocusPosition()
            self.emit(QtCore.SIGNAL('ZoomFocusPos(QString)'),
                      "{},{}".format(ZoomPos, FocusPos))
        return


class PanTiltThread(QtCore.QThread):
    def __init__(self, PanTil):
        QtCore.QThread.__init__(self)
        self.PanTil = PanTil

    def __del__(self):
        self.wait()

    def run(self):
        while True:
            time.sleep(0.3)  # time delay between queries
            PanPos, TiltPos = self.PanTil.getPanTiltPosition()
            self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
                      "{},{}".format(PanPos, TiltPos))
        return

app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
