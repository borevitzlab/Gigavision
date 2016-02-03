# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong, gareth
"""
import io
import os
import time
from datetime import datetime
from urllib import request as urllib_request

import numpy as np
import scipy.misc as misc
import yaml
from flask import Flask, flash, session, request, render_template, redirect

app = Flask(__name__)
app.debug = True
app.secret_key = "e739b9c6a6aaf27cf44bc86330975ad8edb65a65b009c4c0c3469e9082cf0b8a6e902af10e5d31a160291935f48262114a31fc"


@app.before_request
def initialise_session():
    if not "camera_config" in session.keys():
        session['camera_config'] = {}
    if not "ptz_config" in session.keys():
        session['ptz_config'] = {}
    if not "pano_config" in session.keys():
        session['pano_config'] = {}

    if not "pano_config_fn" in session.keys():
        session['pano_config_fn'] = None

    if not "camera_config_fn" in session.keys():
        session['camera_config_fn'] = None

    if not "ptz_config_fn" in session.keys():
        session['ptz_config_fn'] = None


    def remove_submit(d):
        if "submit" in d.keys():
            del d["submit"]

    remove_submit(session['ptz_config'])
    remove_submit(session['pano_config'])
    remove_submit(session['camera_config'])


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

def convert_config(config_in):
    if type(config_in) == str:
        with open(config_in, 'r') as f:
            config_in = yaml.load(f.read())

    if "ip" in config_in.keys() or "first_corner" in config_in.keys():
        return config_in

    def to_numlist(inp):
        if type(inp) == list:
            return inp
        inp = inp.replace("}", "").replace("{", "")
        if "x" in inp:
            return inp.split("x")
        if "," in inp:
            return inp.split(",")
        return [inp]

    translate = {
        "IPVAL": "ip",
        "USERVAL": "username",
        "PASSVAL": "password",
        "ImageSizeList": "image_size_list",
        "ZoomRange": "zoom_range",
        "Zoom_HorFoVList": "zoom_horizontal_fov_list",
        "Zoom_VirFoVList": "zoom_vertical_fov_list",
        "ZoomListOut": "zoom_list_out",
        "ZoomVal": "zoom_val",
        "FocusVal": "focus_val",
        "FocusMode": "focus_mode",
        "URL_SetImageSize": "URL_set_image_size",
        "URL_SetZoom": "URL_set_zoom",
        "URL_SetFocus": "URL_set_focus",
        "URL_SetFocusAuto": "URL_set_focus_auto",
        "URL_SetFocusManual": "URL_set_focus_manual",
        "URL_GetImage": "URL_get_image",
        "URL_GetImageSize": "URL_get_image_size",
        "URL_GetVideo": "URL_GetVideo",
        "URL_GetZoom": "URL_get_zoom",
        "URL_GetFocus": "URL_get_focus",
        "RET_GetImage": "RET_get_image",
        "RET_SetImageSize": "RET_set_image_size",
        "RET_SetZoom": "RET_set_zoom",
        "RET_SetFocus": "RET_set_focus",
        "RET_GetImageSize": "RET_get_image_size",
        "RET_GetZoom": "RET_get_zoom",
        "RET_GetFocus": "RET_get_focus",
        "1stCorner": "first_corner",
        "2ndCorner": "second_corner",
        "CameraConfigFile": "camera_config_file",
        "PanTiltConfigFile": "ptz_config_file",
        "CameraName": "camera_name",
        "FieldOfView": "field_of_view",
        "LocalFolder": "local_folder",
        "MaxPanoNoImages": "max_no_pano_images",
        "MinFreeSpace": "min_free_space",
        "Overlap": "overlap",
        "PanoEndHour": "pano_end_hour",
        "PanoFallbackFolder": "pano_fallback_folder",
        "PanoGridSize": "pano_grid_size",
        "PanoLoopInterval": "pano_loop_interval",
        "PanoMainFolder": "pano_main_folder",
        "PanoStartHour": "pano_start_hour",
        "PanoStartMin": "pano_start_min",
        "PanoWaitMin": "pano_wait_min",
        "RemoteFolder": "remote_folder",
        "RemoteStorageAddress": "remote_storage_address",
        "RemoteStoragePassword": "remote_storage_password",
        "RemoteStorageUsername": "remote_storage_username",
        "ScanOrder": "scan_order",
        "UseFocusAtCenter": "use_focus_at_center",
        "Zoom": "zoom",
        "Type": "type",
        "PanRange": "pan_range",
        "TiltRange": "tilt_range",
        "PanTiltScale": "pan_tilt_scale",
        "URL_SetPanTilt": "URL_set_pan_tilt",
        "URL_GetPanTilt": "URL_get_pan_tilt",
        "RET_GetPanTilt": "RET_get_pan_tilt"
    }

    needslist = {
        "first_corner",
        "second_corner",
        "pano_grid_size",
        "pano_grid_size"
    }
    needsformatstring = {
        "URL_set_image_size",
        "URL_set_zoom",
        "URL_set_focus",
        "URL_set_focus_auto",
        "URL_set_focus_manual",
        "URL_get_image",
        "URL_get_image_size",
        "URL_GetVideo",
        "URL_get_zoom",
        "URL_get_focus",
        "URL_set_pan_tilt",
        "URL_get_pan_tilt"
    }

    fixstring_map = {
        "USERVAL": "{user}",
        "PASSVAL": "{pass}",
        "IPVAL": "{ip}",
        "ZOOMVAL": "{zoom}",
        "FOCUSVAL": "{focus}",
        "WIDTHVAL": "{width}",
        "HEIGHTVAL": "{height}",
        "PANVAL": "{pan}",
        "TILTVAL": "{tilt}",
        "ZOOM_POSITION": "{zoom_position}",
        "FOCUS_POSITION": "{focus_position}"
    }

    dict_config = {}
    for k, v in config_in.items():
        if k in translate.keys():
            dict_config[translate[k]] = v
    for k, v in dict_config.items():
        if k in needslist:
            dict_config[k] = to_numlist(dict_config[k])
        if k in needsformatstring:
            for match, replacement in fixstring_map.items():
                dict_config[k] = dict_config[k].replace(match, replacement)
    return dict_config


def sort_validate_configs(configs_filepaths):
    panorama_configs = []
    camera_configs = []
    ptz_configs = []
    failed = []
    for config in configs_filepaths:
        try:
            with open(config, 'r') as f:
                d = yaml.load(f)
                if "URL_get_image" in d.keys() or "URL_GetImage" in d.keys():
                    camera_configs.append(config)
                elif "camera_name" in d.keys() or "CameraName" in d.keys():
                    panorama_configs.append(config)
                elif "URL_set_pan_tilt" in d.keys() or "URL_SetPanTilt":
                    ptz_configs.append(config)
                else:
                    failed.append(config)
        except Exception as e:
            flash(u'Exception {}'.format(str(e)), "error")

    if len(failed):
        flash(u'configs that didnt fit into any category: {}'.format(", ".join(failed)), 'warning')

    return panorama_configs, camera_configs, ptz_configs


from glob import glob


def gotoFirstCorner(self):
    PANVAL, TILTVAL = self.lineEditPanoFirstCorner.text().split(",")
    self.setPanTilt(PANVAL, TILTVAL)


def gotoSecondCorner(self):
    PANVAL, TILTVAL = self.lineEditPanoSecondCorner.text().split(",")
    self.setPanTilt(PANVAL, TILTVAL)


def get_pan_tilt(self):
    url = session['ptz_config']["URL_get_pan_tilt"]
    ret = session['ptz_config']["RET_get_pan_tilt"]
    pan, tilt = executeURL(url, ret)
    return pan, tilt


def set_zoom(zoom):
    url = session['camera_config']["URL_set_zoom"].format(zoom=zoom)
    executeURL(url)
    return zoom


def get_zoom():
    url = session['camera_config']["URL_get_zoom"]
    ret = session['camera_config']["RET_get_zoom"]
    zoom_val = executeURL(url, ret)
    zoom_scale = 1
    if "zoom_scale" in session['camera_config'].keys():
        zoom_scale = session['camera_config']["zoom_scale"]
    zoom_val = int(float(zoom_val) * zoom_scale)
    return zoom_val


def set_focus(focus):
    URL = session['camera_config']["URL_set_focus"].format(focus=focus)
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
    keys_to_copy = set(session.keys())
    return


@app.route("/clear-session")
def clearsesh():
    session.clear()
    return ""


def get_filename(p):
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
        if p == "pano":
            if "camera_name" in session['pano_config'].keys():
                filename = str(session['pano_config']['camera_name'])
            else:
                filename = datetime.now().strftime("pano-%y_%m_%d_%H_%M ")
        else:
            filename = datetime.now().strftime(p + "-%y_%m_%d_%H_%M ")
    if filename == "":
        if p == "pano":
            if "camera_name" in session['pano_config'].keys():
                filename = str(session['pano_config']['camera_name'])
            else:
                filename = datetime.now().strftime("pano-%y_%m_%d_%H_%M ")
        else:
            filename = datetime.now().strftime(p + "-%y_%m_%d_%H_%M ")
    if not filename.endswith(".yml") and not filename.endswith(".yaml"):
        filename = filename + ".yml"
    return filename


@app.route("/download-<any('pano','camera','ptz'):p>")
def export_pano_config(p):
    from flask import send_file
    from io import BytesIO
    str_io = BytesIO()
    y = bytes(yaml.dump(session[p + '_config'], default_flow_style=False), "utf-8")
    str_io.write(y)
    str_io.seek(0)
    return send_file(str_io, attachment_filename=get_filename(p), as_attachment=True)


@app.route("/save-<any('pano','camera','ptz'):p>")
def save_pano_config(p):
    """
    saves a panorama config file to the local disk from the session vars.
    :return:
    """

    filename = get_filename(p)

    with open(filename, 'w') as yml_fh:
        yml_fh.write(yaml.dump(session[p + '_config'], default_flow_style=False))

    return redirect("/export")


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


from wtforms import *


class CSVListField(Field):
    """
    Comma separated numbers field.
    Fails if any of the comma separated values are not comma separated.
    Should return a list
    """
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return "[" + u', '.join([str(x) for x in self.data]) + "]"
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            numbracks = valuelist[0].count("]") + valuelist[0].count("[")
            if numbracks > 2 or numbracks == 1:
                raise ValueError(self.gettext("Not a comma separated list."))
            self.data = [x.strip() for x in valuelist[0].replace("[", "").replace("]", "").split(',')]
        else:
            self.data = []
        try:
            iterator = iter(self.data)
        except TypeError:
            raise ValueError(self.gettext("Not a comma separated list."))
        else:
            try:
                for v in self.data:
                    v = float(v)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('One or more values is not a number'))


from pprint import pformat


class CSVListOfListsField(Field):
    """
    Comma separated numbers field.
    Fails if any of the comma separated values are not comma separated.
    Should return a list
    """
    widget = widgets.TextArea()

    def _value(self):
        if self.data:
            return pformat(self.data, width=90, indent=2)
        else:
            return u''

    def process_formdata(self, valuelist):
        if len(valuelist):
            strs = valuelist[0].replace('[', '').split('],')
            self.data = [map(float, s.replace(']', '').split(',')).strip() for s in strs]
            # self.data = [x.strip() for x in valuelist[0].split(',')]
        else:
            self.data = []
        try:
            iterator = iter(self.data)
        except TypeError:
            raise ValueError(self.gettext("Not a comma separated list."))
        else:
            try:
                for v in self.data:
                    v = float(v)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('One or more values is not a number'))


class MustContain(object):
    def __init__(self, *args, message=None):

        for x in args:
            try:
                a = str(x)
            except:
                raise ValueError('Only stringifiable objects may be checked')
        self.req_list = [str(x) for x in args]

        if not message:
            message = u'Field must contain %s'
        self.message = message

    def __call__(self, form, field):
        for check in self.req_list:
            if check not in str(field.data):
                raise ValidationError(self.message % check)


class IPAddressWithPort(validators.IPAddress):
    """
    Validates an IP address. with a port
    only works with ipv4
    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        value = field.data
        valid = False
        if value:
            valid = self.check_ipv4(value)

        if not valid:
            message = self.message
            if message is None:
                message = field.gettext('Invalid IP address or port.')
            raise ValidationError(message)

    @classmethod
    def check_ipv4(cls, value):
        if value.count(":") > 1:
            return False
        if ":" in value:
            value, port = value.split(":")
            try:
                port = int(port)
            except:
                return False
            # ban some ports, and any outside of the max.
            if not 1 <= port <= 65535 or port in [21, 20, 53, 68, 123]:
                return False

        parts = value.split('.')

        if len(parts) == 4 and all(x.isdigit() for x in parts):
            numbers = list(int(x) for x in parts)
            return all(num >= 0 and num < 256 for num in numbers)
        return False


class PanoConfigForm(Form):
    camera_name = StringField("Pano/Camera name")
    camera_config_file = StringField('Camera config filename')
    ptz_config_file = StringField("PTZ config filename")
    field_of_view = StringField("Field of View", default="10.9995,6.2503")
    overlap = FloatField("Overlap %", default=50.0)
    zoom = FloatField("Zoom", default=800.0)
    first_corner = CSVListField('First Corner', default=[113, 9])
    second_corner = CSVListField('Second Corner', default=[163, -15])
    pano_grid_size = CSVListField("Panorama grid shape", default=[8, 9])
    pano_loop_interval = IntegerField("Panorama loop interval (m)", default=60,
                                      validators=[validators.number_range(max=1440, min=2), validators.optional()])
    pano_start_hour = IntegerField("Start hour",
                                   validators=[validators.number_range(max=23, min=0), validators.optional()])
    pano_end_hour = IntegerField("Start hour",
                                 validators=[validators.number_range(max=23, min=1), validators.optional()])
    pano_start_min = IntegerField("Start minutes",
                                  validators=[validators.number_range(max=59, min=0), validators.optional()])
    pano_wait_min = IntegerField("Wait minutes",
                                 validators=[validators.number_range(max=3600, min=0), validators.optional()])
    local_folder = StringField("Local Folder", default='/home/chuong/Data/a_data')
    pano_fallback_folder = StringField("Fallback folder", default='home/pi/Data/Panorama')
    pano_main_folder = StringField("Main Folder", default='/home/chuong/Data/a_data/Gigavision/chuong_tests')
    min_free_space = IntegerField("Minimum free space to keep", default=1000,
                                  validators=[validators.number_range(max=16000, min=256), validators.optional()])
    remote_folder = StringField("Remote Folder", default='/network/phenocam-largedatases/a_data')
    remote_storage_address = StringField("Remote storage address", default='percy.anu.edu.au')
    remote_storage_username = StringField("Remote storage username")
    remote_storage_password = PasswordField("Remote storage password")
    max_no_pano_images = IntegerField("Max number of pano images", default=2000)
    scan_order = StringField('Scan order (see scan-orders for options)', default="Cols, right")
    use_focus_at_center = BooleanField('Use focus at center?', default=True)
    submit = SubmitField()


class PTZConfigForm(Form):
    ip = StringField("IP Address", default="192.168.1.101:81", validators=[IPAddressWithPort(), validators.optional()])
    username = StringField("Username", default="admin")
    password = PasswordField("Password", default="admin")
    type = StringField("Type", default="ServoMotors")
    pan_range = CSVListField("Pan Range", default=[-2, 358])
    tilt_range = CSVListField("Tilt Range", default=[-90, 30])
    pan_tilt_scale = FloatField("Pan/Tilt scaling", default=10.0)
    URL_set_pan_tilt = StringField("URL_set_pan_tilt", default="{ip}/Bump.xml?GoToP={pan}&GoToT={tilt}",
                                   validators=[MustContain("{ip}", "{pan}", '{tilt}'), validators.optional()])
    URL_get_pan_tilt = StringField("URL_get_pan_tilt", default="{ip}/CP_Update.xml",
                                   validators=[MustContain("{ip}"), validators.optional()])
    RET_get_pan_tilt = StringField("RET_get_pan_tilt", default="*<PanPos>{}</PanPos>*<TiltPos>{}</TiltPos>*")
    submit = SubmitField()


class CameraConfigForm(Form):
    ip = StringField("IP Address", default="192.168.1.101:81", validators=[IPAddressWithPort(), validators.optional()])
    username = StringField("Username", default="admin")
    password = PasswordField("Password", default="admin")
    image_size_list = CSVListOfListsField("Image Size list", default=[[1920, 1080], [1280, 720], [640, 480]])
    zoom_range = CSVListField("Zoom Range", default=[30, 1000])
    zoom_val = IntegerField("Zoom Value", default=800,
                            validators=[validators.number_range(max=20000, min=1), validators.optional()])
    zoom_horizontal_fov_list = CSVListOfListsField('', default=[[50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000],
                                                                [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126,
                                                                 12.782, 9.217, 7.050, 5.824]])
    zoom_vertical_fov_list = CSVListOfListsField('', default=[[50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000],
                                                              [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324,
                                                               7.7136, 4.787, 3.729, 2.448]])
    zoom_list_out = CSVListField('Zoom list out', default=[80, 336, 592, 848, 1104, 1360, 1616, 1872, 2128, 2384, 2520])
    URL_set_image_size = StringField("URL_set_image_size",
                                     default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&VIDEO_RESOLUTION=N{width}x{height}",
                                     validators=[MustContain('{ip}', '{user}', '{password}', '{width}', '{height}'),
                                                 validators.optional()])
    URL_set_zoom = StringField("URL_set_zoom",
                               default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&ZOOM=DIRECT,{zoom}",
                               validators=[MustContain('{ip}', '{user}', '{password}', '{zoom}'),
                                           validators.optional()])
    URL_set_focus = StringField("URL_set_focus",
                                default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&FOCUS=DIRECT,{focus}",
                                validators=[MustContain('{ip}', '{user}', '{password}', '{focus}'),
                                            validators.optional()])
    URL_set_focus_auto = StringField("URL_set_focus_auto",
                                     default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&FOCUS=AUTO",
                                     validators=[MustContain('{ip}', '{user}', '{password}'), validators.optional()])
    URL_set_focus_manual = StringField("URL_set_focus_manual",
                                       default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&FOCUS=MANUAL",
                                       validators=[MustContain('{ip}', '{user}', '{password}'), validators.optional()])
    URL_get_image = StringField("URL_get_image", default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&SNAPSHOT",
                                validators=[MustContain('{ip}', '{user}', '{password}'), validators.optional()])
    URL_get_image_size = StringField("URL_get_image_size",
                                     default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&VIDEO_RESOLUTION",
                                     validators=[MustContain('{ip}', '{user}', '{password}'), validators.optional()])
    URL_get_zoom = StringField("URL_get_zoom",
                               default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&{zoom_position}",
                               validators=[MustContain('{ip}', '{user}', '{password}', "{zoom_position}"),
                                           validators.optional()])
    URL_get_focus = StringField("URL_get_focus",
                                default="{ip}/cgi-bin/encoder?USER={user}&PWD={password}&{focus_position}",
                                validators=[MustContain('{ip}', '{user}', '{password}', "{focus_position}"),
                                            validators.optional()])
    RET_set_image_size = StringField("RET_set_image_size", default='OK: VIDEO_RESOLUTION=''N{}x{}''')
    RET_set_zoom = StringField("RET_set_zoom", default='OK: OK: ZOOM=''DIRECT,{}''')
    RET_set_focus = StringField("RET_set_focus", default='OK: FOCUS=''DIRECT,{}''')
    RET_get_image_size = StringField("RET_get_image_size", default='VIDEO_RESOLUTION=''N{}x{}''')
    RET_get_zoom = StringField("RET_get_zoom", default='ZOOM_POSITION=''{}''')
    RET_get_focus = StringField("RET_get_focus", default='FOCUS_POSITION=''{}''')
    submit = SubmitField()


from pprint import pprint as print


@app.route("/export")
def export_view():
    files = glob("*.yml")
    files.extend(glob("*.yaml"))
    pcfg, ccfg, ptzcfg = sort_validate_configs(files)
    template_data = {
        "pcfg": pcfg,
        "ccfg": ccfg,
        "ptzcfg": ptzcfg
    }
    return render_template("export.html", **template_data)


@app.route("/", methods=['POST', 'GET'])
@app.route("/config", methods=['POST', 'GET'])
def config():
    """
    Loads a yaml config file from posted file or get filename
    :return:
    """
    pano_config_dict = {
        "camera_config_file": str,
        "ptz_config_file": str,
        "field_of_view": str,
        "overlap": float,
        "zoom": int,
        "focus": int,
        "first_corner": str,
        "second_corner": str,
        "use_focus_at_center": bool,
        "scan_order": str,
        "min_free_space": int,
        "pano_loop_interval": int,
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
        "max_no_pano_images": int,
        "min_free_space": int
    }

    cam_config_dict = {
        "ip": str,
        "username": str,
        "password": str,
        "image_size_list": list,
        "zoom_horizontal_fov_list": list,
        "zoom_vertical_fov_list": list,
        "zoom_list_out": list,
        "zoom_val": int,
        "zoom_range": list,
        "URL_set_image_size": str,
        "URL_set_zoom": str,
        "URL_set_focus": str,
        "URL_set_focus_auto": str,
        "URL_set_focus_manual": str,
        "URL_get_image": str,
        "URL_get_image_size": str,
        "URL_get_zoom": str,
        "URL_get_focus": str,
        "RET_get_image": str,
        "RET_set_image_size": str,
        "RET_set_zoom": str,
        "RET_set_focus": str,
        "RET_get_image_size": str,
        "RET_get_zoom": str,
        "RET_get_focus": str
    }
    ptz_config_dict = {
        "ip": str,
        "username": str,
        "password": str,
        "type": str,
        "pan_range": list,
        "tilt_range": list,
        "pan_tilt_scale": float,
        "URL_set_pan_tilt": str,
        "URL_get_pan_tilt": str,
        "RET_get_pan_tilt": str
    }

    def load_config_file(session_key, filename, yml=None):
        if not yml:
            if not os.path.isfile(filename):
                flash(u'No file.', 'error')
                return None
            try:
                with open(filename, 'r') as f:
                    yml = yaml.load(f.read())
            except Exception as e:
                flash(u'Couldnt read yaml file: {}'.format(str(e)))
                return None
            session[session_key+"_fn"] = filename if filename is not None else None

        flashes = []
        if session_key == "camera_config":
            for k, v in yml.items():
                if k not in cam_config_dict.keys():
                    flashes.append(u'{}'.format(k))
                else:
                    session[session_key][k] = v
        elif session_key == "ptz_config":
            for k, v in yml.items():
                if k not in ptz_config_dict.keys():
                    flashes.append(u'{}'.format(k))
                else:
                    session[session_key][k] = v
        elif session_key == "pano_config":
            for k, v in yml.items():
                if k not in pano_config_dict.keys():
                    flashes.append(u'{}'.format(k))
                else:
                    session[session_key][k] = v
        if len(flashes):
            flash(u", ".join(flashes) + " are not valid or arent configuration options for a {}".format(
                session_key.replace("_", " ")), "warning")
        else:
            flash(u'Valid config!')

    files = glob("*.yml")
    files.extend(glob("*.yaml"))
    pcfg, ccfg, ptzcfg = sort_validate_configs(files)

    print(session)
    panoform = PanoConfigForm(request.form, prefix="panoform")
    ptzform = PTZConfigForm(request.form, prefix="ptzform")
    camform = CameraConfigForm(request.form, prefix="camform")

    if request.method == "POST":
        for k in request.form.keys():
            if k.split("-")[-1] == 'sel':
                a = {'camera-sel': "camera_config", 'ptz-sel': "ptz_config", 'pano-sel': "pano_config"}
                load_config_file(a[k], request.form[k])

        if len(request.files):
            if "pano-config-file" in request.files.keys():
                f = request.files['pano-config-file']
                if f and allowed_file(f.filename, ["yml", "yaml"]):
                    load_config_file("pano_config", "", yml=convert_config(yaml.load(f.read())))

            if "ptz-config-file" in request.files.keys():
                f = request.files['ptz-config-file']

                if f and allowed_file(f.filename, ["yml", "yaml"]):
                    load_config_file("ptz_config", "", yml=convert_config(yaml.load(f.read())))

            if "cam-config-file" in request.files.keys():
                f = request.files['cam-config-file']

                if f and allowed_file(f.filename, ["yml", "yaml"]):
                    load_config_file("camera_config", "", yml=convert_config(yaml.load(f.read())))
        if panoform.validate() and panoform.submit.data:
            for k in [x for x in vars(panoform) if not x.startswith("_") and not x == "meta"]:
                session['pano_config'][k] = panoform[k].data
        if ptzform.validate() and ptzform.submit.data:
            for k in [x for x in vars(ptzform) if not x.startswith("_") and not x == "meta"]:
                session['ptz_config'][k] = ptzform[k].data
        if camform.validate() and camform.submit.data:
            for k in [x for x in vars(camform) if not x.startswith("_") and not x == "meta"]:
                session['camera_config'][k] = camform[k].data

    for k, v in session['pano_config'].items():
        # check to see whether the panorama form has a value that can be set from the session data
        if v is not None:
            try:
                panoform[k].data = v
            except Exception as e:
                print(u'Exception repopulating form: {}'.format(str(e)))
    for k, v in session['ptz_config'].items():
        # check to see whether the panorama form has a value that can be set from the session data
        if v is not None:
            try:
                ptzform[k].data = v
            except Exception as e:
                print(u'Exception repopulating form: {}'.format(str(e)))

    for k, v in session['camera_config'].items():
        # check to see whether the panorama form has a value that can be set from the session data
        if v is not None:
            try:
                camform[k].data = v
            except Exception as e:
                pass
                # print(u'Exception repopulating form: {}'.format(str(e)))

    template_data = {
        "panoform": panoform,
        "ptzform": ptzform,
        'camform': camform,
        "pano_config_dict": pano_config_dict,
        "cam_config_dict": cam_config_dict,
        "ptz_config_dict": ptz_config_dict,
        "pcfg": pcfg,
        "ccfg": ccfg,
        "ptzcfg": ptzcfg
    }
    return render_template("config-edit.html", **template_data)


def calculate_pano_grid():
    """
    calculates the panorama grid
    :return:
    """
    pan0, tilt0 = session['pano_config'].get('first_corner', ',').split(",")
    pan1, tilt1 = session['pano_config'].get('second_corner', ',').split(",")
    if '' in [pan0, pan1, tilt0, tilt1]:
        flash("First Corner or Second Corner not set", "error")

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
    main_folder = session['main_folder'].format(local_folder=session['local_folder'])
    fallback_folder = session['fallback_folder']
    if os.path.exists(main_folder):
        root_folder = main_folder
        session['root_folder'] = main_folder
    elif os.path.exists(fallback_folder):
        root_folder = fallback_folder
        session['root_folder'] = fallback_folder
        flash(u'main folder doesnt exist, using fallback folder.', 'warning')
    else:
        flash(u'failed to open either folders, aborting.', 'error')

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
# def select_main_folder(self):
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
