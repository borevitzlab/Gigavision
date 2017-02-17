# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 18:22:54 2014

@author: chuong, gareth
"""
import io
import os
# import celerypano
from datetime import datetime
from urllib import request as urllib_request
import string
import numpy as np
import yaml
from flask import Flask, flash, session, request, render_template, redirect, jsonify, Response
# from flask_debugtoolbar import DebugToolbarExtension

app = Flask(__name__)
app.debug = True
app.secret_key = "e739b9c6a6aaf27cf44bc86330975ad8edb65a65b009c4c0c3469e9082cf0b8a6e902af10e5d31a160291935f48262114a31fc"
app.config.update({
    "CELERY_BROKER_URL": "mongodb://localhost:27017/brokerdb",
    "CELERY_RESULT_BACKEND": 'mongodb://localhost:27017',
    "CELERY_MONGODB_BACKEND_SETTINGS": {
        'database': 'backenddb',
        'taskmeta_collection': 'celery_taskmeta_collection',
    },
    "CELERY_TIMEZONE": 'Australia/Canberra',
    "CELERY_DISABLE_RATE_LIMITS": True,
    "CELERY_IGNORE_RESULT": False
})

# toolbar = DebugToolbarExtension(app)


def prepare():
    required_keys = ["scan_order"]


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


@app.route("/scan-orders")
def scan_orders():
    from flask import send_file
    return send_file(os.path.join("static", "ScanOrders.png"))


def set_zoom(zoom):
    url = session['camera_config']["URL_set_zoom"].format(zoom=zoom)
    executeURL(url)
    return zoom


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


@app.route("/api/set-corner/<int:corner>", methods=["POST"])
def set(corner):
    if corner in [1, 2]:
        try:
            pt = get_pan_tilt()
        except Exception as e:
            print(str(e))
            return jsonify(messages=[{"message": "Couldnt access the url: {}".format(
                str(e).replace("<", "").replace(">", "")),
                "classsuffix": "danger"}])

    if corner == 1:
        session["1st_corner"] = pt
        return jsonify(messages=[{"message": "Set first corner to {},{}".format(*pt),
                                  "classsuffix": "success"}])

    elif corner == 2:
        session["2nd_corner"] = pt
        return jsonify(messages=[{"message": "Set second corner to {},{}".format(*pt),
                                  "classsuffix": "success"}])
    else:
        return jsonify(messages=[{"message": "mystery corner?",
                                  "classsuffix": "danger"}])


def get_pan_tilt():
    # for test
    import random
    return round(random.uniform(-4, 180)), round(random.uniform(-45, 45))

    url = session['ptz_config']["URL_get_pan_tilt"]
    ret = session['ptz_config']["RET_get_pan_tilt"]
    pan, tilt = executeURL(url, ret)
    return pan, tilt


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
                flash('Something went horribly wrong accessing the url.', "error")
        if len(values) == 1:
            return values[0]
        return values


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
        "Zoom_HorFoVList": "horizontal_fov_list",
        "Zoom_VirFoVList": "vertical_fov_list",
        "ZoomListOut": "zoom_list_out",
        "ZoomVal": "zoom_pos",
        "FocusVal": "focus_val",
        "FocusMode": "focus_mode",
        "URL_SetImageSize": "URL_set_image_size",
        "URL_SetZoom": "URL_set_zoom",
        "URL_SetFocus": "URL_set_focus",
        "URL_SetFocusAuto": "URL_set_focus_mode",
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
        "FieldOfView": "camera_fov",
        "LocalFolder": "spool_dir",
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

    scanorders_map = {
        "colsright": 0,
        "colsleft": 1,
        "rowsdown": 2,
        "rowsup": 3
    }

    needsformatstring = {
        "URL_set_image_size",
        "URL_set_zoom",
        "URL_set_focus",
        "URL_set_focus_mode",
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
        "FOCUS_POSITION": "{focus_position}",
        "AUTO":"{mode}"
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
        if k == "scan_order":
            for c in string.punctuation:
                v = v.replace(c, "")
            dict_config[k] = scanorders_map.get(v.lower(), 0)
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


from PIL import Image, ImageDraw
import math
import time

import cv2
def stream_image(fn):
    """Video streaming generator function."""

    while True:
        frame = ""
        try:
            img = cv2.imread(fn,cv2.IMREAD_COLOR)
            b,frame = cv2.imencode(".jpg", img)
            frame = frame.tostring()

            # with open(fn, 'rb') as f:
            #     frame = f.read()

        except Exception as e:
            print(str(e))
            img = Image.new("RGB", (512, 256))
            draw = ImageDraw.Draw(img)
            pos = float(time.time() * 1000) / 1000
            pos = (1 + math.sin(pos)) / 2
            pos = pos * (img.size[0] - 50)
            draw.multiline_text((pos, img.size[1] / 2),
                                "NO IMAGE",
                                fill="white")
            del draw
            b = io.BytesIO()
            img.save(b, "JPEG")
            b.seek(0)
            frame = b.read()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route("/calibrate")
def calibrate():
    return render_template("calibrate.html")

@app.route("/calibration-stream")
def calibration_image():
    return Response(stream_image("matches.jpg"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/overview-stream")
def stream_overview():
    return Response(stream_image("overview.jpg"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def stream_video():
    def frame():
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
                # what is going on here?
                #      Image = cv2.imdecode(np.fromstring(jpg, dtype=np.uint8),cv2.CV_LOAD_IMAGE_COLOR)
                yield image

    def generate():
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame() + b'\r\n')

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


def get_savable_pano_config():
    """
    returns a yml string of the session variables that are included here
    :return:
    """
    keys_to_copy = set(session.keys())
    return yaml.dump(keys_to_copy)


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


from wtforms import Field
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


class SelectListField(SelectField):
    def pre_validate(self, form):
        for v, _ in self.choices:
            if self.data == v:
                self.data = _
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


class UserInputForm(Form):
    image_size = SelectListField("Image Size",
                                 validators=[validators.Optional()],
                                 choices=[(0, [1920, 1080]), (1, [1280, 720]), (2, [640, 480]), (3, [320, 240])],
                                 coerce=int)
    overlap = FloatField("Overlap (%)", validators=[validators.Optional()])
    scan_order = SelectField('Scan order',
                             choices=[(0, 'Cols, right'),
                                      (1, 'Cols, left'),
                                      (2, 'Rows, down'),
                                      (3, 'Rows, up')],
                             validators=[validators.Optional()],
                             coerce=int)
    submit = SubmitField()
    # user_editable = ["1st_corner", "2nd_corner", "overlap", "scan_order", "image_height", "image_width"]


class PanoConfigForm(Form):
    camera_name = StringField("Pano/Camera name")
    camera_config_file = StringField('Camera config filename')
    ptz_config_file = StringField("PTZ config filename")
    camera_fov = StringField("Field of View", default="10.9995,6.2503")
    overlap = FloatField("Overlap %", default=50.0)
    zoom = FloatField("Zoom", default=800.0)
    first_corner = CSVListField('First Corner', default=[113, 9])
    second_corner = CSVListField('Second Corner', default=[163, -15])
    interval = IntegerField("Panorama interval (s)", default=60,
                                      validators=[validators.number_range(max=1440, min=2), validators.optional()])
    starttime = IntegerField("Start Time (HHMM)",
                                   validators=[validators.number_range(max=23, min=0), validators.optional()])
    stoptime = IntegerField("Stop Time (HHMM)",
                                 validators=[validators.number_range(max=23, min=1), validators.optional()])
    spool_dir = StringField("Spooling directory", default='/home/GigaVision/spool')
    upload_dir = StringField("Upload directory", default='/home/GigaVision/upload')
    server_dir = StringField("Remote Dir", default='/')
    server = StringField("Remote storage address", default='sftp.traitcapture.org')
    username = StringField("Remote storage username", default="picam")
    password = PasswordField("Remote storage password", default="DEFAULT")
    max_no_pano_images = IntegerField("Max number of pano images", default=2000)
    scan_order = SelectField('Scan order',
                             choices=[(0, 'Cols, right'),
                                      (1, 'Cols, left'),
                                      (2, 'Rows, down'),
                                      (3, 'Rows, up')],
                             validators=[validators.Optional()],
                             coerce=int)
    use_focus_at_center = BooleanField('Use focus at center?', default=True)
    submit = SubmitField()


class PTZConfigForm(Form):
    ip = StringField("IP Address", default="192.168.1.101:81", validators=[IPAddressWithPort(), validators.optional()])
    username = StringField("Username", default="admin")
    password = PasswordField("Password", default="admin")
    HTTP_login = StringField("HTTP login format string",
                             default="USER={user}&PWD={password}",
                             validators=[MustContain('{user}', '{password}'),
                                         validators.optional()])
    format_url = StringField("URL format",
                             default="http://{ip}{command}&{HTTP_login}",
                             validators=[MustContain('{ip}',"{command}",'{HTTP_login}'),
                                         validators.optional()])
    type = StringField("Type", default="ServoMotors")
    pan_range = CSVListField("Pan Range", default=[0, 356])
    tilt_range = CSVListField("Tilt Range", default=[-89, 29])
    pan_tilt_scale = FloatField("Pan/Tilt scaling", default=1.0)
    URL_set_pan_tilt = StringField("URL_set_pan_tilt", default="/Bump.xml?GoToP={pan}&GoToT={tilt}",
                                   validators=[MustContain("{pan}", '{tilt}'), validators.optional()])
    URL_get_pan_tilt = StringField("URL_get_pan_tilt", default="/CP_Update.xml",
                                   validators=[MustContain("{ip}"), validators.optional()])
    RET_get_pan_tilt = StringField("RET_get_pan_tilt", default="*<PanPos>{}</PanPos>*<TiltPos>{}</TiltPos>*")
    submit = SubmitField()


class CameraConfigForm(Form):
    ip = StringField("IP Address", default="192.168.1.101:81", validators=[IPAddressWithPort(), validators.optional()])
    username = StringField("Username", default="admin")
    password = PasswordField("Password", default="admin")
    HTTP_login = StringField("HTTP_login",
                             default="USER={user}&PWD={password}",
                             validators=[MustContain('{user}', '{password}'),
                                         validators.optional()])
    format_url = StringField("URL format",
                             default="http://{ip}{command}&{HTTP_login}",
                             validators=[MustContain('{ip}',"{command}",'{HTTP_login}'),
                                         validators.optional()])

    image_size_list = CSVListOfListsField("Image Size list", default=[[1920, 1080], [1280, 720], [640, 480]])
    zoom_range = CSVListField("Zoom Range", default=[30, 1000])
    zoom_pos = IntegerField("Zoom Value", default=800,
                            validators=[validators.number_range(max=20000, min=1), validators.optional()])
    horizontal_fov_list = CSVListOfListsField('', default=[[50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000],
                                                                [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126,
                                                                 12.782, 9.217, 7.050, 5.824]])
    vertical_fov_list = CSVListOfListsField('', default=[[50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000],
                                                              [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324,
                                                               7.7136, 4.787, 3.729, 2.448]])
    zoom_list_out = CSVListField('Zoom list out', default=[80, 336, 592, 848, 1104, 1360, 1616, 1872, 2128, 2384, 2520])

    URL_set_image_size = StringField("URL_set_image_size",
                                     default="/cgi-bin/encoder&VIDEO_RESOLUTION=N{width}x{height}",
                                     validators=[MustContain('{width}', '{height}'),
                                                 validators.optional()])
    URL_set_zoom = StringField("URL_set_zoom",
                               default="/cgi-bin/encoder&ZOOM=DIRECT,{zoom}",
                               validators=[MustContain('{zoom}'),
                                           validators.optional()])
    URL_set_focus = StringField("URL_set_focus",
                                default="/cgi-bin/encoder&FOCUS=DIRECT,{focus}",
                                validators=[MustContain('{focus}'),
                                            validators.optional()])
    URL_set_focus_mode = StringField("URL_set_focus_mode",
                                     default="/cgi-bin/encoder&FOCUS={mode}",
                                     validators=[MustContain("{mode}"), validators.optional()])
    URL_get_image = StringField("URL_get_image", default="/cgi-bin/encoder&SNAPSHOT",
                                validators=[validators.optional()])
    URL_get_image_size = StringField("URL_get_image_size",
                                     default="/cgi-bin/encoder&VIDEO_RESOLUTION",
                                     validators=[validators.optional()])
    URL_get_zoom = StringField("URL_get_zoom",
                               default="/cgi-bin/encoder&{zoom_position}",
                               validators=[MustContain("{zoom_position}"),
                                           validators.optional()])
    URL_get_focus = StringField("URL_get_focus",
                                default="/cgi-bin/encoder&{focus_position}",
                                validators=[MustContain("{focus_position}"),
                                            validators.optional()])

    RET_set_image_size = StringField("RET_set_image_size", default='OK: VIDEO_RESOLUTION=''N{}x{}''')
    RET_set_zoom = StringField("RET_set_zoom", default='OK: OK: ZOOM=''DIRECT,{}''')
    RET_set_focus = StringField("RET_set_focus", default='OK: FOCUS=''DIRECT,{}''')
    RET_get_image_size = StringField("RET_get_image_size", default='VIDEO_RESOLUTION=''N{}x{}''')
    RET_get_zoom = StringField("RET_get_zoom", default='ZOOM_POSITION=''{}''')
    RET_get_focus = StringField("RET_get_focus", default='FOCUS_POSITION=''{}''')
    submit = SubmitField()


from pprint import pprint as print


@app.route("/reset-session")
def reset():
    session.clear()
    return str(session)


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


@app.route("/capture", methods=["GET", "POST"])
def capture_view():
    user_form = UserInputForm(request.form)
    try:
        lookup = [(idx, x) for idx, x in enumerate(session["camera_config"]["image_size_list"])]
        reverselookup = dict([(str(v), k) for k, v in lookup])
        user_form.image_size.choices = lookup
    except:
        pass
    if user_form.validate() and user_form.submit.data:
        print(user_form.data)
        for k in [x for x in vars(user_form) if not x.startswith("_") and not x == "meta"]:
            if k == "image_size":
                session["image_width"], session["image_height"] = user_form[k].data
            session[k] = user_form[k].data

    for k, v in session.items():
        try:
            user_form[k].data = v
        except:
            pass
    try:
        user_form.image_size.data = reverselookup[str(session.get("image_size"))]
    except:
        pass

    user_editable = ["1st_corner", "2nd_corner", "overlap", "scan_order", "image_height", "image_width"]
    template_data = {"form": user_form}

    return render_template("capture.html", **template_data)


def init_pano_overview():
    from PIL import Image, ImageDraw

    # get scalings for individual images
    scaled_height = int(session.get("overview_scale", 0.2) * session['image_height'])
    scaled_width = int(session.get("overview_scale", 0.2) * session["image_width"])

    # create overview image
    overview = Image.new("RGB", session.get("overview_shape", (1280, 720)), color="black")
    draw = ImageDraw.Draw(overview)

    # add lines shows rows and columns
    for i in range(session["pano_cols"]):
        pos = scaled_width * i
        coords = [pos, 0, pos, overview.size[1]]
        draw.line(coords, fill=255)
    for j in range(session["pano_rows"]):
        pos = scaled_height * j
        coords = [0, pos, overview.size[0], pos]
        draw.line(coords, fill=255)
    del draw
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "overview.jpg")
    try:
        overview.save(path, format="JPEG")
    except:
        return [{"message": "failed to properly overview file to {}".format(path),
                 "classsuffix": "warning"}]
    return []


@app.route("/api/calculate-grid", methods=["POST"])
def calculate_pano_grid():
    """
    calculates the panorama fov and grid.
    :return:
    """
    messages = []
    try:
        pan0, tilt0 = session['1st_corner']
        pan1, tilt1 = session['2nd_corner']
    except:
        # flash("First Corner or Second Corner not set. Aborting","error")
        return jsonify(messages=[{"message": "First Corner or Second Corner not set. Aborting",
                                  "classsuffix": "danger"}])

    if not (session.get("image_width", None) and session.get("image_height", None)):
        return jsonify(messages=[{"message": "No image width/height, set it first.",
                                  "classsuffix": "danger"}])

    HFoV = abs(float(pan0) - float(pan1))
    VFoV = abs(float(tilt0) - float(tilt1))

    if VFoV <= HFoV <= 2 * VFoV:
        session['HFoV'] = HFoV
        session['VFoV'] = VFoV
    else:
        return jsonify(messages=[{"message": "invalid Fov: h{} v{}".format(HFoV, VFoV),
                                  "classsuffix": "danger"}])

    lr = float(pan0) <= float(pan1)
    tb = float(tilt0) >= float(tilt1)

    pan_min = float(pan0) if lr else float(pan1)
    pan_max = float(pan0) if not lr else float(pan1)

    max_tilt = float(tilt0) if tb else float(tilt1)
    min_tilt = float(tilt0) if not tb else float(tilt1)
    print(max_tilt)
    print(min_tilt)
    session['top_left_corner'] = [pan_min, max_tilt]
    session['bottom_right_corner'] = [pan_max, min_tilt]
    session['pano_rows'] = int(round((max_tilt - min_tilt) / session['VFoV'] / (1.0 - session.get('overlap', 0))))
    session['pano_cols'] = int(round((pan_max - pan_min) / session['HFoV'] / (1.0 - session.get('overlap', 0))))
    session['pano_total'] = session['pano_rows'] * session['pano_cols']

    # Gigapan Sticher only works with 2000 images max
    if session['pano_total'] > 2000:
        messages.append({"message": 'Total number of images {} is more than {}'.format(session['pano_total'], 2000),
                         "classsuffix": "warning"})

    # todo: set panogridsize info values.

    if session['pano_rows'] >= 0 and session['pano_cols'] >= 0:
        scale = 2
        # todo: set image size info values here
        image_width, image_height = (session['image_width'], session['image_height'])
        while scale > 0:
            scaled_height = int(scale * image_height)
            scaled_width = int(scale * image_width)
            if scaled_height * session['pano_rows'] <= 1080 and \
                                    scaled_width * session['pano_cols'] <= 1920:
                break
            scale = scale - 0.001
        session["overview_scale"] = scale

        # session['PanoOverViewScale'] = scale
        # session['PanoOverViewHeight'] = scaled_height * session['pano_rows']
        # session['PanoOverViewWidth'] = scaled_width * session['pano_cols']


        # todo; return some updated infor about the state of the panorama variables in the session.
        overview_msgs = init_pano_overview()
        messages.extend(overview_msgs)
        # updatePanoOverView()
    else:
        return jsonify(messages=[
            {"message": "Invalid number of panorama rows or columns (you need at least 1 of each. Please try again.",
             "classsuffix": "warning"}])

    # todo: return some meaningful json values and represent them in the ui.
    messages.append({"message": 'successfully calculated the grid'.format(session['pano_total'], 2000),
                     "classsuffix": "danger"})
    return jsonify(messages=messages)


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
        "HTTP_login": str,
        "field_of_view": str,
        "overlap": float,
        "zoom": int,
        "focus": int,
        "first_corner": str,
        "second_corner": str,
        "use_focus_at_center": bool,
        "scan_order": int,
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
        "HTTP_login": str,
        "image_size_list": list,
        "horizontal_fov_list": list,
        "vertical_fov_list": list,
        "zoom_list_out": list,
        "zoom_pos": int,
        "zoom_range": list,
        "URL_set_image_size": str,
        "URL_set_zoom": str,
        "URL_set_focus": str,
        "URL_set_focus_mode": str,
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
            session[session_key + "_fn"] = filename if filename is not None else None

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


@app.route("/api/task-call/<func>", methods=['POST'])
def call_task(func):
    ftypes = {
        "take-panorama": celerypano.take_panorama
    }
    if func in ftypes.keys():
        task = ftypes[func].delay(session)
        return jsonify(callback="/api/task-info/{func}/{task_id}.json".format(func=func, task_id=task.id))
    else:
        return jsonify(message="404, no task by that name.", classsuffix="danger")


@app.route("/api/task-info/<func>/<task_id>.json")
def task_status(func, task_id):
    """
    gets the updates for a task from the id string.
    :param id:
    :return:
    """
    ftypes = {
        "take-panorama": celerypano.take_panorama
    }
    f = ftypes[func]
    task = f.AsyncResult(task_id)
    return jsonify(get_state_dict(task))


def get_state_dict(task):
    """
    gets a state dict for a given task
    :param task_id:
    :return:
    """
    no_chars = str.maketrans("", "", "<>/()[]")
    response = {
        "state": task.state,
        "class": "",
        "loading": "Loading...",
        "message": "No status message probably an error",
        "current": 0,
        "total": 1,
    }
    loadingd = {
        "SUCCESS": "Done!",
        "FAILURE": "Failed."
    }
    classsuffixdict = {
        "PENDING": "-info",
        "RECEIVED": "-info",
        "STARTED": "-info",
        "PROGRESS": "-default",
        "WARNING": "-warning",
        "SUCCESS": "-success",
        "FAILED": "-danger",
    }
    msgdict = {
        "PENDING": "Pending...",
        "RECEIVED": "Received by processing server...",
        "STARTED": "Started...",
    }

    if hasattr(task, 'info') and type(task.info) is dict:
        response['message'] = str(task.info.get('status', "").translate(no_chars).split(":")[-1].strip())
        response['current'] = task.info.get("current", 0)
        response['total'] = task.info.get("total", 1)

    response['message'] = msgdict.get(task.state, response['message'])
    response['classsuffix'] = classsuffixdict.get(task.state, "")
    response['loading'] = loadingd.get(task.state, response['loading'])
    return response


if __name__ == "__main__":
    app.run(threaded=True)

#
#
# def calculate_fov():
#     """
#     Calculates the horizontal and vertical field of view from the apps current
#     lineEditViewFirstCorner
#     lineEditViewSecondCorner
#     lineEditViewFirstCornerPixels
#     lineEditViewSecondCornerPixels
#     and the current image sizes
#     :return: (horizontal FoV, vertical FoV)
#     """
#     pan1, tilt1 = session['1st_corner']
#     pan2, tilt2 = session['2nd_corner']
#     try:
#         # todo: fix this
#         pan_pix1, tilt_pix1 = session['lineEditViewFirstCornerPixels'].split(",")
#         pan_pix2, tilt_pix2 = session['lineEditViewSecondCornerPixels'].split(",")
#         HFoV = abs(float(pan1) - float(pan2)) / \
#                abs(float(pan_pix1) - float(pan_pix2)) * session['image_width']
#         VFoV = abs(float(tilt1) - float(tilt2)) / \
#                abs(float(tilt_pix1) - float(tilt_pix2)) * session['image_height']
#     except:
#         HFoV = abs(float(pan1) - float(pan2))
#         VFoV = abs(float(tilt1) - float(tilt2))
#
#     if VFoV <= HFoV <= 2 * VFoV:
#         session['HFoV'] = HFoV
#         session['VFoV'] = VFoV
#     else:
#         flash("Invalid selection of field of view ({}, {})".format(
#             HFoV, VFoV), 'error')
#     return (HFoV, VFoV)
