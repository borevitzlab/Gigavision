# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong
"""

import sys
import time
from PyQt4 import QtGui, QtCore, uic
from ipcamcontrol import IPCamera, PanTilt
import cv2

form_class = uic.loadUiType("controller.ui")[0]
COLORTABLE = []
for i in range(256):
    COLORTABLE.append(QtGui.qRgb(i/4, i, i/2))


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        for ImageSize in [[1920, 1080], [1280, 720], [640, 480]]:
            self.comboBoxImageSize.addItem("{},{}".format(ImageSize[0],
                                                          ImageSize[1]))
        self.pushButtonStartCamera.clicked.connect(self.initCamera)
        self.pushButtonStartPanTilt.clicked.connect(self.initPanTilt)
        self.PanPos = 0
        self.TiltPos = 0
        self.ZoomPos = 0
        self.FocusPos = 0
        self.threadPool = []

    def initCamera(self):
        self.CameraIP = self.lineEditIPCamURL.text()
        self.CameraUsername = self.lineEditIPCamUsername.text()
        self.CameraPassword = self.lineEditIPCamPassword.text()
        ImageSizeQStr = self.comboBoxImageSize.currentText()
        self.ImageSize = [int(size) for size in str(ImageSizeQStr).split(",")]
        self.Camera = IPCamera(self.CameraIP, self.CameraUsername,
                               self.CameraPassword, self.ImageSize)
        self.textEditMessages.append("Initialised camera.")
        self.ZoomPos = self.Camera.getZoomPosition()
        self.FocusPos = self.Camera.getFocusPosition()
        self.updatePositions()

        # start polling images and show
        self.threadPool.append(CameraThread(self.Camera))
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('ImageSnapped()'), self.updateImage)
        self.connect(self.threadPool[len(self.threadPool)-1],
                     QtCore.SIGNAL('ZoomFocusPos(QString)'),
                     self.updateZoomFocusInfo)
        self.threadPool[len(self.threadPool)-1].start()

    def initPanTilt(self):
        self.PanTiltIP = self.lineEditPanTiltURL.text()
        self.PanTiltUsername = self.lineEditPanTiltUsername.text()
        self.PanTiltPassword = self.lineEditPanTiltPassword.text()
        self.PanTilt = PanTilt(self.PanTiltIP, self.PanTiltUsername,
                               self.PanTiltPassword)
        self.textEditMessages.append("Initialised pan-tilt")
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
            cv2.cvtColor(Image, cv2.cv.CV_BGR2RGB, Image)
            QI = QtGui.QImage(Image.data, Image.shape[1], Image.shape[0],
                              bytesPerLine, QtGui.QImage.Format_RGB888)
            self.labelCurrentViewImage.setPixmap(QtGui.QPixmap.fromImage(QI))

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
