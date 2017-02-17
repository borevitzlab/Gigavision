import os, io
from celery import Celery
from celery.schedules import crontab
from celery.task import periodic_task
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger
import time
from urllib import request as urllib_request
import disk_usage
from datetime import datetime
from ipcamcontrol_webinterface import app as application
import numpy as np
import scipy.misc as misc
import yaml
import pantiltzoomlib

def create_celery_app(app):
    celery = Celery(__name__, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    taskbase = celery.Task
    class ContextTask(taskbase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return taskbase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = create_celery_app(application)
logger = get_task_logger(__name__)


@celery.task(bind=True)
def create_panorama(self,session):



def move_and_snap(self, session, main_folder, dt, i_col, j_row,  delay_sec=0.1):
    set_pan_tilt(self, session,
                 session["top_left_corner"]+
                 i_col * session['HFoV'] * (1.0 - session.get("overlap",0)),
                 session["top_left_corner"]+
                 j_row * session['VFoV'] * (1.0 - session.get("overlap",0)))

    # for some reason this was here, it doesnt actually do anything
    # except inform the user of the current pan tilt postion.
    # pan_pos, tilt_pos = get_pan_tilt(self,session)

    # extra time to settle down
    if delay_sec != 0:
        time.sleep(delay_sec)

    # try 10 times to capture.
    count = 0
    while count < 10:
        count += 1
        image = snap_photo(self,session)
        if image is not None:
            self.update_state(state='PROGRESS',
                      meta={'status': 'Image captured.'})
            break
        else:
            self.update_state(state='WARNING',
                      meta={'status': 'Image not captured, Recapturing image..'})
        time.sleep(0.1)

    # allocate the full size of the image and read write the image.
    scaled_height = int(self.Pano.PanoOverViewScale*session['image_height'])
    scaled_width = int(self.Pano.PanoOverViewScale*session['image_width'])
    imageresized = misc.imresize(image,(scaled_height, scaled_width,image.shape[2]))
    self.Pano.PanoOverView[
        scaled_height * j_row:scaled_height * (j_row + 1),
        scaled_width * i_col:scaled_width * (i_col + 1), :] = imageresized

    self.update_state(state='PROGRESS',
                      meta={'status': 'Overview updated'})

    fn_fmt = "{name}_%Y_%m_%d_%H_%M_00_00_{number:04}.jpg"
    fn = os.path.join(main_folder,
                      datetime.now().strftime(fn_fmt).format(name=session['camera_name'], number=i_col*j_row))

    try:
        misc.imsave(fn, image)
        if os.path.getsize(fn) > 1000:
            self.update_state(state='PROGRESS',
                      meta={'status': 'Image captured: {}x{}'.format(i_col,j_row)})
        else:
            self.update_state(state='PROGRESS',
                      meta={'status': 'Image saving failed (too small image), '.format(i_col,j_row)})
    except:
        self.update_state(state='PROGRESS',
                      meta={'status': 'Image saving failed (other exception), '.format(i_col,j_row)})


@celery.task(bind=True)
def run_pano(self,session):
    primary_folder = session['pano_config']['pano_main_folder']
    fallback_folder = session['pano_config']['pano_fallback_folder']
    main_folder = None
    if os.path.exists(primary_folder):
        main_folder = primary_folder
        self.update_state(state='PROGRESS',
                      meta={'status': 'Primary folder found.'})
    elif os.path.exists(fallback_folder):
        main_folder = fallback_folder
        self.update_state(state='WARNING',
                      meta={'status': 'Primary folder not found, using fallback'})
    else:
        self.update_state(state='FAILURE',
                      meta={'status': 'No folders found. Aborting...'})
        raise Ignore

    self.update_state(state='PROGRESS',
                      meta={'status': 'Saving panorma images to {} '.format(main_folder)})
    time.sleep(5)

    # test if there's enough disk space
    current_usage = disk_usage.disk_usage(main_folder)
    if current_usage.free < 1e6*int(512):
        self.update_state(state='FAILURE',
                      meta={'status':"There's only {} bytes left. Stopping".format(current_usage.free)})
        raise Ignore


    timestream_format = "%Y/%Y_%m/%Y_%m_%d/%Y_%m_%d_%H/{}_%Y_%m_%d_%H_%M"
    dt = datetime.now()
    temp = dt.stftime(timestream_format).format(session["pano_config"]['camera_name'])
    main_folder = os.path.join(main_folder, temp)

    if not os.path.exists(main_folder):
        os.makedirs(main_folder)

    self.update_state(state='PROGRESS',
                      meta={'status': 'Created folder: {} '.format(main_folder)})

    self.update_state(state='PROGRESS',
                      meta={'status': 'Started...'})

    pano_image_num = 0
    delay_sec = 3

    # make sure zoom is correct before taking panorama
    if session.get("zoom_val",None):
        self.update_state(state='PROGRESS',
                      meta={'status': 'Setting zoom to {}'.format(session['zoom_val'])})
        set_zoom(self, session, session["zoom_val"])
        time.sleep(1)


    def cols_right():
        for i in range(session['pano_cols']):
            for j in range(session['pano_rows']):
                if j == 0:
                    move_and_snap(self, session, main_folder, dt, i, j, delay_sec)
                else:
                    move_and_snap(self, session, main_folder, dt, i, j)


    def cols_left():
        for i in range(session['pano_cols']-1, -1, -1):
            for j in range(session['pano_rows']):
                if j == 0:
                    move_and_snap(self, session, main_folder, dt, i, j, delay_sec)
                else:
                    move_and_snap(self, session, main_folder, dt, i, j)


    def rows_down():
        for j in range(session['pano_rows']):
            for i in range(session['pano_cols']):
                if i == 0:
                    move_and_snap(self, session, main_folder, dt, i, j, delay_sec)
                else:
                    move_and_snap(self, session, main_folder, dt, i, j)

    def rows_up():
        for j in range(session['pano_rows']-1, -1, -1):
            for i in session['pano_cols']:
                if i == 0:
                    move_and_snap(self, session, main_folder, dt, i, j, delay_sec)
                else:
                    move_and_snap(self, session, main_folder, dt, i, j)

    funcs = {
        0: cols_right,
        1: cols_left,
        2: rows_down,
        3: rows_up
    }

    # run a function from the signatures.
    funcs[session.get("scan_order",0)]()

@celery.task(bind=True)
def take_panorama(self, session):
    init_camera(self, session)
    init_pan_tilt(self, session)
    # if not initilisedCamera:
    #     initCamera()
    # if not initilisedPanTilt:
    #     initPanTilt()

    if session.get('use_focus_at_center',False):
        index = self.comboBoxFocusMode.findText("AUTO")
        # if index >= 0:
        #     self.setFocusMode()  # make sure this change applies
        set_focus_mode(self, session, "AUTO")
        PANVAL0, TILTVAL0 = session['1st_corner']
        PANVAL1, TILTVAL1 = session['2nd_corner']
        set_pan_tilt(self, session,
                        0.5 * (float(PANVAL0) + float(PANVAL1)),
                        0.5 * (float(TILTVAL0) + float(TILTVAL1)))
        img = snap_photo(self,session)
        temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"temp.jpg")
        misc.imsave(temp_path, img)

        self.update_state(state='PROGRESS',
                      meta={'status': 'Updated image...'})

        time.sleep(3)
        img = snap_photo(self,session)
        misc.imsave(temp_path, img)

        self.update_state(state='PROGRESS',
                      meta={'status': 'Updated image...'})

        set_focus_mode(self, session, "MANUAL")
        time.sleep(3)

        img = snap_photo(self, session)
        misc.imsave(temp_path, img)
        self.update_state(state='PROGRESS',
                      meta={'status': 'Updated image...'})
        time.sleep(3)

    run_pano(self,session)
#        # make sure panoram loop start within "StartMin" from zero minute
#        Start = datetime.now()
#        WaitSeconds = 60*(self.Pano.PanoStartMin - Start.minute) - Start.second
#        if not self.IsOneTime and \
#                WaitSeconds > 0 and WaitSeconds < self.Pano.PanoWaitMin*60:
#            self.emit(QtCore.SIGNAL('Message(QString)'),
#                      "It's {}. Wait for {} minutes before start.".format(
#                          Start.strftime("%H:%M"), WaitSeconds/60))
#            time.sleep(WaitSeconds)


@celery.task(bind=True)
def set_pan_tilt(self, session, pan, tilt):
    # TODO: go through and fix this up.
    pan_tilt_scale = session['ptz_config'].get("pan_tilt_scale",1.0)
    pan_value = str(int(float(pan) * pan_tilt_scale))
    tilt_value = str(int(float(tilt) * pan_tilt_scale))

    url = session['ptz_config']["URL_set_pan_tilt"].format(pan=pan_value)
    url = url.replace("tilt_value", tilt_value)
    executeURL(self, session, url)
    if session['ptz_config']["type"] == "ServoMotors":
        num_loops = 0
        # loop until within 1 degree
        while True:
            pan_cur, tilt_cur = get_pan_tilt(self, session)
            pan_diff = int(abs(float(pan_cur) - float(pan)))
            tilt_diff = int(abs(float(tilt_cur) - float(tilt)))
            if pan_diff <= 1 and tilt_diff <= 1:
                break
            time.sleep(0.2)
            num_loops += 1
            if num_loops > 50:
                self.update_state(state='WARNING',
                      meta={'status': 'Warning: pan-tilt fails to move to correct location: \
                      p:{desp} t:{dest}. current p:{curp} t:{curt}'.format(desp=pan,
                                                                           dest=tilt,
                                                                           curp=pan_cur,
                                                                           curt=tilt_cur)})
                break
        # loop until smallest distance is reached
        while True:
            pan_pos, tilt_pos = get_pan_tilt(self, session)
            pan_diff_new = abs(float(pan_cur) - float(pan))
            tilt_diff_new = abs(float(tilt_cur) - float(tilt))
            if pan_diff_new <= 0.1 and tilt_diff_new <= 0.1:
                break
            elif pan_diff_new >= pan_diff or tilt_diff_new >= tilt_diff:
                break
            else:
                pan_diff = pan_diff_new
                tilt_diff = tilt_diff_new
            time.sleep(0.2)
            num_loops += 1
            if num_loops > 50:
                break

        # this doesnt do anything here.
        # session["pan_pos"],session['tilt_pos'] = pan_pos, tilt_pos
        # TODO: check if this is necessary
        time.sleep(2)  # Acti camera need this extra time
    else:
        pan_cur, tilt_cur = get_pan_tilt(self,session)
        # we cannot actually use this.
        # session["pan_pos"], session['tilt_pos'] = pan_cur, tilt_cur
        time.sleep(0.2)  # Acti camera need this extra time

    return pan_cur, tilt_cur


@celery.task(bind=True)
def executeURL(self, url, return_string=None):
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
                self.update_state(state='WARNING',
                      meta={'status': 'Something went horribly wrong parsing return values.'})
        if len(values) == 1:
            return values[0]
        return values



@celery.task(bind=True)
def go_to_1st_corner(self, session):
    PANVAL, TILTVAL = session.get("pano_first_corner","0,0").split(",")
    set_pan_tilt(self,PANVAL, TILTVAL)

@celery.task(bind=True)
def go_to_2nd_corner(self, session):
    PANVAL, TILTVAL = session.get("pano_second_corner","0,0").split(",")
    set_pan_tilt(self,PANVAL, TILTVAL)


@celery.task(bind=True)
def get_pan_tilt(self, session):
    url = session['ptz_config']["URL_get_pan_tilt"]
    ret = session['ptz_config']["RET_get_pan_tilt"]
    pan, tilt = executeURL(self, url, ret)
    return pan, tilt

@celery.task(bind=True)
def set_focus_mode(self,session, mode):
    if str(mode).upper() == "AUTO":
        url = session['camera_config']["set_focus_auto"]
        executeURL(self,url)
    elif str(mode).upper() == "MANUAL":
        url = session['camera_config']["set_focus_manual"]
        executeURL(self,url)

@celery.task(bind=True)
def set_zoom(self, session, zoom):
    url = session['camera_config']["URL_set_zoom"].format(zoom=zoom)
    executeURL(self, url)
    return zoom


@celery.task(bind=True)
def get_zoom(self, session):
    url = session['camera_config']["URL_get_zoom"]
    ret = session['camera_config']["RET_get_zoom"]
    zoom_val = executeURL(self,url, ret)
    zoom_scale = 1
    if "zoom_scale" in session['camera_config'].keys():
        zoom_scale = session['camera_config']["zoom_scale"]
    zoom_val = int(float(zoom_val) * zoom_scale)
    return zoom_val


@celery.task(bind=True)
def set_focus(self, session, focus):
    url = session['camera_config']["URL_set_focus"].format(focus=focus)
    executeURL(self, url)
    return int(focus)


@celery.task(bind=True)
def get_focus(self, session):
    url = session['camera_config']["get_focus"]
    ret = session['camera_config']["ret_get_focus"]
    focus_val = executeURL(self, url, ret)
    return focus_val


@celery.task(bind=True)
def snap_photo(self, session):
    url = session['camera_config']["get_image"]
    return_string = session['camera_config']["ret_get_image"]
    image = executeURL(self, url, return_string)
    return image

@celery.task(bind=True)
def snap_photo(self, session):
    ImageSize = (session['image_width'],session["image_height"])

    if ImageSize and ImageSize in self.IMAGE_SIZES:
        stream = urllib_request.urlopen(self.HTTPLogin +
                                self.Commands["snap_photo"].format(
                                    ImageSize[0], ImageSize[1],
                                    self.PhotoIndex))
    else:
        stream = urllib_request.urlopen(self.HTTPLogin +
                                self.Commands["snap_photo"].format(
                                    self.ImageSize[0], self.ImageSize[1],
                                    self.PhotoIndex))
    jpg_bytearray = np.asarray(bytearray(stream.read()), dtype=np.uint8)
    self.Image = cv2.imdecode(jpg_bytearray, cv2.CV_LOAD_IMAGE_COLOR)
    self.PhotoIndex += 1
    return self.Image

@celery.task(bind=True)
def init_camera(self, session):

    if session['camera_config'].get("URL_login",None):
        executeURL(self, session, session['camera_config']["URL_login"])

    self.update_state(state='PROGRESS',
                      meta={'status': 'Initialised a camera'})

@celery.task(bind=True)
def init_pan_tilt(self, session):

    if session['ptz_config'].get("URL_login",None):
        executeURL(self, session, session['ptz_config']["URL_login"])

    PanPosStr, TiltPosStr = get_pan_tilt(self,session)
    set_pan_tilt(self, session, float(PanPosStr), float(TiltPosStr))
    time.sleep(1)  # make sure it wakes up
    self.update_state(state='PROGRESS',
                      meta={'status': 'Initialised a PTZ'})


@celery.task(bind=True)
def init_pano_overview(self, session):
    from PIL import Image, ImageDraw

    # get scalings for individual images
    scaled_height = int(session.get("overview_scale",0.2) * session['image_height'])
    scaled_width = int(session.get("overview_scale",0.2) * session["image_width"])

    # create overview image
    overview = Image.new("RGB", session.get("overview_shape", (1280, 720)), color="black")
    draw = ImageDraw.Draw(overview)

    # add lines shows rows and columns
    for i in range(session["pano_cols"]):
        pos = scaled_width*i
        coords = [pos, 0, pos, overview.size[1]]
        draw.line(coords,fill=255)
    for j in range(session["pano_rows"]):
        pos = scaled_height*j
        coords = [0, pos, overview.size[0], pos]
        draw.line(coords,fill=255)
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),"overview.jpg")
    try:
        overview.save(path,
                  format="JPEG")
    except:
        self.update_state(state='FAILURE',
                  meta={'status': "failed to properly overview file to {}".format(path)})
    self.update_state(state='PROGRESS',
                  meta={'status': "Initialised the pano overview"})
#
# def calibrateFoV(self, ZoomPos, PanPos0=150, TiltPos0=0,
#                      PanInc=2, TiltInc=0):
#         """
#         Capture images at different pan/tilt angles, then measure the pixel
#         displacement between the images to estimate the field-of-view angle.
#         """
#         self.Cam.setZoomPosition(ZoomPos)
#         self.Cam.snapPhoto()
#         # add nearby position to reduce backlash
#         self.PanTil.setPanTiltPosition(PanPos0, TiltPos0)
#
#         # capture image with pan motion
#         ImagePanList = []
#         for i in range(100):
#             self.PanTil.setPanTiltPosition(PanPos0+PanInc*i,
#                                            TiltPos0+TiltInc*i)
#             # change zoom to force refocusing
#             self.Cam.refocus()
#             cv2.waitKey(100)
#             while True:
#                 Image = self.Cam.snapPhoto()
#                 if Image is not None:
#                     ImagePanList.append(Image)
#                     break
#             if i == 0:
#                 continue
#             Image0 = ImagePanList[0]
#             Image1 = ImagePanList[i]
#             dx, dy = get_displacement(Image0, Image1)
#             if PanInc != 0:
#                 CamHFoV = Image0.shape[1]*PanInc*i/dx
#             if TiltInc != 0:
#                 CamVFoV = Image0.shape[0]*TiltInc*i/dy
#             if dx > 100 or dy > 100:
#                 break
#
#         # make an increment equal to 1/4 of FoV
#         if PanInc != 0:
#             PanFoVSmall = 0.25*CamHFoV
#         else:
#             PanFoVSmall = 0.25*CamVFoV*self.Cam.ImageSize[0]/self.Cam.ImageSize[1]
#         self.PanTil.setPanTiltPosition(PanPos0 + PanFoVSmall, TiltPos0)
#         while True:
#             # make sure camera finishes refocusing
#             Image1 = self.Cam.snapPhoto()
#             if Image1 is not None:
#                 break
#         dx, dy = get_displacement(Image0, Image1)
#         CamHFoV = Image0.shape[1]*PanFoVSmall/dx
#
#         if TiltInc != 0:
#             TiltFoVSmall = 0.25*CamVFoV
#         else:
#             TiltFoVSmall = 0.25*CamHFoV*self.Cam.ImageSize[1]/self.Cam.ImageSize[0]
#         self.PanTil.setPanTiltPosition(PanPos0 + PanFoVSmall,
#                                        TiltPos0 + TiltFoVSmall)
#         while True:
#             # make sure camera finishes refocusing
#             Image2 = self.Cam.snapPhoto()
#             if Image2 is not None:
#                 break
#         dx, dy = get_displacement(Image1, Image2)
#         CamVFoV = Image0.shape[0]*TiltFoVSmall/dy
#
#         return CamHFoV, CamVFoV

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
#
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
#     PanPosStr, TiltPosStr = get_pan_tilt(self,session)
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
#                   "Save panorma images to {} ".format(self.Pano.root_folder))
#
#         while not self.Pano.StopPanorama:
#             while self.Pano.PausePanorama:
#                 time.sleep(5)
#
#             # test if there's enough
#             Usage = disk_usage.disk_usage(self.Pano.root_folder)
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
#                         self.Pano.root_folder,
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



