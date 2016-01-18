# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong, gareth
"""
import glob
import io
import os
import subprocess
import time
from datetime import datetime
from urllib import request as urllib_request

import numpy as np
import scipy.misc as misc
import yaml
from flask import Flask, flash, session, request, render_template

import disk_usage

app = Flask(__name__)
app.debug = True
app.secret_key = "e739b9c6a6aaf27cf44bc86330975ad8edb65a65b009c4c0c3469e9082cf0b8a6e902af10e5d31a160291935f48262114a31fc"


@app.before_request
def initialise_session():
    if not "camera_config" in session.keys():
        session['camera_config'] = {}
    if not "ptz_config" in session.keys():
        session['camera_config'] = {}


def executeURL(url, return_string=None):
    if "http://" not in url:
        url = "http://" + url
    if return_string is None:
        stream = urllib_request.urlopen(url)
    elif return_string == "RAW_JPG" or return_string == "RAW_BMP":
        try:
            import PIL.Image
            stream = urllib_request.urlopen(url)
            byte_array = io.BytesIO(stream.read())
            image = np.array(PIL.Image.open(byte_array))
            return image
        except:
            import tempfile
            from scipy import misc
            image_filename = os.path.join(tempfile.gettempdir(), "image.jpg")
            urllib_request.urlretrieve(url, image_filename)
            image = misc.imread(image_filename)
            return image
    else:
        stream = urllib_request.urlopen(url)
        output = stream.read(1024).strip()
        string_list = return_string.split("*")
        string_list = [s for s in string_list if len(s) > 0]
        values = []
        for s in string_list:
            word_list = s.split("{}")
            word_list = [w for w in word_list if len(w) > 0]
            if len(word_list) == 1:
                pos = output.find(word_list[0])
                if pos >= 0:
                    v = output[pos + len(word_list[0]):]
                    temp_values = v.split("\n")
                    values.append(temp_values[0].strip())
            elif len(word_list) == 2:
                pos1 = output.find(word_list[0])
                pos2 = output.find(word_list[1], pos1 + len(word_list[0]))
                if 0 <= pos1 <= pos2:
                    values.append(output[pos1 + len(word_list[0]):pos2])
            else:
                flash("Unhandled case {}".format(s), 'error')
        if len(values) == 1:
            return values[0]
        return values


@app.route("/scan-orders")
def scan_orders():
    from flask import send_file
    return send_file(os.path.join("static", "ScanOrders.png"))


@app.route('/apply-zoom')
def apply_zoom():
    values = list(request.args.keys())
    values.extend(list(request.args.values()))

    def can_int_cast(s):
        try:
            int(float(s))
            return True
        except:
            return False

    value = next((obj for obj in values if can_int_cast(obj)), None)
    if not value:
        return "FAIL", 500
    set_zoom(value)


# fixme
# def setCurrentAsFirstCorner(self):
#     self.lineEditPanoFirstCorner.setText("{},{}".format(self.PanPos,
#                                                         self.TiltPos))
# fixme
# def setCurrentAsSecondCorner(self):
#     self.lineEditPanoSecondCorner.setText("{},{}".format(self.PanPos,
#                                                          self.TiltPos))

# fixme
# def setCurrentAsViewFirstCorner(self):
#     self.lineEditViewFirstCorner.setText("{},{}".format(self.PanPos,
#                                                         self.TiltPos))
# fixme
# def setCurrentAsViewSecondCorner(self):
#     self.lineEditViewSecondCorner.setText("{},{}".format(self.PanPos,
#                                                          self.TiltPos))

def gotoFirstCorner(self):
    PANVAL, TILTVAL = self.lineEditPanoFirstCorner.text().split(",")
    self.setPanTilt(PANVAL, TILTVAL)


def gotoSecondCorner(self):
    PANVAL, TILTVAL = self.lineEditPanoSecondCorner.text().split(",")
    self.setPanTilt(PANVAL, TILTVAL)


def get_pan_tilt(self):
    url = session['ptz_config']["URL_GetPanTilt"]
    ret = session['ptz_config']["RET_GetPanTilt"]
    pan, tilt = executeURL(url, ret)
    return pan, tilt


def set_zoom(zoom):
    url = session['camera_config']["set_zoom"].format(zoom_val=zoom)
    executeURL(url)
    return zoom


def get_zoom():
    url = session['camera_config']["get_zoom"]
    ret = session['camera_config']["ret_get_zoom"]
    zoom_val = executeURL(url, ret)
    zoom_scale = 1
    if "zoom_scale" in session['camera_config'].keys():
        zoom_scale = session['camera_config']["zoom_scale"]
    zoom_val = int(float(zoom_val) * zoom_scale)
    return zoom_val


def set_focus(focus):
    URL = session['camera_config']["set_focus"].format(focus_val=focus)
    executeURL(URL)
    return int(focus)


@app.route("/set-focus-mode")
def set_focus_mode():
    values = list(request.args.keys())
    values.extend(list(request.args.values()))
    value = next((obj for obj in values if str(obj).upper() in ['AUTO', 'MANUAL']), None)

    if session['camera_config'] is not None and value is not None:
        if str(value).upper() == "AUTO":
            url = session['camera_config']["set_focus_auto"]
            executeURL(url)
        elif str(value).upper() == "MANUAL":
            url = session['camera_config']["set_focus_manual"]
            executeURL(url)


def get_focus(self):
    url = session['camera_config']["get_focus"]
    ret = session['camera_config']["ret_get_focus"]
    focus_val = executeURL(url, ret)
    return focus_val


def snap_photo():
    while True:
        url = session['camera_config']["get_image"]
        return_string = session['camera_config']["ret_get_image"]
        image = executeURL(url, return_string)
        yield image


def stream_video(self):
    import PIL.Image
    #        import cv2
    url = session['camera_config']["get_video"]
    if "http://" not in url:
        url = "http://" + url
    stream = urllib_request.urlopen(url)
    byte = ''
    while True:
        byte += stream.read(1024)
        a = byte.find('\xff\xd8')
        b = byte.find('\xff\xd9')
        if a != -1 and b != -1:
            jpg = byte[a:b + 2]
            byte = byte[b + 2:]
            byte_array = io.BytesIO(jpg)
            image = np.array(PIL.Image.open(byte_array))
            #           what is going on here?
            #                Image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.CV_LOAD_IMAGE_COLOR)
            yield image


def calculate_fov():
    """
    Calculates the horizontal and vertical field of view from the apps current
    lineEditViewFirstCorner
    lineEditViewSecondCorner
    lineEditViewFirstCornerPixels
    lineEditViewSecondCornerPixels
    and the current image sizes
    :return: (horizontal FoV, vertical FoV)
    """
    pan1, tilt1 = session['1st_corner']
    pan2, tilt2 = session['2nd_corner']
    try:
        # todo: fix this
        pan_pix1, tilt_pix1 = session['lineEditViewFirstCornerPixels'].split(",")
        pan_pix2, tilt_pix2 = session['lineEditViewSecondCornerPixels'].split(",")
        HFoV = abs(float(pan1) - float(pan2)) / \
               abs(float(pan_pix1) - float(pan_pix2)) * session['image_width']
        VFoV = abs(float(tilt1) - float(tilt2)) / \
               abs(float(tilt_pix1) - float(tilt_pix2)) * session['image_height']
    except:
        HFoV = abs(float(pan1) - float(pan2))
        VFoV = abs(float(tilt1) - float(tilt2))

    if VFoV <= HFoV <= 2 * VFoV:
        session['HFoV'] = HFoV
        session['VFoV'] = VFoV
    else:
        flash("Invalid selection of field of view ({}, {})".format(
                HFoV, VFoV), 'error')
    return (HFoV, VFoV)


def get_savable_pano_config():
    """
    returns a yml string of the session variables that are included here
    :return:
    """

    # todo: fix hfov and vfov and condense  down to field of view for simplicity.
    pano_config_dict = {
        "camera_config_file": str,
        "ptz_config_file": str,
        "field_of_view": str,
        "overlap": float,
        "zoom": int,
        "focus": int,
        "1st_corner": str,
        "2nd_corner": str,
        "use_focus_at_center": bool,
        "scan_order": str,
        "pano_grid_size": str,
        "pano_main_folder": str,
        "pano_loop_interval": int,
        "pano_start_hour": int,
        "pano_end_hour": int,
        "pano_start_min": int,
        "pano_wait_min": int,
        "remote_storage_address": str,
        "remote_storage_username": str,
        "remote_storage_password": str,
        "remote_folder": str,
        "local_folder": str,
        "camera_name": str,
        "pano_fallback_folder": str,
        "max_pano_no_images": int,
        "min_free_space": int
    }
    keys_to_copy = set(session.keys()) & set(pano_config_dict.keys())

    for x in keys_to_copy:
        try:
            pano_config_dict[x] = pano_config_dict[x](session[x])
        except Exception as e:
            flash("Whoa something went wrong typecasting {}, is {} a correct value".format(x, session[x]), "error")

    # if not len(keys_to_copy):
    #     return "NO DATA"

    return yaml.dump(pano_config_dict, default_flow_style=False)


@app.route("/export-config")
def export_pano_config():
    from flask import Response, send_file
    from io import BytesIO
    str_io = BytesIO()
    y = bytes(get_savable_pano_config(), "utf-8")
    str_io.write(y)
    str_io.seek(0)

    return send_file(str_io, attachment_filename="config.yml", as_attachment=True)


@app.route("/save-config")
def save_pano_config():
    """
    saves a panorama config file from the session vars.
    :return:
    """
    filename = None
    filename = request.args.get('filename', None)
    filename = request.args.get('file', None)

    while not filename:
        values = list(request.args.keys()) + list(request.args.values())

        if "filename" in values:
            values.remove("filename")
        if "file" in values:
            values.remove("file")

        if len(values):
            filename = str(values[0])
            break

        if "camera_name" in session.keys():
            filename = str(session['camera_name'])
        else:
            filename = datetime.now().strftime("PanoConfig-%y_%m_%d_%H_%M ")

    if not filename.endswith(".yml") and not filename.endswith(".yaml"):
        filename = filename + ".yml"

    with open(filename, 'w') as yml_fh:
        yml_fh.write(get_savable_pano_config())

    return "Saved as " + filename


def allowed_file(fn, types):
    """
    validates a filename of allowed types
    :param fn:
    :param types: iterable of extensions
    :return:
    """
    if fn.split(".")[-1] in (x.replace(".", "") for x in types):
        return True
    return False


@app.route("/load-pano-config", methods=['POST', 'GET'])
def load_pano_config():
    """
    Loads a yaml panorama config from a POSTed file.
    :return:
    """

    pano_config_dict = {
        "camera_config_file": str,
        "ptz_config_file": str,
        "field_of_view": str,
        "overlap": float,
        "zoom": int,
        "focus": int,
        "1st_corner": str,
        "2nd_corner": str,
        "use_focus_at_center": bool,
        "scan_order": str,
        "pano_grid_size": str,
        "pano_main_folder": str,
        "pano_loop_interval": int,
        "pano_start_hour": int,
        "pano_end_hour": int,
        "pano_start_min": int,
        "pano_wait_min": int,
        "remote_storage_address": str,
        "remote_storage_username": str,
        "remote_storage_password": str,
        "remote_folder": str,
        "local_folder": str,
        "camera_name": str,
        "pano_fallback_folder": str,
        "max_pano_no_images": int,
        "min_free_space": int
    }

    if request.method == "POST":
        print(len(request.files))
        print(list(request.files.keys()))
        if len(request.files):
            f = request.files['config-file']
            if f and allowed_file(f.filename, ["yml", "yaml"]):
                print(yaml.load(f.read()))


    template_data = {
        "pano_config_dict": pano_config_dict
    }
    return render_template("pano-config.html", **template_data)


def calculate_pano_grid():
    """
    calculates the panorama grid
    :return:
    """
    pan0, tilt0 = session['line_edit_pano_first_corner'].split(",")
    pan1, tilt1 = session['line_edit_pano_second_corner'].split(",")
    # HFoV, VFoV = session['lineEditFieldOfView'].split(",")
    # session['HFoV'] = float(HFoV)
    # session['VFoV'] = float(VFoV)
    if float(pan0) <= float(pan1):
        left_pan = float(pan0)
        right_pan = float(pan1)
    else:
        left_pan = float(pan1)
        right_pan = float(pan0)
    if float(tilt0) >= float(tilt1):
        top_tilt = float(tilt0)
        bottom_tilt = float(tilt1)
    else:
        top_tilt = float(tilt1)
        bottom_tilt = float(tilt0)
    session['top_left_corner'] = [left_pan, top_tilt]
    session['bottom_right_corner'] = [right_pan, bottom_tilt]
    session['pano_rows'] = int(round((top_tilt - bottom_tilt) / session['VFoV'] / (1.0 - session['Overlap'])))
    session['pano_cols'] = int(round((right_pan - left_pan) / session['HFoV'] / (1.0 - session['Overlap'])))
    session['pano_total'] = session['PanoRows'] * session['PanoCols']

    # Gigapan Sticher only works with 2000 images max
    if session['pano_total'] > 2000:
        flash('Total number of images {} is more than {}'.format(session['pano_total'], 2000), 'warning')

    # todo: set panogridsize info values.

    if session['pano_rows'] >= 0 and session['pano_cols'] >= 0:
        # todo: enable "takeonepano" button here.
        # todo: enable "looppanorama" button here.
        scale = 2
        # todo: set image size info values here
        image_width, image_height = (session['image_width'], session['image_height'])
        while scale > 0:
            scaled_height = int(scale * image_height)
            scaled_width = int(scale * image_width)
            if scaled_height * session['PanoRows'] <= 1080 and \
                                    scaled_width * session['PanoCols'] <= 1920:
                break
            scale = scale - 0.001
        session['PanoOverViewScale'] = scale
        session['PanoOverViewHeight'] = scaled_height * session['PanoRows']
        session['PanoOverViewWidth'] = scaled_width * session['PanoCols']


        # todo; return some updated infor about the state of the panorama variables in the session.
        # initialisePanoOverView()
        # updatePanoOverView()
    else:
        flash('You broke the number of panorama rows or columns (you need at least 1 of each. Please try again.')


def take_panorama(is_one_time=True):
    # if not initilisedCamera:
    #     initCamera()
    # if not initilisedPanTilt:
    #     initPanTilt()

    calculate_pano_grid()  # make sure everything is up-to-date
    pano_image_no = 0

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
        self.setPanTilt(0.5 * (float(PANVAL0) + float(PANVAL1)),
                        0.5 * (float(TILTVAL0) + float(TILTVAL1)))
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
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('PanoImageSnapped()'),
                     self.updatePanoImage)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('ColRowPanTiltPos(QString)'),
                     self.updateColRowPanTiltInfo)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('PanoThreadStarted()'),
                     self.deactivateLiveView)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('PanoThreadDone()'),
                     self.activateLiveView)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('OnePanoStarted()'),
                     self.initialisePanoOverView)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('OnePanoDone()'),
                     self.finalisePano)
        self.connect(self.threadPool[len(self.threadPool) - 1],
                     QtCore.SIGNAL('Message(QString)'),
                     self.printMessage)
        self.threadPool[len(self.threadPool) - 1].start()

#
#
# def updatePanoOverView(self):
#     height, width, bytesPerComponent = self.PanoOverView.shape
#     bytesPerLine = bytesPerComponent * width
#     QI = QtGui.QImage(self.PanoOverView.data,
#                       self.PanoOverView.shape[1],
#                       self.PanoOverView.shape[0],
#                       bytesPerLine, QtGui.QImage.Format_RGB888)
#     self.labelPanoOverviewImage.setPixmap(
#         QtGui.QPixmap.fromImage(QI))
#     self.labelPanoOverviewImage.setScaledContents(True)
#     self.labelPanoOverviewImage.setGeometry(
#         QtCore.QRect(0, 0, self.PanoOverView.shape[1],
#                      self.PanoOverView.shape[0]))
#
#
# def mapRemoteFolder(self):
#     if os.system == "Windows":
#         self.printError("This mapping needs to be done by win-sshfs")
#         return False
#
#     HostName = str(self.lineEditStorageAddress.text())
#     UserName = str(self.lineEditStorageUsername.text())
#     Password = str(self.lineEditStoragePassword.text())
#     RemoteFolder = str(self.lineEditPanoRemoteFolder.text())
#     LocalFolder = str(self.lineEditPanoLocalFolder.text())
#     if len(glob.glob(os.path.join(LocalFolder, "*"))) > 0:
#         self.printMessage("Remote folder seems to be already mapped")
#         return True
#     elif len(HostName) > 0 and len(UserName) > 0 and \
#                     len(RemoteFolder) > 0 and len(LocalFolder) > 0:
#
#         import pexpect
#         # make sure the folder is not mounted
#         UmountCommand = "fusermount -u {}".format(LocalFolder)
#         try:
#             child = pexpect.spawn(UmountCommand)
#             child.expect(pexpect.EOF)
#             print("Umount previously mounted {}".format(LocalFolder))
#         except:
#             pass
#         time.sleep(1)
#
#         MountCommand = "sshfs {}@{}:{} {}".format(UserName, HostName,
#                                                   RemoteFolder, LocalFolder)
#         self.printMessage('MountCommand = ' + MountCommand)
#         if len(Password) > 0:
#             # try connecting 5 times
#             NoTries = 5
#             for Try in range(NoTries):
#                 try:
#                     print('Try #{}/{} mapping network drive'.format(Try, NoTries))
#                     child = pexpect.spawn(MountCommand)
#                     ExpectedString = "{}@{}'s password:".format(UserName, HostName)
#                     child.expect(ExpectedString)
#                     self.printMessage('ExpectedString = ' + ExpectedString)
#                     time.sleep(0.1)
#                     child.sendline(Password)
#                     time.sleep(10)
#                     child.expect(pexpect.EOF)
#                     self.printMessage("Successfully mapped network drive")
#                     Success = True
#                     break
#                 except:
#                     self.printError("Failed to map network drive")
#                     Success = False
#                     time.sleep(1)
#             return Success
#         else:
#             process = subprocess.Popen(MountCommand, shell=True)
#             sts = os.waitpid(process.pid, 0)
#             if sts[1] != 0:
#                 self.printError("Cannot map remote folder")
#                 return False
#             else:
#                 self.printMessage("Successfully mapped network drive")
#                 return True
#
#
# # todo: input forms for these options
# def selectPanoMainFolder(self):
#     PanoMainFolder = str(self.lineEditPanoMainFolder.text())
#     PanoLocalFolder = str(self.lineEditPanoLocalFolder.text())
#     PanoMainFolder.replace("$LOCAL_FOLDER", PanoLocalFolder)
#     Folder = QtGui.QFileDialog.getExistingDirectory(
#         self, "Select Directory", PanoMainFolder)
#     if len(Folder) > 0:
#         self.lineEditPanoMainFolder.setText(Folder)
#         return True
#     else:
#         return False
#
#
# def selectFallbackFolder(self):
#     PanoFallbackFolder = self.lineEditPanoMainFolderFallBack.text()
#     Folder = QtGui.QFileDialog.getExistingDirectory(self,
#                                                     "Select Directory",
#                                                     PanoFallbackFolder)
#     if len(Folder) > 0:
#         self.lineEditPanoMainFolderFallBack.setText(Folder)
#
#
#
#
#
# def takeOnePanorama(self):
#     self.takePanorama(IsOneTime=True)
#
#
# def loopPanorama(self):
#     self.takePanorama(IsOneTime=False)
#
#
# def pausePanorama(self):
#     self.PausePanorama = not (self.PausePanorama)
#
#     if self.PausePanorama:
#         self.pushButtonPausePanorama.setText("Resume")
#     else:
#         self.pushButtonPausePanorama.setText("Pause")
#
#
# def stopPanorama(self):
#     self.StopPanorama = True
#
#
# def activateLiveView(self):
#     self.startPanTilt()
#     self.startCamera()
#     self.pushButtonTakeOnePano.setEnabled(True)
#     self.pushButtonLoopPanorama.setEnabled(True)
#
#     # update current pan-tilt position
#     self.horizontalSliderPan.setValue(int(self.PanPosDesired))
#     self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))
#
#
# def deactivateLiveView(self):
#     self.stopPanTilt()
#     self.stopCamera()
#     self.pushButtonTakeOnePano.setEnabled(False)
#     self.pushButtonLoopPanorama.setEnabled(False)
#
#
# #        for i in range(len(self.threadPool)):
# #            print(self.threadPool[i].Name)
# #            if self.threadPool[i].Name == "PanoThread":
# ##                self.threadPool[i].stop()
# #                self.threadPool[i].wait()
# #                del self.threadPool[i]
# #                break
#
# def updatePanoImage(self):
#     self.updateImage()
#     self.updatePanoOverView()
#     RunConfigOutFileName = os.path.join(
#         self.PanoFolder, "_data", "RunInfo.cvs")
#     if not os.path.exists(RunConfigOutFileName):
#         with open(RunConfigOutFileName, 'w') as File:
#             File.write("Index,Col,Row,PanDeg,TiltDeg,Zoom,Focus\n")
#     with open(RunConfigOutFileName, 'a') as File:
#         File.write("{},{},{},{},{},{},{}\n".format(
#             self.PanoImageNo, self.PanoCol, self.PanoRow,
#             self.PanPos, self.TiltPos, self.ZoomPos, self.FocusPos))
#
#     self.PanoImageNo += 1
#
#
# def initialisePanoOverView(self):
#     # clear log message for last panorama
#     self.clearMessages()
#
#     ScaledHeight = int(self.PanoOverViewScale * self.ImageHeight)
#     ScaledWidth = int(self.PanoOverViewScale * self.ImageWidth)
#     self.PanoOverView = np.zeros((self.PanoOverViewHeight,
#                                   self.PanoOverViewWidth, 3),
#                                  dtype=np.uint8)
#     # add lines shows rows and columns
#     for i in range(self.PanoCols):
#         self.PanoOverView[:, ScaledWidth * i: ScaledWidth * i + 1, :] = 255
#     for j in range(self.PanoRows):
#         self.PanoOverView[ScaledHeight * j:ScaledHeight * j + 1, :, :] = 255
#     try:
#         # try saving panorama config
#         DataFolder = os.path.join(self.PanoFolder, "_data")
#         if not os.path.exists(DataFolder):
#             os.mkdir(DataFolder)
#         self.savePanoConfig(os.path.join(DataFolder, "PanoConfig.yml"))
#     except:
#         #            self.printError("Cannot save PanoConfig.yml")
#         pass
#
#
# def finalisePano(self):
#     try:
#         # try saving PanoOverView
#         DataFolder = os.path.join(self.PanoFolder, "_data")
#         if not os.path.exists(DataFolder):
#             os.mkdir(DataFolder)
#         Prefix = "PanoOverView"
#         Now = datetime.now()
#         FileName = os.path.join(DataFolder,
#                                 "{}_{}_00_00.jpg".format(
#                                     Prefix,
#                                     Now.strftime("%Y_%m_%d_%H_%M")))
#         misc.imsave(FileName, self.PanoOverView)
#     except:
#         self.printError("Cannot save PanoOverView image")
#
#     # go to middle of panorama view
#     if self.checkBoxUseFocusAtCenter.checkState() == QtCore.Qt.Checked:
#         PANVAL0, TILTVAL0 = self.lineEditPanoFirstCorner.text().split(",")
#         PANVAL1, TILTVAL1 = self.lineEditPanoSecondCorner.text().split(",")
#         self.setPanTilt(0.5 * (float(PANVAL0) + float(PANVAL1)),
#                         0.5 * (float(TILTVAL0) + float(TILTVAL1)))
#
#
# def setPan(self, Pan):
#     self.setPanTilt(Pan, self.TiltPosDesired)
#
#
# def setTilt(self, Tilt):
#     self.setPanTilt(self.PanPosDesired, Tilt)
#
#
# def setZoom2(self, Zoom):
#     if session['camera_config'] is not None:
#         self.setZoom(Zoom)
#         self.lineEditZoom.setText(str(Zoom))
#         self.updateFoVFromZoom(Zoom)
#
#
# def updateFoVFromZoom(self, Zoom):
#     if "Zoom_HorFoVList" in session['camera_config'].keys():
#         ZoomList = session['camera_config']["Zoom_HorFoVList"][0]
#         HFoVList = session['camera_config']["Zoom_HorFoVList"][1]
#         self.HFoV = np.interp(int(Zoom), ZoomList, HFoVList)
#     if "Zoom_VirFoVList" in session['camera_config'].keys():
#         ZoomList = session['camera_config']["Zoom_VirFoVList"][0]
#         VFoVList = session['camera_config']["Zoom_VirFoVList"][1]
#         self.VFoV = np.interp(int(Zoom), ZoomList, VFoVList)
#     if self.HFoV != 0 and self.VFoV != 0:
#         self.lineEditFieldOfView.setText("{},{}".format(self.HFoV, self.VFoV))
#         self.lineEditFieldOfView_2.setText("{},{}".format(self.HFoV, self.VFoV))
#
#
# def setPanTilt(self, Pan, Tilt):
#     if "PanTiltScale" in session['ptz_config'].keys():
#         # this is for Acti camera
#         PanTiltScale = session['ptz_config']["PanTiltScale"]
#         PANVAL = str(int(float(Pan) * PanTiltScale))
#         TILTVAL = str(int(float(Tilt) * PanTiltScale))
#     else:
#         PANVAL = str(float(Pan))
#         TILTVAL = str(float(Tilt))
#     URL = session['ptz_config']["URL_SetPanTilt"].replace("PANVAL",
#                                                           PANVAL)
#     URL = URL.replace("TILTVAL", TILTVAL)
#     executeURL(URL)
#
#     if session['ptz_config']["Type"] == "ServoMotors":
#         NoLoops = 0
#         # loop until within 1 degree
#         while True:
#             PanCur, TiltCur = self.getPanTilt()
#             PanDiff = int(abs(float(PanCur) - float(Pan)))
#             TiltDiff = int(abs(float(TiltCur) - float(Tilt)))
#             if PanDiff <= 1 and TiltDiff <= 1:
#                 break
#             time.sleep(0.2)
#             NoLoops += 1
#             if NoLoops > 50:
#                 self.printMessage("Warning: pan-tilt fails to move to correct location")
#                 self.printMessage("  Desired position: PanPos={}, TiltPos={}".format(
#                     Pan, Tilt))
#                 self.printMessage("  Current position: PanPos={}, TiltPos={}".format(
#                     PanCur, TiltCur))
#                 break
#         # loop until smallest distance is reached
#         while True:
#             PanPos, TiltPos = self.getPanTilt()
#             PanDiffNew = abs(float(PanCur) - float(Pan))
#             TiltDiffNew = abs(float(TiltCur) - float(Tilt))
#             if PanDiffNew <= 0.1 and TiltDiffNew <= 0.1:
#                 break
#             elif PanDiffNew >= PanDiff or TiltDiffNew >= TiltDiff:
#                 break
#             else:
#                 PanDiff = PanDiffNew
#                 TiltDiff = TiltDiffNew
#             time.sleep(0.2)
#             NoLoops += 1
#             if NoLoops > 50:
#                 break
#         self.PanPos, self.TiltPos = PanPos, TiltPos
#         # TODO: check if this is necessary
#         time.sleep(2)  # Acti camera need this extra time
#     else:
#         PanCur, TiltCur = self.getPanTilt()
#         self.PanPos, self.TiltPos = PanCur, TiltCur
#         time.sleep(0.2)  # Acti camera need this extra time
#
#     self.PanPosDesired = float(Pan)
#     self.TiltPosDesired = float(Tilt)
#     self.updatePositions()
#
#
# def loadPanTiltConfig(self):
#     Filename = self.lineEditPanTiltConfigFilename.text()
#     if len(Filename) == 0 or not os.path.exists(Filename):
#         Filename = QtGui.QFileDialog.getOpenFileName(
#             self, 'Open pan-tilt config file', Filename)
#     with open(Filename, 'r') as ConfigFile:
#         self.lineEditPanTiltConfigFilename.setText(Filename)
#         session['ptz_config'] = yaml.load(ConfigFile)
#         Message = "Loaded {}:\n".format(Filename) + \
#                   "----------\n" + \
#                   yaml.dump(session['ptz_config'])
#         self.printMessage(Message)
#
#         if "IPVAL" in session['ptz_config'].keys():
#             self.lineEditPanTiltAddress.setText(
#                 session['ptz_config']["IPVAL"])
#         if "USERVAL" in session['ptz_config'].keys():
#             self.lineEditPanTiltUsername.setText(
#                 session['ptz_config']["USERVAL"])
#         if "PASSVAL" in session['ptz_config'].keys():
#             self.lineEditPanTiltPassword.setText(
#                 session['ptz_config']["PASSVAL"])
#         if "PanRange" in session['ptz_config'].keys():
#             self.horizontalSliderPan.setMinimum(
#                 session['ptz_config']["PanRange"][0])
#             self.horizontalSliderPan.setMaximum(
#                 session['ptz_config']["PanRange"][1])
#         if "TiltRange" in session['ptz_config'].keys():
#             self.horizontalSliderTilt.setMinimum(
#                 session['ptz_config']["TiltRange"][0])
#             self.horizontalSliderTilt.setMaximum(
#                 session['ptz_config']["TiltRange"][1])
#
#
# def updatePanTiltURLs(self):
#     session['ptz_config'] = {}
#     for Key in session['ptz_config'].keys():
#         if "URL" in Key:
#             text = session['ptz_config'][Key]
#             text = text.replace("IPVAL", self.PanTiltIP)
#             text = text.replace("USERVAL", self.PanTiltUsername)
#             text = text.replace("PASSVAL", self.PanTiltPassword)
#             session['ptz_config'][Key] = text
#         else:
#             session['ptz_config'][Key] = session['ptz_config'][Key]
#     Message = "Updated pan-tilt configs:\n" + \
#               "----------\n" + \
#               yaml.dump(session['ptz_config'])
#     self.printMessage(Message)
#
#
# def loadCameraConfig(self):
#     Filename = self.lineEditCameraConfigFilename.text()
#     if len(Filename) == 0 or not os.path.exists(Filename):
#         Filename = QtGui.QFileDialog.getOpenFileName(
#             self, 'Open camera config file', Filename)
#     with open(Filename, 'r') as ConfigFile:
#         self.lineEditCameraConfigFilename.setText(Filename)
#         self.CamConfig = yaml.load(ConfigFile)
#         Message = "Loaded {}:\n".format(Filename) + \
#                   "----------\n" + \
#                   yaml.dump(self.CamConfig)
#         self.printMessage(Message)
#         if "IPVAL" in self.CamConfig.keys():
#             self.lineEditIPCamAddress.setText(self.CamConfig["IPVAL"])
#         if "USERVAL" in self.CamConfig.keys():
#             self.lineEditIPCamUsername.setText(self.CamConfig["USERVAL"])
#         if "PASSVAL" in self.CamConfig.keys():
#             self.lineEditIPCamPassword.setText(self.CamConfig["PASSVAL"])
#         if "ImageSizeList" in self.CamConfig.keys():
#             for ImageSize in self.CamConfig["ImageSizeList"]:
#                 self.comboBoxImageSize.addItem(
#                     "{},{}".format(ImageSize[0], ImageSize[1]))
#         if "ZoomVal" in self.CamConfig.keys():
#             self.lineEditZoom.setText(str(self.CamConfig["ZoomVal"]))
#         if "ZoomRange" in self.CamConfig.keys():
#             self.horizontalSliderZoom.setRange(
#                 int(self.CamConfig["ZoomRange"][0]),
#                 int(self.CamConfig["ZoomRange"][1]))
#         if "set_focus_auto" in self.CamConfig.keys():
#             self.comboBoxFocusMode.addItem("AUTO")
#         if "set_focus_manual" in self.CamConfig.keys():
#             self.comboBoxFocusMode.addItem("MANUAL")
#         if "FocusVal" in self.CamConfig.keys():
#             self.lineEditFocus.setText(str(self.CamConfig["FocusVal"]))
#             # MANUAL mode is assumed as focus value is given
#             index = self.comboBoxFocusMode.findText("MANUAL")
#             if index >= 0:
#                 self.comboBoxFocusMode.setCurrentIndex(index)
#         if "FocusMode" in self.CamConfig.keys():
#             index = self.comboBoxFocusMode.findText(
#                 self.CamConfig["FocusMode"])
#             if index >= 0:
#                 self.comboBoxFocusMode.setCurrentIndex(index)
#             else:
#                 self.printError("FocusMode must be AUTO or MANUAL")
#             if index == 0:  # AUTO
#                 self.lineEditFocus.setText("")
#         if "URL_GetVideo" in self.CamConfig.keys():
#             self.hasMJPGVideo = True
#
#
# def updateCameraURLs(self):
#     session['camera_config'] = {}
#     for Key in self.CamConfig.keys():
#         if "URL" in Key:
#             text = self.CamConfig[Key]
#             text = text.replace("IPVAL", self.CameraIP)
#             text = text.replace("USERVAL", self.CameraUsername)
#             text = text.replace("PASSVAL", self.CameraPassword)
#             text = text.replace("WIDTHVAL", str(self.ImageWidth))
#             text = text.replace("HEIGHTVAL", str(self.ImageHeight))
#             session['camera_config'][Key] = text
#         else:
#             session['camera_config'][Key] = self.CamConfig[Key]
#     Message = "Updated camera configs:\n" + \
#               "----------\n" + \
#               yaml.dump(session['camera_config'])
#     self.printMessage(Message)
#
#
# def initCamera(self):
#     self.CameraIP = self.lineEditIPCamAddress.text()
#     self.CameraUsername = self.lineEditIPCamUsername.text()
#     self.CameraPassword = self.lineEditIPCamPassword.text()
#     ImageWidthStr, ImageHeightStr = \
#         self.comboBoxImageSize.currentText().split(",")
#     self.ImageHeight = int(ImageHeightStr)
#     self.ImageWidth = int(ImageWidthStr)
#     self.updateCameraURLs()
#     if "URL_Login" in session['camera_config'].keys():
#         URL_Str = session['camera_config']["URL_Login"]
#         executeURL(URL_Str)
#
#     self.printMessage("Initialised camera.")
#
#     self.ZoomPos = self.getZoom()
#     Zoom = self.lineEditZoom.text()
#     if len(Zoom) > 0 and int(Zoom) != self.ZoomPos:
#         self.setZoom(int(Zoom))
#         self.horizontalSliderZoom.setValue(int(Zoom))
#
#     self.FocusPos = self.getFocus()
#     Focus = self.lineEditFocus.text()
#     if len(Focus) > 0 and int(Focus) != self.FocusPos:
#         #            self.Camera.setFocusPosition(int(Focus))
#         self.setFocus(int(Focus))
#
#     self.Image = self.snapPhoto().next()
#     self.updateImage()
#     self.updatePositions()
#     self.updateFoVFromZoom(Zoom)
#     self.initilisedCamera = True
#
#
# def startCamera(self):
#     if not self.initilisedCamera:
#         self.initCamera()
#     createdCameraThread = False
#     for i in range(len(self.threadPool)):
#         if self.threadPool[i].Name == "CameraThread":
#             createdCameraThread = True
#             if not self.threadPool[i].isRunning():
#                 self.threadPool[i].run()
#     if not createdCameraThread:
#         # start polling images and show
#         self.threadPool.append(CameraThread(self))
#         self.connect(self.threadPool[len(self.threadPool) - 1],
#                      QtCore.SIGNAL('ImageSnapped()'), self.updateImage)
#         self.connect(self.threadPool[len(self.threadPool) - 1],
#                      QtCore.SIGNAL('ZoomFocusPos(QString)'),
#                      self.updateZoomFocusInfo)
#         self.connect(self.threadPool[len(self.threadPool) - 1],
#                      QtCore.SIGNAL('Message(QString)'),
#                      self.printMessage)
#         self.threadPool[len(self.threadPool) - 1].start()
#
#
# def stopCamera(self):
#     for i in range(len(self.threadPool)):
#         self.printMessage(self.threadPool[i].Name)
#         if self.threadPool[i].Name == "CameraThread":
#             self.threadPool[i].stop()
#             self.threadPool[i].wait()
#             del self.threadPool[i]
#             break
#
#
# def initPanTilt(self):
#     self.PanTiltIP = self.lineEditPanTiltAddress.text()
#     self.PanTiltUsername = self.lineEditPanTiltUsername.text()
#     self.PanTiltPassword = self.lineEditPanTiltPassword.text()
#     self.updatePanTiltURLs()
#     #        self.PanTilt = PanTilt(self.PanTiltIP, self.PanTiltUsername,
#     #                               self.PanTiltPassword)
#     if "URL_Login" in session['ptz_config'].keys():
#         URL_Str = session['ptz_config']["URL_Login"]
#         executeURL(URL_Str)
#
#     PanPosStr, TiltPosStr = self.getPanTilt()
#     self.setPanTilt(float(PanPosStr), float(TiltPosStr))
#     time.sleep(1)  # make sure it wakes up
#     self.PanPosDesired = float(PanPosStr)
#     self.TiltPosDesired = float(TiltPosStr)
#     self.horizontalSliderPan.setValue(int(self.PanPosDesired))
#     self.horizontalSliderTilt.setValue(int(self.TiltPosDesired))
#     self.initilisedPanTilt = True
#     self.printMessage("Initialised pan-tilt.")
#
#
# def startPanTilt(self):
#     if not self.initilisedPanTilt:
#         self.initPanTilt()
#     createdPanTiltThread = False
#     for i in range(len(self.threadPool)):
#         if self.threadPool[i].Name == "PanTiltThread":
#             createdPanTiltThread = True
#             if not self.threadPool[i].isRunning():
#                 self.threadPool[i].run()
#     if not createdPanTiltThread:
#         # start polling pan-tilt values and show
#         self.threadPool.append(PanTiltThread(self))
#         self.connect(self.threadPool[len(self.threadPool) - 1],
#                      QtCore.SIGNAL('PanTiltPos(QString)'),
#                      self.updatePanTiltInfo)
#         self.threadPool[len(self.threadPool) - 1].start()
#
#
# def stopPanTilt(self):
#     for i in range(len(self.threadPool)):
#         self.printMessage(self.threadPool[i].Name)
#         if self.threadPool[i].Name == "PanTiltThread":
#             self.threadPool[i].stop()
#             self.threadPool[i].wait()
#             del self.threadPool[i]
#             break
#
#
# def updateImage(self):
#     if self.Image is None:
#         return
#     Image = np.zeros_like(self.Image)
#     Image[:, :, :] = self.Image[:, :, :]
#     Image[100, :, :] = 255
#     Image[:, 100, :] = 255
#     Image[-100, :, :] = 255
#     Image[:, -100, :] = 255
#     # Convert to RGB for QImage.
#     if Image is not None:
#         height, width, bytesPerComponent = Image.shape
#         bytesPerLine = bytesPerComponent * width
#         QI = QtGui.QImage(Image.data, Image.shape[1], Image.shape[0],
#                           bytesPerLine, QtGui.QImage.Format_RGB888)
#         self.labelCurrentViewImage.setPixmap(QtGui.QPixmap.fromImage(QI))
#         self.labelCurrentViewImage.setScaledContents(True)
#         self.labelCurrentViewImage.setGeometry(
#             QtCore.QRect(0, 0, Image.shape[1], Image.shape[0]))
#
#
# def updatePositions(self):
#     self.labelPositions.setText("P={:.2f}, T={:.2f}, Z={}, F={}".format(
#         float(self.PanPos), float(self.TiltPos), self.ZoomPos, self.FocusPos))
#     if self.PanoImageNo > 0:
#         self.labelCurrentLiveView.setText(
#             "Current image of {}/{} ".format(self.PanoImageNo,
#                                              self.PanoTotal))
#     else:
#         self.labelCurrentLiveView.setText("Current live view")
#
#
# def updatePanTiltInfo(self, PanTiltPos):
#     self.PanPos, self.TiltPos = PanTiltPos.split(",")
#     self.updatePositions()
#
#
# def updateColRowPanTiltInfo(self, ColRowPanTiltPos):
#     self.PanoCol, self.PanoRow, self.PanPos, self.TiltPos = \
#         ColRowPanTiltPos.split(",")
#     self.PanoCol, self.PanoRow = int(self.PanoCol), int(self.PanoRow)
#     self.updatePositions()
#
#
# def updateZoomFocusInfo(self, ZoomFocusPos):
#     self.ZoomPos, self.FocusPos = ZoomFocusPos.split(",")
#     self.updatePositions()
#
#
# def keyPressEvent(self, event):
#     Key = event.key()
#     if Key == QtCore.Qt.Key_Escape:
#         self.stopPanorama()
#         self.close()
#
#
# # elif Key == QtCore.Qt.DownArrow:
# #            self.PanTilt.panStep("down", 10)
# #            event.accept()
# #        elif Key == QtCore.Qt.UpArrow:
# #            self.PanTilt.panStep("up", 10)
# #            event.accept()
# #        elif Key == QtCore.Qt.LeftArrow:
# #            self.PanTilt.panStep("left", 10)
# #            event.accept()
# #        elif Key == QtCore.Qt.RightArrow:
# #            self.PanTilt.panStep("right", 10)
# #            event.accept()
# #        elif Key == QtCore.Qt.Key_PageDown:
# #            self.Camera.zoomStep("out", 50)
# #            event.accept()
# #        elif Key == QtCore.Qt.Key_PageUp:
# #            self.Camera.zoomStep("in", 50)
# #            event.accept()
#
# def closeEvent(self, event):
#     if self.PanoConfigChanged:
#         Answer = QtGui.QMessageBox.question(
#             self, "Warning",
#             "Panoram config changed. Do you want to save changes?",
#             QtGui.QMessageBox.Ignore | QtGui.QMessageBox.Save |
#             QtGui.QMessageBox.SaveAll, QtGui.QMessageBox.Save)
#         if Answer == QtGui.QMessageBox.Save and \
#                 os.path.exists(self.PanoConfigFileName):
#             self.savePanoConfig(self.PanoConfigFileName)
#         elif Answer == QtGui.QMessageBox.SaveAll or \
#                 (Answer == QtGui.QMessageBox.Save and
#                      not os.path.exists(self.PanoConfigFileName)):
#             FileName = str(QtGui.QFileDialog.getSaveFileName(
#                 self, 'Save panorama config',
#                 self.lineEditRunConfigInFileName.text(),
#                 filter='*.yml'))
#             if len(os.path.basename(FileName)) > 0:
#                 self.savePanoConfig(FileName)
#
#     Answer2 = QtGui.QMessageBox.question(
#         self, "Warning", "Are you sure to quit?",
#         QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
#         QtGui.QMessageBox.Yes)
#     if Answer2 == QtGui.QMessageBox.Yes:
#         event.accept()
#     else:
#         event.ignore()
#
#
# def mousePressEvent(self, event):
#     if event.button() == QtCore.Qt.RightButton:
#         self.objectSelected = self.childAt(event.pos())
#         if self.objectSelected == self.labelCurrentViewImage:
#             QtGui.QApplication.setOverrideCursor(
#                 QtGui.QCursor(QtCore.Qt.SizeAllCursor))
#         self.mouseStartPos = self.labelCurrentViewImage.mapFromGlobal(
#             event.globalPos())
#
#
# def mouseReleaseEvent(self, event):
#     modifiers = QtGui.QApplication.keyboardModifiers()
#     if event.button() == QtCore.Qt.RightButton:
#         # pan and tilt camera if click on areas around the edge or drag
#         self.mouseEndPos = self.labelCurrentViewImage.mapFromGlobal(
#             event.globalPos())
#         if self.objectSelected == self.labelCurrentViewImage:
#             QtGui.QApplication.restoreOverrideCursor()
#             dx = self.mouseEndPos.x() - self.mouseStartPos.x()
#             dy = self.mouseEndPos.y() - self.mouseStartPos.y()
#             self.mousePressed = False
#             dp = self.HFoV * dx / self.labelCurrentViewImage.width()
#             dt = self.VFoV * dy / self.labelCurrentViewImage.height()
#             if dp == 0.0 and dt == 0.0:
#                 # pan/tilt one degree at a time if right clicked at edge
#                 x = self.mouseEndPos.x() / self.labelCurrentViewImage.width()
#                 y = self.mouseEndPos.y() / self.labelCurrentViewImage.height()
#                 x *= self.Image.shape[1]
#                 y *= self.Image.shape[0]
#                 if x <= 100:
#                     dp = float(self.lineEditPanStep.text())
#                 elif x >= self.Image.shape[1] - 100:
#                     dp = -float(self.lineEditPanStep.text())
#                 if y <= 100:
#                     dt = float(self.lineEditTiltStep.text())
#                 elif y >= self.Image.shape[0] - 100:
#                     dt = -float(self.lineEditTiltStep.text())
#             self.printMessage("Pan/tilt camera {},{} degrees".format(
#                 dp, dt))
#             self.PanPosDesired = self.PanPosDesired - dp
#             self.TiltPosDesired = self.TiltPosDesired + dt
#             self.setPanTilt(self.PanPosDesired, self.TiltPosDesired)
#     elif event.button() == QtCore.Qt.MidButton:
#         objectSelected = self.childAt(event.pos())
#         if objectSelected == self.labelCurrentViewImage:
#             # convert Shift/Ctrl + Mouse Mid-Click to image pixel position
#             self.mousePos = self.labelCurrentViewImage.mapFromGlobal(
#                 event.globalPos())
#             size = self.labelCurrentViewImage.size()
#             if modifiers == QtCore.Qt.ShiftModifier:
#                 self.lineEditViewFirstCornerPixels.setText("{},{}".format(
#                     self.mousePos.x() / size.width() * self.ImageWidth,
#                     self.mousePos.y() / size.height() * self.ImageHeight))
#             elif modifiers == QtCore.Qt.ControlModifier:
#                 self.lineEditViewSecondCornerPixels.setText("{},{}".format(
#                     self.mousePos.x() / size.width() * self.ImageWidth,
#                     self.mousePos.y() / size.height() * self.ImageHeight))
#         elif objectSelected == self.labelPanoOverviewImage:
#             # show panorama view of Mid-Click on panorama grid
#             self.mousePos = self.labelPanoOverviewImage.mapFromGlobal(
#                 event.globalPos())
#             size = self.labelPanoOverviewImage.size()
#             clickedX = self.mousePos.x() / size.width()
#             clickedY = self.mousePos.y() / size.height()
#             if clickedX >= 0 and clickedX < self.PanoOverViewWidth and \
#                             clickedY >= 0 and clickedY < self.PanoOverViewHeight:
#                 Pan = self.TopLeftCorner[0] + clickedX * abs(
#                     self.BottomRightCorner[0] - self.TopLeftCorner[0])
#                 Tilt = self.TopLeftCorner[1] - clickedY * abs(
#                     self.BottomRightCorner[1] - self.TopLeftCorner[1])
#                 self.setPanTilt(Pan, Tilt)
#
#
# def printMessage(self, Message):
#     self.textEditMessages.append(Message)
#     self.logger.info(Message)
#     if self.PanoFolder is None:
#         self.LogBuffer += Message + '\n'
#     else:
#         LogFilePath = os.path.join(self.PanoFolder, "_data")
#         if not os.path.exists(LogFilePath):
#             os.makedirs(LogFilePath)
#         LogFileName = os.path.join(self.PanoFolder, "_data", 'Log.txt')
#         with open(LogFileName, 'a') as File:
#             if len(self.LogBuffer) > 0:
#                 File.write(self.LogBuffer)
#                 self.LogBuffer = ''
#             File.write(Message + '\n')
#
#
# def printError(self, Message):
#     self.textEditMessages.append("Error: " + Message)
#     self.logger.error(Message)
#     if self.PanoFolder is None:
#         self.LogBuffer += Message + '\n'
#     else:
#         LogFilePath = os.path.join(self.PanoFolder, "_data")
#         if not os.path.exists(LogFilePath):
#             os.makedirs(LogFilePath)
#         LogFileName = os.path.join(self.PanoFolder, "_data", 'Log.txt')
#         with open(LogFileName, 'a') as File:
#             if len(self.LogBuffer) > 0:
#                 File.write(self.LogBuffer)
#                 self.LogBuffer = ''
#             File.write(Message + '\n')
#
#
# def clearMessages(self):
#     self.textEditMessages.clear()
#     try:
#         LogFileName = os.path.join(self.PanoFolder, "_data", 'Log.txt')
#         if os.path.exists(LogFileName) and \
#                         os.path.getsize(LogFileName) > 2 ** 20:
#             # clear log file content if larger than 1MB
#             open(LogFileName, 'w').close()
#     except:
#         pass
#
#
# class CameraThread(QtCore.QThread):
#     def __init__(self, Pano):
#         QtCore.QThread.__init__(self)
#         self.Pano = Pano
#         self.NoImages = 0
#         self.Name = "CameraThread"
#         self.stopped = False
#         self.mutex = QtCore.QMutex()
#
#     def __del__(self):
#         self.wait()
#
#     def run(self):
#         self.emit(QtCore.SIGNAL('Message(QString)'),
#                   "Started {}".format(self.Name))
#         self.stopped = False
#         if self.Pano.hasMJPGVideo:
#             ImageSource = self.Pano.streamVideo()
#         else:
#             ImageSource = self.Pano.snapPhoto()
#         for Image in ImageSource:
#             if self.stopped:
#                 break
#             time.sleep(0.5)  # time delay between queries
#             self.emit(QtCore.SIGNAL('ImageSnapped()'))
#             ZoomPos = self.Pano.getZoom()
#             FocusPos = self.Pano.getFocus()
#             self.emit(QtCore.SIGNAL('ZoomFocusPos(QString)'),
#                       "{},{}".format(ZoomPos, FocusPos))
#         self.emit(QtCore.SIGNAL('Message(QString)'), "Stopped CameraThread")
#         return
#
#     def stop(self):
#         with QtCore.QMutexLocker(self.mutex):
#             self.stopped = True
#
#
# class PanTiltThread(QtCore.QThread):
#     def __init__(self, Pano):
#         QtCore.QThread.__init__(self)
#         self.Pano = Pano
#         self.Name = "PanTiltThread"
#         self.stopped = False
#         self.mutex = QtCore.QMutex()
#
#     def __del__(self):
#         self.wait()
#
#     def run(self):
#         self.emit(QtCore.SIGNAL('Message(QString)'),
#                   "Started {}".format(self.Name))
#         self.stopped = False
#         while not self.stopped:
#             time.sleep(0.5)  # time delay between queries
#             PanPos, TiltPos = self.Pano.getPanTilt()
#             self.emit(QtCore.SIGNAL('PanTiltPos(QString)'),
#                       "{},{}".format(PanPos, TiltPos))
#         self.emit(QtCore.SIGNAL('Message(QString)'), "Stopped PanTiltThread")
#         return
#
#     def stop(self):
#         with QtCore.QMutexLocker(self.mutex):
#             self.stopped = True
#
#
# class PanoThread(QtCore.QThread):
#     def __init__(self, Pano, IsOneTime=True,
#                  LoopIntervalMinute=60, StartHour=0, EndHour=0):
#         QtCore.QThread.__init__(self)
#         self.Pano = Pano
#         self.IsOneTime = IsOneTime
#         self.LoopIntervalMinute = LoopIntervalMinute
#         self.StartHour = StartHour
#         self.EndHour = EndHour
#         self.NoImages = self.Pano.PanoCols * self.Pano.PanoRows
#         self.Name = "PanoThread"
#         self.stopped = False
#         self.mutex = QtCore.QMutex()
#
#     def __del__(self):
#         self.wait()
#
#     def _moveAndSnap(self, iCol, jRow, DelaySeconds=0.1):
#         if self.Pano.RunConfig is not None and \
#                         len(self.Pano.RunConfig["Index"]) == self.NoImages:
#             self.Pano.setPanTilt(
#                 self.Pano.RunConfig["PanDeg"][self.Pano.PanoImageNo],
#                 self.Pano.RunConfig["TiltDeg"][self.Pano.PanoImageNo])
#             self.Pano.setZoom(
#                 self.Pano.RunConfig["Zoom"][self.Pano.PanoImageNo])
#             self.Pano.setFocus(
#                 self.Pano.RunConfig["Focus"][self.Pano.PanoImageNo])
#         else:
#             self.Pano.setPanTilt(
#                 self.Pano.TopLeftCorner[0] +
#                 iCol * self.Pano.HFoV * (1.0 - self.Pano.Overlap),
#                 self.Pano.TopLeftCorner[1] -
#                 jRow * self.Pano.VFoV * (1.0 - self.Pano.Overlap))
#         PanPos, TiltPos = self.Pano.getPanTilt()
#
#         # extra time to settle down
#         if DelaySeconds != 0:
#             time.sleep(DelaySeconds)
#
#         # # wait until new image is saved
#         #        while self.Pano.hasNewImage:
#         #            time.sleep(0.1)
#
#         while True:
#             Image = self.Pano.snapPhoto().next()
#             if Image is not None:
#                 self.Pano.hasNewImage = True
#                 break
#             else:
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Try recapturing image")
#         ScaledHeight = int(self.Pano.PanoOverViewScale * self.Pano.ImageHeight)
#         ScaledWidth = int(self.Pano.PanoOverViewScale * self.Pano.ImageWidth)
#         ImageResized = misc.imresize(Image,
#                                      (ScaledHeight, ScaledWidth,
#                                       Image.shape[2]))
#         self.Pano.PanoOverView[
#         ScaledHeight * jRow:ScaledHeight * (jRow + 1),
#         ScaledWidth * iCol:ScaledWidth * (iCol + 1), :] = ImageResized
#         self.emit(QtCore.SIGNAL('ColRowPanTiltPos(QString)'),
#                   "{},{},{},{}".format(iCol, jRow, PanPos, TiltPos))
#         self.emit(QtCore.SIGNAL('PanoImageSnapped()'))
#
#         Now = datetime.now()
#         FileName = os.path.join(self.Pano.PanoFolder,
#                                 "{}_{}_00_00_{:04}.jpg".format(
#                                     self.Pano.CameraName,
#                                     Now.strftime("%Y_%m_%d_%H_%M"),
#                                     self.Pano.PanoImageNo))
#         try:
#             misc.imsave(FileName, Image)
#             if os.path.getsize(FileName) > 1000:
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Wrote image " + FileName)
#             else:
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Warning: failed to snap an image")
#         except:
#             self.emit(QtCore.SIGNAL('Message(QString)'),
#                       "Failed to write image " + FileName)
#             pass
#
#     def run(self):
#         self.emit(QtCore.SIGNAL('Message(QString)'),
#                   "Started {}".format(self.Name))
#         self.emit(QtCore.SIGNAL('PanoThreadStarted()'))
#         self.stopped = False
#
#         #        # make sure panoram loop start within "StartMin" from zero minute
#         #        Start = datetime.now()
#         #        WaitSeconds = 60*(self.Pano.PanoStartMin - Start.minute) - Start.second
#         #        if not self.IsOneTime and \
#         #                WaitSeconds > 0 and WaitSeconds < self.Pano.PanoWaitMin*60:
#         #            self.emit(QtCore.SIGNAL('Message(QString)'),
#         #                      "It's {}. Wait for {} minutes before start.".format(
#         #                          Start.strftime("%H:%M"), WaitSeconds/60))
#         #            time.sleep(WaitSeconds)
#
#         self.emit(QtCore.SIGNAL('Message(QString)'),
#                   "Save panorma images to {} ".format(self.Pano.RootFolder))
#
#         while not self.Pano.StopPanorama:
#             while self.Pano.PausePanorama:
#                 time.sleep(5)
#
#             # test if there's enough
#             Usage = disk_usage.disk_usage(self.Pano.RootFolder)
#             if Usage.free < 1e6 * int(self.Pano.lineEditMinFreeDiskSpace.text()):
#                 self.Pano.StopPanorama = True
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "There's only {} bytes left. Stop".format(Usage.free))
#                 break
#
#             Start = datetime.now()
#             IgnoreHourRange = (self.StartHour > self.EndHour)
#             WithinHourRange = (Start.hour >= self.StartHour and
#                                Start.hour <= self.EndHour)
#             if self.IsOneTime or IgnoreHourRange or WithinHourRange:
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Take a panorama from {}".format(
#                               Start.strftime("%H:%M")))
#                 # create a new panorama folder with increasing index
#                 NoPanoInSameHour = 1
#                 while True:
#                     self.Pano.PanoFolder = os.path.join(
#                         self.Pano.RootFolder,
#                         self.Pano.CameraName,
#                         Start.strftime("%Y"),
#                         Start.strftime("%Y_%m"),
#                         Start.strftime("%Y_%m_%d"),
#                         Start.strftime("%Y_%m_%d_%H"),
#                         "{}_{}_{:02}".format(self.Pano.CameraName,
#                                              Start.strftime("%Y_%m_%d_%H"),
#                                              NoPanoInSameHour))
#                     if not os.path.exists(self.Pano.PanoFolder):
#                         os.makedirs(self.Pano.PanoFolder)
#                         break
#                     else:
#                         NoPanoInSameHour += 1
#
#                 self.emit(QtCore.SIGNAL('OnePanoStarted()'))
#                 self.Pano.PanoImageNo = 0
#                 ScanOrder = str(self.Pano.comboBoxPanoScanOrder.currentText())
#                 DelaySeconds = 3  # delay to reduce blurring when first start
#
#                 # make sure zoom is correct before taking panorama
#                 try:
#                     self.Pano.setZoom(int(self.Pano.ZoomPos))
#                     self.emit(QtCore.SIGNAL('Message(QString)'),
#                               "Set zoom to {}".format(int(self.Pano.ZoomPos)))
#                     time.sleep(1)
#                 except:
#                     print("Unable to set zoom")
#                     pass
#
#                 if self.Pano.RunConfig is not None:
#                     for k in self.Pano.RunConfig["Index"]:
#                         i = self.Pano.RunConfig["Col"][self.Pano.PanoImageNo]
#                         j = self.Pano.RunConfig["Row"][self.Pano.PanoImageNo]
#                         try:
#                             self._moveAndSnap(i, j)
#                         except:
#                             self.emit(QtCore.SIGNAL('Message(QString)'),
#                                       "Camera or pantilt is not available. Skip #1.")
#                             break
#                 else:
#                     if ScanOrder == "Cols, right":
#                         def f1():
#                             for i in range(self.Pano.PanoCols):
#                                 for j in range(self.Pano.PanoRows):
#                                     while self.Pano.PausePanorama:
#                                         time.sleep(5)
#                                     if self.stopped or self.Pano.StopPanorama:
#                                         break
#                                     try:
#                                         if j == 0:
#                                             self._moveAndSnap(i, j, DelaySeconds)
#                                         else:
#                                             self._moveAndSnap(i, j)
#                                     except:
#                                         self.emit(QtCore.SIGNAL('Message(QString)'),
#                                                   "Camera or pantilt is not available. Skip #2.")
#                                         break
#
#                         f1()
#                     elif ScanOrder == "Cols, left":
#                         def f2():
#                             for i in range(self.Pano.PanoCols - 1, -1, -1):
#                                 for j in range(self.Pano.PanoRows):
#                                     while self.Pano.PausePanorama:
#                                         time.sleep(5)
#                                     if self.stopped or self.Pano.StopPanorama:
#                                         break
#                                     try:
#                                         if j == 0:
#                                             self._moveAndSnap(i, j, DelaySeconds)
#                                         else:
#                                             self._moveAndSnap(i, j)
#                                     except:
#                                         self.emit(QtCore.SIGNAL('Message(QString)'),
#                                                   "Camera or pantilt is not available. Skip #3.")
#                                         return
#
#                         f2()
#                     elif ScanOrder == "Rows, down":
#                         def f3():
#                             for j in range(self.Pano.PanoRows):
#                                 for i in range(self.Pano.PanoCols):
#                                     while self.Pano.PausePanorama:
#                                         time.sleep(5)
#                                     if self.stopped or self.Pano.StopPanorama:
#                                         break
#                                     try:
#                                         if i == 0:
#                                             self._moveAndSnap(i, j, DelaySeconds)
#                                         else:
#                                             self._moveAndSnap(i, j)
#                                     except:
#                                         self.emit(QtCore.SIGNAL('Message(QString)'),
#                                                   "Camera or pantilt is not available. Skip #4.")
#                                         return
#
#                         f3()
#                     else:  # ScanOrder == "Rows, up"
#                         def f4():
#                             for j in range(self.Pano.PanoRows - 1, -1, -1):
#                                 for i in range(self.Pano.PanoCols):
#                                     while self.Pano.PausePanorama:
#                                         time.sleep(5)
#                                     if self.stopped or self.Pano.StopPanorama:
#                                         break
#                                     try:
#                                         if i == 0:
#                                             self._moveAndSnap(i, j, DelaySeconds)
#                                         else:
#                                             self._moveAndSnap(i, j)
#                                     except:
#                                         self.emit(QtCore.SIGNAL('Message(QString)'),
#                                                   "Camera or pantilt is not available. Skip #5.")
#                                         return
#
#                         f4()
#                 self.emit(QtCore.SIGNAL('OnePanoDone()'))
#
#             elif not IgnoreHourRange and not WithinHourRange:
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Outside hour range ({} to {})".format(self.StartHour,
#                                                                  self.EndHour))
#                 # sleep until start of hour range
#                 Now = datetime.now()
#                 DueTime = (24 + self.StartHour) * 60
#                 WaitMin = DueTime - (Now.hour * 60 + Now.minute)
#                 Hours, Mins = divmod(WaitMin, 60)
#                 self.emit(QtCore.SIGNAL('Message(QString)'),
#                           "Wait {} hours and {} minutes".format(Hours, Mins))
#                 time.sleep(WaitMin * 60)
#
#             if self.IsOneTime:
#                 break
#             else:
#                 # wait until the start of the next hour
#                 while True:
#                     End = datetime.now()
#                     Quotient, Remainder = divmod((End.hour * 60 + End.minute),
#                                                  self.LoopIntervalMinute)
#                     if Remainder <= self.Pano.PanoWaitMin:
#                         break
#                     DueTime = (Quotient + 1) * self.LoopIntervalMinute
#                     WaitMin = DueTime - (End.hour * 60 + End.minute)
#                     self.emit(QtCore.SIGNAL('Message(QString)'),
#                               "Wait for {} minutes before start.".format(
#                                   WaitMin))
#                     time.sleep(WaitMin * 60)
#
#         self.emit(QtCore.SIGNAL('PanoThreadDone()'))
#         return
#
#     def stop(self):
#         with QtCore.QMutexLocker(self.mutex):
#             self.stopped = True


if __name__ == "__main__":
    app.run()

"""
OLD QT4 stuff to copy from.

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
    self.hasNewImage = False
    self.PanoTotal = 0
    self.threadPool = []
    self.hasMJPGVideo = False
    self.PausePanorama = False
    self.StopPanorama = False
    self.PanoOverView = None
    session['camera_config'] = None
    session['ptz_config'] = None
    self.RunConfig = None
    self.PanoStartMin = 60
    self.PanoWaitMin = 15
    self.PanoConfigChanged = False
    self.PanoFolder = None

    # create logger
    self.logger = logging.getLogger()
    self.logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    self.logger.addHandler(ch)
    self.LogBuffer = ''
"""

"""
UNknown runconfig?


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
"""
