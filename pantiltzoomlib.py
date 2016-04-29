# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
"""

import sys
import os, json
import random
from datetime import datetime
from io import BytesIO
from urllib import request as urllib
import numpy as np
import time
import re
import glob
import shutil
import csv
from xml.etree import ElementTree
from skimage import io
from skimage.feature import (match_descriptors, ORB, plot_matches)
from skimage.color import rgb2gray
from scipy.spatial.distance import hamming
from scipy import misc
import cv2
import yaml

with open("stardot_SECH10IR.yml", 'r') as f:
    cam_config = yaml.load(f.read())
with open("new_ptz_config_style.yml", 'r') as f:
    ptz_config = yaml.load(f.read())
with open("new_pano_config_style.yml", 'r') as f:
    pano_conf = yaml.load(f.read())


def draw_matches_opencv(img1, kp1, img2, kp2, matches):
    """
    Source: http://stackoverflow.com/questions/20259025/module-object-has-no-attribute-drawmatches-opencv-python
    This function takes in two images with their associated
    keypoints, as well as a list of DMatch data structure (matches)
    that contains which keypoints matched in which images.

    An image will be produced where a montage is shown with
    the first image followed by the second image beside it.

    Keypoints are delineated with circles, while lines are connected
    between matching keypoints.
    :param img1: grayscale image
    :param kp1: Detected list of keypoints through any of the OpenCV keypoint detection algorithms
    :param img2: grayscale image
    :param kp2: Detected list of keypoints through any of the OpenCV keypoint detection algorithms
    :param matches: A list of matches of corresponding keypoints through any OpenCV keypoint matching algorithm
    :return:
    """

    import cv2
    # define a taget height
    TARGETHEIGHT = 800

    # Create a new output image that concatenates the two images together
    # (a.k.a) a montage
    rows1 = img1.shape[0]
    cols1 = img1.shape[1]
    rows2 = img2.shape[0]
    cols2 = img2.shape[1]

    out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')

    # Place the first image to the left
    out[:rows1, :cols1, :] = np.dstack([img1, img1, img1])

    # Place the next image to the right of it
    out[:rows2, cols1:cols1 + cols2, :] = np.dstack([img2, img2, img2])
    ar = out.shape[1] / out.shape[0]
    w = int(TARGETHEIGHT * ar)
    # For each pair of points we have between both images
    # draw circles, then connect a line between them
    for mat in matches:
        # Get the matching keypoints for each of the images
        img1_idx = mat.queryIdx
        img2_idx = mat.trainIdx

        # x - columns
        # y - rows
        (x1, y1) = kp1[img1_idx].pt
        (x2, y2) = kp2[img2_idx].pt

        # Draw a small circle at both co-ordinates
        # radius 4
        # colour blue
        # thickness = 1
        cv2.circle(out, (int(x1), int(y1)), 4, (255, 0, 0), 1)
        cv2.circle(out, (int(x2) + cols1, int(y2)), 4, (255, 0, 0), 1)

        # Draw a line in between the two points
        # thickness = 3
        # colour red green blue
        cv2.line(out, (int(x1), int(y1)), (int(x2) + cols1, int(y2)),
                 (0, 0, 255), max(int(out.shape[0] / TARGETHEIGHT), 2))

    # rescale image here.

    out = cv2.resize(out, (w, TARGETHEIGHT))
    return out


def get_displacement_opencv(image0, image1):
    import cv2

    img1 = cv2.cvtColor(image0, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)

    # Create ORB detector with 1000 keypoints with a scaling pyramid factor of 1.2
    # gareth changed here from cv2.ORB to cv2.ORB_create for opencv3.1.0 compatibility.
    orb = cv2.ORB_create(1000, 1.2)

    # Detect keypoints
    (kp1, des1) = orb.detectAndCompute(img1, None)
    (kp2, des2) = orb.detectAndCompute(img2, None)

    # Create matcher and do matching
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    # Sort the matches based on distance.  Least distance
    # is better
    matches = sorted(matches, key=lambda val: val.distance)

    # collect displacement from the first 10 matches
    dx_list = []
    dy_list = []
    for mat in matches[:20]:
        # Get the matching keypoints for each of the images
        img1_idx = mat.queryIdx
        img2_idx = mat.trainIdx

        # x - columns
        # y - rows
        (x1, y1) = kp1[img1_idx].pt
        (x2, y2) = kp2[img2_idx].pt
        dx_list.append(abs(x1 - x2))
        dy_list.append(abs(y1 - y2))

    dx_median = np.median(np.asarray(dx_list, dtype=np.double))
    dy_median = np.median(np.asarray(dy_list, dtype=np.double))

    img3 = draw_matches_opencv(img1, kp1, img2, kp2, matches[:20])
    misc.imsave("matches.jpg", img3)
    return dx_median, dy_median


def get_displacement(image0, image1):
    image0_gray = rgb2gray(image0)
    image1_gray = rgb2gray(image1)
    descriptor_extractor = ORB(n_keypoints=200)

    descriptor_extractor.detect_and_extract(image0_gray)
    keypoints1 = descriptor_extractor.keypoints
    descriptors1 = descriptor_extractor.descriptors

    descriptor_extractor.detect_and_extract(image1_gray)
    keypoints2 = descriptor_extractor.keypoints
    descriptors2 = descriptor_extractor.descriptors

    matches12 = match_descriptors(descriptors1, descriptors2, cross_check=True)

    # Sort the matches based on distance.  Least distance
    # is better
    distances12 = []
    for match in matches12:
        distance = hamming(descriptors1[match[0]], descriptors2[match[1]])
        distances12.append(distance)

    indices = np.arange(len(matches12))
    indices = [index for (_, index) in sorted(zip(distances12, indices))]
    matches12 = matches12[indices]

    # collect displacement from the first 10 matches
    dx_list = []
    dy_list = []
    for mat in matches12[:10]:
        # Get the matching key points for each of the images
        img1_idx = mat[0]
        img2_idx = mat[1]

        # x - columns
        # y - rows
        (x1, y1) = keypoints1[img1_idx]
        (x2, y2) = keypoints2[img2_idx]
        dx_list.append(abs(x1 - x2))
        dy_list.append(abs(y1 - y2))

    dx_median = np.median(np.asarray(dx_list, dtype=np.double))
    dy_median = np.median(np.asarray(dy_list, dtype=np.double))
    # plot_matches(image0, image1, descriptors1, descriptors2, matches12[:10])
    return dx_median, dy_median


class Camera(object):
    """
    Camera abstraction. Should eventually allow gphoto2 cameras and webcams.
    """

    def __init__(self, ip=None, user=None, password=None, image_size=None, image_quality=100, config=None):
        self._image = None

        if not config:
            config = dict()
        config = config.copy()
        self._notified = []
        #
        # self._HTTP_login = config.pop("HTTP_login","USER={user}&PWD={password}").format(
        #     user = user or config.pop("username", "admin"),
        #     password = password or config.pop("password", "admin"))
        #
        # self._url = config.pop("format_url","http://{ip}{command}&{HTTP_login}").format(
        #     ip = ip or config.pop("ip", None),
        #     HTTP_login = self._HTTP_login)

        format_str = config.pop("format_url", "http://{HTTP_login}@{ip}{command}")

        if format_str.startswith("http://{HTTP_login}@"):
            format_str = format_str.replace("{HTTP_login}@", "")
            password_mgr = urllib.HTTPPasswordMgrWithDefaultRealm()

            password_mgr.add_password(None,
                                      format_str.replace("{command}", "").format(
                                          ip=ip or config.get("ip", "192.168.1.7")),
                                      user or config.pop("username", "admin"),
                                      password or config.pop("password", "admin"))
            auth_handler = urllib.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.build_opener(auth_handler)
            urllib.install_opener(opener)

        self._HTTP_login = config.pop("HTTP_login", "{user}:{password}").format(
            user=user or config.pop("username", "admin"),
            password=password or config.pop("password", "admin"))

        self._url = format_str.format(
            ip=ip or config.pop("ip", "192.168.1.7"),
            HTTP_login=self._HTTP_login,
            command="{command}")

        self._image_size_list = config.pop("image_size_list", [[1920, 1080], [1280, 720], [640, 480]])
        self._image_size = image_size or config.pop("image_size", self._image_size_list[0])
        image_quality = image_quality or config.pop("image_quality", 100)
        self._image_quality = image_quality
        self._focus_modes = config.get("focus_modes", ["AUTO", "MANUAL"])

        self._hfov_list = config.pop("horizontal_fov_list",
                                     [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126, 12.782, 9.217, 7.050,
                                      5.82])
        self._vfov_list = config.pop("vertical_fov_list",
                                     [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324, 7.7136, 4.787, 3.729,
                                      2.448])
        self._hfov = self._vfov = None
        self._zoom_list = config.pop("zoom_list", [50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000])
        self._zoom_position = config.pop("zoom_pos", 800)
        self._zoom_range = config.pop("zoom_range", [30, 1000])
        self._focus_range = config.pop("focus_range", [-float("inf"), float("inf")])

        # set commands from the rest of the config.
        self.commands = dict()
        self.parse_strings = dict()
        for k, v in config.items():
            if str(k).startswith("URL_"):
                self.commands[k] = v
            if str(k).startswith("RET_"):
                self.parse_strings[k] = v

        # set zoom position to fill hfov and vfov
        self.zoom_position = self._zoom_position

        print(self.status)
        self.image_quality = self.image_quality
        print(self.image_size)

    def _read_stream(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string
        :type command_string: str
        :param command_string: url to go to with parameters
        :return: string of data returned from the camera
        """
        url = self._url.format(*args, command=command_string, **kwargs)
        if "&" in url and "?" not in url:
            url = url.replace("&", "?", 1)
        # print(url)
        try:
            stream = urllib.urlopen(url)
        except urllib.URLError as e:
            print(e)
            return None
        return stream.read().strip()

    def _read_stream_raw(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string
        :type command_string: str
        :param command_string: url to go to with parameters
        :return: string of data returned from the camera
        """
        url = self._url.format(*args, command=command_string, **kwargs)
        if "&" in url and "?" not in url:
            url = url.replace("&", "?", 1)
        try:
            stream = urllib.urlopen(url)
        except urllib.URLError as e:
            print(e)
            return None
        return stream.read()

    def _get_cmd(self, cmd):
        cmd_str = self.commands.get(cmd, None)
        if not cmd_str and cmd_str not in self._notified:
            self._notified.append(cmd_str)
            print("No command available for \"{}\"".format(cmd))
            return None
        if type(cmd_str) == str:
            cmd_str = tuple(cmd_str.split("!"))
            if len(cmd_str) == 1:
                cmd_str = cmd_str[0]
        return cmd_str

    @staticmethod
    def get_value_from_xml(message_xml, *args):
        """
        gets float, int or string values from a xml string where the key is the tag of the first element with value as
        text.
        returns a dict if more than 1 arg.
        returns single value if 1 arg, or None if single arg not found in xml.
        :param message_xml:
        :param args: list of keys to find values for.
        :return:
        """
        assert (len(args) > 0, "No keys to search")
        root_element = ElementTree.fromstring(message_xml)
        return_values = {}
        for key in args:
            target_ele = root_element.find(key)
            if not target_ele:
                continue

            value = target_ele.text.replace(' ', '')
            if not value:
                continue

            types = [float, int, str]
            for t in types:
                try:
                    return_values[key] = t(value)
                except ValueError:
                    pass
            else:
                print("Couldnt cast an xml element text attribute to str. What are you feeding the xml parser?")

        # return single arg
        if len(args) == 1 and len(return_values) == 1:
            return next(iter(return_values.values()))
        elif len(args) == 1:
            return None
        return return_values

    @staticmethod
    def get_value_from_stream(raw_text, *args):
        """
        parses a string returned from the camera by urlopen into a list
        :type raw_text: str to be parsed
        :param text: text to parse
        :param args: string keys to select
        :return: list of values or None if input text has no '=' chars or dict of key values if args
        """
        if raw_text is None:
            raw_text = ""
        multitexts = raw_text.splitlines()
        multitexts = [x.decode().split("=") for x in multitexts]
        multitexts = dict([(x[0], x[-1]) for x in multitexts])

        if len(args):
            return dict((k, multitexts[k]) for k in args if k in multitexts.keys())

        values = []

        def ap(v):
            try:
                a = float(v)
                values.append(a)
            except:
                values.append(a)

        for k, value in multitexts.items():
            value = re.sub("'", "", value)
            if ',' in value:
                va = value.split()
                for v in va:
                    ap(v)
            else:
                ap(value)

        return values

    def capture(self, image_size=None, file_name=""):
        """
        captures an image.
        it returns an np.array of the image
        if file_name is a string, it will same the image to disk.
        if file_name is None, it will save the file with a temporary file name.
        if file_name is either a string or None it will return the filename, not a np.array

        :type file_name: None or str
        :type: image_size:  None or iter
        :param image_size: iterable of image size [width, height]
        :param file_name: file name to save as
        :return: numpy array, file name or None
        """
        cmd = self._get_cmd("URL_get_image")
        if not cmd:
            print("no capture command...")
            return self._image

        url = self._url.format(command=cmd)

        if file_name != "":
            try:

                filename, _ = urllib.urlretrieve(url, file_name)
                return filename
            except:
                return None
        try:
            # fast method
            a = self._read_stream_raw(cmd)
            b = np.fromstring(a, np.uint8)
            barry = cv2.imdecode(b, 1)
            self._image = barry
        except Exception as e:
            print(e)
            # fallback slow solution
            file_name = self.capture(file_name=None)
            self._image = cv2.imread(file_name, 1)
        return self._image

    @property
    def image_quality(self):
        """
        gets the image quality
        :return:
        """
        return self._image_quality

    @image_quality.setter
    def image_quality(self, value):
        """
        sets the image quality
        :param value: percentage value of image quality
        :return:
        """
        assert (1 <= value <= 100)
        cmd = self._get_cmd("URL_get_image_quality")
        if cmd:
            self._read_stream(cmd.format(value))

    @property
    def image_size(self):
        """
        gets the image resolution
        :return: image size
        """

        cmd = self._get_cmd("URL_get_image_size")
        if cmd:
            key = None
            if type(cmd) is tuple:
                cmd, key = cmd
            stream = self._read_stream(cmd)
            output = self.get_value_from_stream(stream, key)
            if type(output) is dict:
                output = output.get(key, None)
            else:
                return self._image_size
            if output:
                if type(output) is list:
                    self._image_size = output
                else:
                    self._image_size = self._image_size_list[int(output) % len(self._image_size_list)]
        return self._image_size

    @image_size.setter
    def image_size(self, value):
        """
        sets the image resolution
        :param image_size: iterable of len 2 (width, height)
        :return:
        """
        assert type(value) in (list, tuple), "image size is not a list or tuple!"
        assert len(value) == 2, "image size doesnt have 2 elements width,height are required"
        value = list(value)
        assert value in self._image_size_list, "image size not in available image sizes"
        cmd = self._get_cmd("URL_set_image_size")
        if cmd:
            self._read_stream(cmd.format(width=value[0], height=value[1]))
            self._image_size = value

    @property
    def zoom_position(self):
        """
        retrieves the current zoom position from the camera
        :return:
        """
        cmd = self._get_cmd("URL_get_zoom")
        if cmd:
            try:
                stream_output = self._read_stream(cmd)
                value = self.get_value_from_stream(stream_output)
                if value:
                    self._zoom_position = value
            except:
                pass

        self._hfov = np.interp(self._zoom_position, self.zoom_list, self.hfov_list)
        self._vfov = np.interp(self._zoom_position, self.zoom_list, self.vfov_list)
        return self._zoom_position

    @zoom_position.setter
    def zoom_position(self, absolute_value):
        """
        sets the camera zoom position to an absolute value
        :param absolute_value: absolute value to set zoom to
        :return:
        """
        cmd = self._get_cmd("URL_set_zoom")
        if cmd:
            assert (self._zoom_range is not None and absolute_value is not None)
            assert type(absolute_value) in (float, int)
            absolute_value = min(self._zoom_range[1], max(self._zoom_range[0], absolute_value))
            try:
                stream_output = self._read_stream(cmd.format(zoom=absolute_value))
                value = self.get_value_from_stream(stream_output)
                if value:
                    self._zoom_position = value
            except:
                pass
        else:
            self._zoom_position = absolute_value
        self._hfov = np.interp(self._zoom_position, self.zoom_list, self.hfov_list)
        self._vfov = np.interp(self._zoom_position, self.zoom_list, self.vfov_list)

    @property
    def zoom_range(self):
        """
        retrieves the available zoom range from the camera
        :return:
        """
        cmd = self._get_cmd("URL_get_zoom_range")
        if not cmd:
            return self._zoom_range
        stream_output = self._read_stream(cmd)
        v = self.get_value_from_stream(stream_output)
        if v:
            self._zoom_range = v
        return self._zoom_range

    @zoom_range.setter
    def zoom_range(self, value):
        assert type(value) in (list, tuple), "must be either list or tuple"
        assert len(value) == 2, "must be 2 values"
        self._zoom_range = list(value)

    @property
    def zoom_list(self):
        return self._zoom_list

    @zoom_list.setter
    def zoom_list(self, value):
        assert type(value) in (list, tuple), "Must be a list or tuple"
        assert len(value) > 1, "Must have more than one element"
        self._zoom_list = list(value)
        it = iter(self._hfov_list)
        self._hfov_list = [next(it, self._hfov_list[-1]) for _ in self._zoom_list]
        it = iter(self._vfov_list)
        self._vfov_list = [next(it, self._vfov_list[-1]) for _ in self._zoom_list]
        self.zoom_position = self._zoom_position

    @property
    def focus_mode(self):
        """
        retrieves the current focus mode from the camera
        :return:
        """
        cmd = self._get_cmd("URL_get_focus_mode")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        return self.get_value_from_stream(stream_output)

    @focus_mode.setter
    def focus_mode(self, mode):
        """
        sets the focus mode of the camera
        :type mode: str
        :param mode: focus mode of the camera. must be in self.focus_modes
        :return:
        """
        assert (self._focus_modes is not None)
        if mode.upper() not in self._focus_modes:
            print("Focus mode not in list of supported focus modes. YMMV.")
        cmd = self._get_cmd("URL_set_focus_mode")
        if cmd:
            self._read_stream(cmd.format(mode=mode.upper()))

    @property
    def focus_position(self):
        """
        retrieves the current focus position from the camera
        :return: focus position or None
        """
        cmd = self._get_cmd("URL_get_focus")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        result = self.get_value_from_stream(stream_output)
        return next(iter(result), float("inf"))

    @focus_position.setter
    def focus_position(self, absolute_position):
        """
        sets the camera focus position to an absolute value
        :param absolute_position: focus position to set the camera to
        :return:
        """
        cmd = self._get_cmd("URL_set_focus")
        if cmd:
            assert (self._focus_range is not None and absolute_position is not None)
            absolute_position = min(self._focus_range[1], max(self._focus_range[0], absolute_position))
            assert (self._focus_range[0] <= absolute_position <= self._focus_range[1])
            self._read_stream(format.format(focus=absolute_position))

    @property
    def focus_range(self):
        """
        retrieves a list of the focus type and range from the camera
        i.e. ["Motorized", 1029.0, 221.0]
        :return: [str:focus type, float:focus max, float:focus min]
        """
        cmd = self._get_cmd("URL_get_focus_range")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        values = self.get_value_from_stream(stream_output)
        return values[2:0:-1]

    @property
    def hfov_list(self):
        return self._hfov_list

    @hfov_list.setter
    def hfov_list(self, value):
        assert type(value) in (list, tuple), "must be either list or tuple"
        assert len(value) == len(self._zoom_list), "must be the same length as zoom list"
        self._hfov_list = list(value)

    @property
    def vfov_list(self):
        return self._vfov_list

    @vfov_list.setter
    def vfov_list(self, value):
        assert type(value) in (list, tuple), "must be either list or tuple"
        assert len(value) == len(self._zoom_list), "must be the same length as zoom list"
        self._vfov_list = list(value)

    @property
    def hfov(self):
        self._hfov = np.interp(self._zoom_position, self.zoom_list, self.hfov_list)
        return self._hfov

    @property
    def vfov(self):
        self._vfov = np.interp(self._zoom_position, self.zoom_list, self.vfov_list)
        return self._vfov

    @property
    def status(self):
        """
        helper function to get a string of the current status.
        :return: informative string of zoom_pos zoom_range focus_pos focus_range
        """
        fmt_string = "zoom_pos:\t{}\nzoom_range:\t{}"
        fmt_string = "".join((fmt_string, "\nfocus_pos:\t{}\nfocus_range:\t{}"))
        return fmt_string.format(self.zoom_position, self.zoom_range, self.focus_position, self.focus_range)

    def refocus(self):
        """
        forces a refocus of the the camera
        :return:
        """
        cmd = self._get_cmd("URL_set_focus_mode")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd.format(mode="REFOCUS"))
        return self.get_value_from_stream(stream_output)


class WebCamera(Camera):
    """
    webcamera class
    using cv2
    """

    def __init__(self, image_size=None):
        super().__init__(None)
        for x in range(0, 10):
            try:
                self.cam = cv2.VideoCapture(x)
                break
            except:
                continue
        else:
            raise SystemError("No cv2 camera available")

    def capture(self, image_size=None, file_name=""):
        """
        captures an image.
        with no params it returns a file like/np.array or an image at the default image size
        if file_name is a string, it will same the image to disk.
        if file_name is None, it will save the file with a temporary file name.
        if file_name is either a string or None it will return the filename, not a np.array

        :type file_name: None or str
        :type: image_size:  None or iter
        :param image_size: iterable of image size [width, height]
        :param file_name: file name to save as
        :return: numpy array, file name or None
        """
        if self._image_size_list:
            if image_size and image_size in self._image_size_list:
                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, image_size[0])
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, image_size[1])

        for _ in range(50):
            ret, im = self.cam.read()
            if ret:
                self._image = im
                break
            time.sleep(0.1)
        else:
            return None

        if file_name != "":
            try:
                misc.imsave(file_name, self._image)
                return file_name
            except:
                return None
        return self._image


class PanTilt(object):
    """
    Control J-Systems PTZ

    For new system or new firmware, the system needs calibration as follows:
    - Open URL of the PTZ on a web browser
    - Click on "Calibration" tab, enter username and password if necessary
    - On Calibration window, click on "Open-loop" and then "Set Mode"
    - Use joystick controller to rotate the pan axis to minimum position
    - Click on 'Pan Axis Min' line, enter '2.0', and click "Set Calibration"
    - Use joystick controller to rotate the pan axis to maximum position
    - Click on 'Pan Axis Max' line, enter '358.0', and click "Set Calibration"
    - Use joystick controller to rotate the tilt axis to minimum position
    - Click on 'Tilt Axis Min' line, enter '-90.0', and click "Set Calibration"
    - Use joystick controller to rotate the tilt axis to maximum position
    - Click on 'Tilt Axis Max' line, enter '30.0', and click "Set Calibration"
    - Click on "Closed-loop" and then "Set Mode"
    - Close Calibration window
    """

    def __init__(self, ip=None, user=None, password=None, config=None):
        if not config:
            config = dict()
        config = config.copy()

        self._notified = []
        format_str = config.pop("format_url", "http://{HTTP_login}@{ip}{command}")

        if format_str.startswith("http://{HTTP_login}@"):
            format_str = format_str.replace("{HTTP_login}@", "")

            password_mgr = urllib.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None,
                                      format_str.replace("{command}", "").format(
                                          ip=ip or config.get("ip", "192.168.1.101:81")),
                                      user or config.pop("username", "admin"),
                                      password or config.pop("password", "admin"))
            auth_handler = urllib.HTTPBasicAuthHandler(password_mgr)
            opener = urllib.build_opener(auth_handler)
            urllib.install_opener(opener)

        self._HTTP_login = config.pop("HTTP_login", "{user}:{password}").format(
            user=user or config.pop("username", "admin"),
            password=password or config.pop("password", "admin"))

        self._url = format_str.format(
            ip=ip or config.pop("ip", "192.168.1.101:81"),
            HTTP_login=self._HTTP_login,
            command="{command}")

        self._pan_tilt_scale = config.pop("pan_tilt_scale", 10.0)
        self._pan_range = list(config.pop("pan_range", [0, 360]))
        self._tilt_range = list(config.pop("tilt_range", [-90, 30]))

        self._pan_range.sort()
        self._tilt_range.sort()

        self._accuracy = config.pop("accuracy", 0.5)
        self._rounding = len(str(float(self._accuracy)).split(".")[-1].replace("0", ""))
        self.commands = dict()
        self.parse_strings = dict()
        for k, v in config.items():
            if str(k).startswith("URL_"):
                self.commands[k] = v
            if str(k).startswith("RET_"):
                self.parse_strings[k] = v

        time.sleep(0.2)

        print("pantilt:".format(self.position))

    def _read_stream(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string
        :type command_string: str
        :param command_string: url to go to with parameters
        :return: string of data returned from the camera
        """
        url = self._url.format(*args, command=command_string, **kwargs)
        if "&" in url and "?" not in url:
            url = url.replace("&", "?", 1)
        try:
            stream = urllib.urlopen(url)
        except urllib.URLError as e:
            print(e)
            return None
        return stream.read().strip()

    def _read_stream_raw(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string
        :type command_string: str
        :param command_string: url to go to with parameters
        :return: string of data returned from the camera
        """
        url = self._url.format(*args, command=command_string, **kwargs)
        if "&" in url and "?" not in url:
            url = url.replace("&", "?", 1)
        try:
            stream = urllib.urlopen(url)
        except urllib.URLError as e:
            print(e)
            return None
        return stream.read()

    def _get_cmd(self, cmd):
        cmd_str = self.commands.get(cmd, None)
        if not cmd_str and cmd_str not in self._notified:
            print("No command available for \"{}\"".format(cmd))
            self._notified.append(cmd_str)
            return None
        if type(cmd_str) == str:
            cmd_str = tuple(cmd_str.split("!"))
            if len(cmd_str) == 1:
                cmd_str = cmd_str[0]
        return cmd_str

    @staticmethod
    def get_value_from_xml(message_xml, *args):
        """
        gets float, int or string values from a xml string where the key is the tag of the first element with value as
        text.
        returns a dict if more than 1 arg.
        returns single value if 1 arg, or None if single arg not found in xml.
        :param message_xml:
        :param args: list of keys to find values for.
        :return:
        """
        assert (len(args) > 0, "No keys to search")
        # apparently, there is an issue parsing when the ptz returns INVALID XML (WTF?)
        # these seem to be the tags that get mutilated.
        illegal = [b'\n', b'\t', b'\r',
                   b"<CPStatusMsg>", b"</CPStatusMsg>", b"<Text>",
                   b"</Text>", b"<Type>Info</Type>", b"<Type>Info",
                   b"Info</Type>", b"</Type>", b"<Type>"]
        for ill in illegal:
            message_xml = message_xml.replace(ill, b"")

        root_element = ElementTree.Element("invalidation_tag")
        try:
            root_element = ElementTree.fromstring(message_xml)

        except Exception as e:
            print(str(e))
            print(message_xml)
            print("Couldnt parse XML")

        return_values = {}
        for key in args:
            target_ele = root_element.find(key)
            if target_ele is None:
                continue

            value = target_ele.text.replace(' ', '')
            if value is None:
                continue

            types = [float, int, str]
            for t in types:
                try:
                    return_values[key] = t(value)
                    break
                except ValueError:
                    pass
            else:
                print("Couldnt cast an xml element text attribute to str. What are you feeding the xml parser?")

        # return single arg
        if len(args) == 1 and len(return_values) == 1:
            return next(iter(return_values.values()))
        elif len(args) == 1:
            return None
        return return_values

    def pan_step(self, direction, n_steps):
        """
        pans by step, steps must be less than or equal to 127
        :type n_steps: int
        :type direction: str
        :param direction:
        :param n_steps: integer <= 127. number of steps
        :return:
        """
        assert (abs(n_steps) <= 127)
        cmd = self._get_cmd("URL_pan_step")
        if cmd and type(cmd) is tuple:
            amt = -n_steps if direction.lower() == "left" else n_steps
            cmd, key = cmd
            stream = self._read_stream(cmd.format(pan=amt))
            return self.get_value_from_xml(stream, key)
        return None

    def tilt_step(self, direction, n_steps):
        """
        tilts by step, steps must be less than or equal to 127
        :type n_steps: int
        :type direction: str
        :param direction:
        :param n_steps: integer <= 127. number of steps
        :return:
        """
        assert (abs(n_steps) <= 127)
        amt = -n_steps if direction.lower() == "down" else n_steps

        cmd = self._get_cmd("URL_tilt_step")
        if not cmd or type(cmd) is not tuple:
            return None

        cmd, key = cmd
        stream = self._read_stream(cmd.format(tilt=amt))

        return self.get_value_from_xml(stream, key)

    @property
    def position(self):
        """
        gets the current pan/tilt position.
        :return: tuple (pan, tilt)
        """
        cmd = self._get_cmd("URL_get_pan_tilt")
        if not cmd:
            return None
        keys = ["PanPos", "TiltPos"]
        if type(cmd) is tuple:
            cmd, keys = cmd[0], cmd[1:]

        output = self._read_stream(cmd)
        values = self.get_value_from_xml(output, *keys)
        p = tuple(values.get(k, None) for k in keys)
        if not any(p):
            return self._position
        else:
            self._position = p
        return self._position

    def _get_pos(self):
        cmd = self._get_cmd("URL_get_pan_tilt")
        if not cmd:
            return None
        keys = ["PanPos", "TiltPos"]
        if type(cmd) is tuple:
            cmd, keys = cmd[0], cmd[1:]

        output = self._read_stream(cmd)
        values = self.get_value_from_xml(output, *keys)
        p = tuple(values.get(k, None) for k in keys)
        if not any(p):
            return None
        return p

    @position.setter
    def position(self, position=(None, None)):
        """
        Sets the absolute pan/tilt position in degrees.
        float degree values are floored to int.
        :type position: tuple
        :param position: absolute degree value for pan,tilt as (pan,tilt)
        :return:
        """
        pan_degrees, tilt_degrees = position
        start_pos = self._get_pos()

        if not start_pos:
            return
        cmd = self._get_cmd("URL_set_pan_tilt")
        if not cmd:
            return
        if type(cmd) is tuple:
            cmd, keys = cmd[0], cmd[1:]

        if pan_degrees is None:
            pan_degrees = start_pos[0]
        if tilt_degrees is None:
            tilt_degrees = start_pos[1]

        pd = min(self._pan_range[1], max(self._pan_range[0], pan_degrees))
        td = min(self._tilt_range[1], max(self._tilt_range[0], tilt_degrees))
        diff = abs(self._position[0] - pd) + abs(self._position[1] - td)
        if diff <= self._accuracy:
            return

        if td != tilt_degrees or pd != pan_degrees:
            print("hit pantilt limit")
            print("{} [{}] {} ....... {} [{}] {}".format(
                self._pan_range[0], pan_degrees, self._pan_range[1],
                self._tilt_range[0], tilt_degrees, self._tilt_range[1]))

        pan_degrees, tilt_degrees = pd, td
        cmd = cmd.format(pan=pan_degrees * self._pan_tilt_scale,
                         tilt=tilt_degrees * self._pan_tilt_scale)

        self._read_stream(cmd)
        time.sleep(0.1)
        # loop until within 1 degree
        pan_pos, tilt_pos = None, None
        for _ in range(60):
            time.sleep(0.1)

            p = self._get_pos()
            if not p:
                continue
            pan_pos, tilt_pos = p
            pan_diff = abs(pan_pos - pan_degrees)
            tilt_diff = abs(tilt_pos - tilt_degrees)
            if pan_diff <= self._accuracy and tilt_diff <= self._accuracy:
                break
        else:
            print("Warning: pan-tilt fails to move to correct location")
            print("  Desired position: pan_pos={}, tilt_pos={}".format(
                pan_degrees, tilt_degrees))
            print("  Current position: pan_pos={}, tilt_pos={}".format(
                pan_pos, tilt_pos))

        # loop until smallest distance is reached
        for _ in range(0, 50):
            time.sleep(0.1)

            p = self._get_pos()
            if not p:
                continue
            pan_pos, tilt_pos = p

            pan_diff_new = abs(pan_pos - pan_degrees)
            tilt_diff_new = abs(tilt_pos - tilt_degrees)
            if pan_diff_new >= pan_diff or tilt_diff_new >= tilt_diff:
                break
            else:
                pan_diff = pan_diff_new
                tilt_diff = tilt_diff_new

        pn = self._position
        self._position = self.position
        print("moved {}° | {}°".format(round(pd-pn[0], self._rounding), round(td-pn[1], self._rounding)))

    @property
    def scale(self):
        return self._pan_tilt_scale

    @scale.setter
    def scale(self, value):
        self._pan_tilt_scale = value

    @property
    def pan(self):
        return self.position[0]

    @pan.setter
    def pan(self, value):
        self.position = (value, None)

    @property
    def pan_range(self):
        return self._pan_range

    @pan_range.setter
    def pan_range(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range = sorted(list(value))

    @property
    def tilt(self):
        return self.position[1]

    @tilt.setter
    def tilt(self, value):
        self.position = (None, value)

    @property
    def tilt_range(self):
        return self._tilt_range

    @tilt_range.setter
    def tilt_range(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._tilt_range = sorted(list(value))

    def hold_pan_tilt(self, state):
        """
        unknown, presumably holds the pan-tilt in one place.
        doesnt work...
        :param state: ? beats me.
        :return:
        """
        cmd_str = "/Calibration.xml?Action=0" if state is True else "/Calibration.xml?Action=C"
        output = self._read_stream(cmd_str)
        # apparently this was left here?
        print(output)
        return self.get_value_from_xml(output, "Text")

    @property
    def PCCWLS(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "PCCWLS")

    @property
    def PCWLS(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "PCWLS")

    @property
    def TDnLS(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "TDnLS")

    @property
    def TUpLS(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "TUpLS")

    @property
    def battery_voltage(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "BattV")

    @property
    def heater(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "Heater")

    @property
    def temp_f(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "Temp")

    @property
    def list_state(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "ListState")

    @property
    def list_index(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "ListIndex")

    @property
    def control_mode(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "CtrlMode")

    @property
    def auto_patrol(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "AutoPatrol")

    @property
    def dwell(self):
        output = self._read_stream("/CP_Update.xml")
        return self.get_value_from_xml(output, "Dwell")


class Panorama(object):
    def __init__(self, output_folder=None, prefix=None, camera=None, ptz=None, config=None):
        if not config:
            config = dict()
        config = config.copy()
        try:
            if not camera:
                camera_config_file = config.pop("camera_config_file", None)
                if camera_config_file:
                    with open(camera_config_file, 'r') as file:
                        cam_config = yaml.load(file.read())
                    camera = Camera(config=cam_config)
        except Exception as e:
            print("couldnt open config file: " + str(e))
            raise

        try:
            if not ptz:
                ptz_config_file = config.pop("ptz_config_file", None)
                if ptz_config_file:
                    with open(ptz_config_file, 'r') as file:
                        ptz_config = yaml.load(file.read())
                    ptz = PanTilt(config=ptz_config)
        except Exception as e:
            print("couldnt open config file: " + str(e))
            raise

        self._camera = camera
        if self._camera:
            print("Camera initialised")

        self._pantilt = ptz
        if self._pantilt:
            print("ptz initialised")

        self._output_folder = output_folder or config.pop("local_folder", "")
        # this is vital to create the output folder
        self.output_folder = self._output_folder
        self._prefix = prefix or config.pop("camera_name", "Gigavision default")

        self._image_overlap = float(config.pop("overlap", 50)) / 100
        self._seconds_per_image = 5

        self._config_csv = "default_gv_conf.csv"
        if not os.path.exists(self._config_csv):
            with open(self._config_csv, 'w') as file:
                file.write("image_index,pan_deg,tilt_deg,zoom_pos,focus_pos\n")

        self._recovery_filename = ".gv_recover.json"
        self._recovery_file = dict()
        if os.path.exists(os.path.join(os.getcwd(), self._recovery_filename)):
            with open(os.path.join(os.getcwd(), self._recovery_filename), "r") as file:
                self._recovery_file = json.loads(file.read())

        first_corner = config.pop("first_corner", [100, 20])
        second_corner = config.pop("second_corner", [300, -20])
        assert type(first_corner) in (list, tuple), "first corner must be a list or tuple"
        assert type(second_corner) in (list, tuple), "second corner must be a list or tuple"
        assert len(first_corner) == 2, "first corner must be of length 2"
        assert len(second_corner) == 2, "second corner must be of length 2"
        self._pan_range = sorted([first_corner[0], second_corner[0]])
        self._tilt_range = sorted([first_corner[1], second_corner[1]])
        self._pan_step = self._tilt_step = None
        self._pan_pos_list = self._tilt_pos_list = list()

        self._camera.focus_mode = "AUTO"

        scan_order_unparsed = config.pop("scan_order", "0")
        self._scan_order_translation = {
            'cols,right': 0,
            'cols,left': 1,
            'rows,down': 2,
            'rows,up': 3,
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3,
            0: 0,
            1: 1,
            2: 2,
            3: 3
        }
        self._scan_order_translation_r = {
            0: 'cols,right',
            1: 'cols,left',
            2: 'rows,down',
            3: 'rows,up'
        }
        self._scan_order = self._scan_order_translation.get(str(scan_order_unparsed).lower().replace(" ", ""), 0)
        print(self.summary)

    def set_current_as_first_corner(self):
        self.first_corner = self._pantilt.position

    def set_current_as_second_corner(self):
        self.second_corner = self._pantilt.position

    def enumerate_positions(self):
        """
        uses the currrent image overlap and camera fov to calculate a "grid" of pan and tilt positions
        :return:
        """
        self._pan_step = (1 - self._image_overlap) * self._camera.hfov
        self._tilt_step = (1 - self._image_overlap) * self._camera.vfov

        pan_start = self._pan_range[0]
        pan_stop = self._pan_range[1]
        tilt_start = self._tilt_range[0]
        tilt_stop = self._tilt_range[1]

        if self._scan_order == 1:
            # cols left
            pan_start, pan_stop = pan_stop, pan_start
            self._pan_step *= -1
        elif self._scan_order == 3:
            # rows up
            tilt_start, tilt_stop = tilt_stop, tilt_start
            self._tilt_step *= -1
        print("pan ", pan_start, " ", pan_stop)
        print("tilt ", tilt_start, " ", tilt_stop)
        # todo: verify this.
        # I think this is right?
        # self._pan_pos_list = np.arange(self._pan_range[0], self._pan_range[1], self._pan_step)
        # self._tilt_pos_list = np.arange(self._tilt_range[1], self._tilt_range[0] - self._tilt_step,
        #                                 -self._tilt_step)
        self._pan_pos_list = np.arange(pan_start, pan_stop, self._pan_step)
        self._tilt_pos_list = np.arange(tilt_start, tilt_stop, self._tilt_step)

    @property
    def summary(self):
        self.enumerate_positions()
        max_num_images = len(self._pan_pos_list) * len(self._tilt_pos_list)
        last_image_index = int(self._recovery_file.get("last_index", 0))
        s = ""
        s += "This panorama has {}(H) x {}(V) = {} images\n".format(
            len(self._pan_pos_list), len(self._tilt_pos_list), max_num_images)

        minutes, seconds = divmod(self._seconds_per_image * (max_num_images - last_image_index), 60)
        if last_image_index > 0:
            s += "RECOVERY AT {}\n".format(last_image_index)
        s += "This will complete in about {} min:{} sec\n".format(minutes, seconds)
        s += "pan_step = {} degree, tilt_step = {} degree\n".format(self._pan_step, self._tilt_step)
        return s

    @property
    def camera(self):
        return self._camera

    @camera.setter
    def camera(self, value):
        self._camera = value

    @property
    def pantilt(self):
        return self._pantilt

    @pantilt.setter
    def pantilt(self, value):
        self._pantilt = value

    @property
    def image_overlap(self):
        return self._image_overlap

    @image_overlap.setter
    def image_overlap(self, value):
        self._image_overlap = value

    @property
    def scan_order(self):
        return self._scan_order_translation_r.get(self._scan_order, "cols,right")

    @scan_order.setter
    def scan_order(self, value):
        self._scan_order = self._scan_order_translation.get(str(value).lower().replace(" ", ""), 0)

    @property
    def output_folder(self):
        return self._output_folder

    @output_folder.setter
    def output_folder(self, value):
        assert type(value) is str, "Set the output folder to a string"
        if not os.path.isdir(value):
            os.makedirs(value)
        self._output_folder = value

    @property
    def panorama_fov(self):
        return self._pan_range, self._tilt_range

    @panorama_fov.setter
    def panorama_fov(self, value):
        try:
            pan_fov, tilt_fov, pan_centre, tilt_centre = value
        except ValueError:
            raise ValueError("You must pass an iterable with the PanFov, TiltFov, PanCentre, TiltCentre")
        self._pan_range = [pan_centre - (pan_fov / 2), pan_centre + (pan_fov / 2)]
        self._tilt_range = [tilt_centre - (tilt_fov / 2), tilt_centre + (tilt_fov / 2)]
        self.enumerate_positions()

    @property
    def first_corner(self):
        return self._pan_range[0], self._tilt_range[1]

    @first_corner.setter
    def first_corner(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range[0], self._tilt_range[1] = value
        self.enumerate_positions()

    @property
    def center(self):
        return tuple((np.array(self.first_corner) + np.array(self.second_corner)) / 2)

    @property
    def second_corner(self):
        return self._pan_range[1], self._tilt_range[0]

    @second_corner.setter
    def second_corner(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range[1], self._tilt_range[0] = value
        self.enumerate_positions()

    @staticmethod
    def print_calibration(fovlists, test):
        s = u"{test_num}).\n\tHFOV:\n{havg:.2f}±{havar:.4f},\tσ: {hstdev}\n\tVFOV:\n{vavg:.2f}±{vavar:.4f},\tσ: {vstdev:.4f}\n"
        h, v = fovlist
        print(s.format(
                test_num=test,
                havg=np.average(h),
                havar=max(h) - min(h),
                hstdev=np.std(h),
                vavg=np.average(v),
                vavar=max(v) - min(v),
                vstdev=np.std(v)
            ))

    def test_calibration(self, number_of_tests):
        import random
        tests = dict((_, int(random.uniform(1, 4))) for _ in range(number_of_tests))

        for test, zooms in tests.items():
            pan_inc = random.uniform(-10, 10)
            tilt_inc = random.uniform(-10, 10)
            if random.uniform(0, 1) > 0.85:
                pan_inc = 0
            if random.uniform(0, 1) > 0.85:
                tilt_inc = 0

            fovlists = self.calibrate_fov_list(zoom_list=range(zooms),
                                                  pan_increment=pan_inc,
                                                  tilt_increment=tilt_inc)

            self.print_calibration(fovlists,n=test)


    def calibrate_fov_list(self, zoom_list=range(50, 1000, 100), panpos=None, tiltpos=None, pan_increment=1,
                           tilt_increment=0):
        """
        calibrates the Panorama on a list of zoom levels.
        :param zoom_list: list of zoom positions to calibrate
        :param panpos: pan position to calibrate
        :param tiltpos: tilt ""
        :param pan_increment: pan increment amount for the calibration
        :param tilt_increment: tilt ""
        :return:
        """
        camhfovlist = []
        camvfovlist = []
        self._camera.zoom_position = zoom_list[0] - 5
        time.sleep(1)
        curpos = self._pantilt.position
        panpos = panpos or curpos[0]
        tiltpos = tiltpos or curpos[1]
        for idx, zoompos in enumerate(zoom_list):
            print("Calibrating {}/{}".format(idx + 1, len(zoom_list)))
            self._camera.zoom_position = zoompos
            fovs = self.calibrate_fov(zoompos, panpos, tiltpos, pan_increment, tilt_increment)
            if fovs:
                camhfovlist.append(fovs[0])
                camvfovlist.append(fovs[1])
        time.sleep(1)
        self._pantilt.position = panpos, tiltpos
        return camhfovlist, camvfovlist

    def calibrate_fov(self, zoom_pos, pan_pos, tilt_pos, pan_increment, tilt_increment):
        """
        Capture images at different pan/tilt angles, then measure the pixel
        displacement between the images to estimate the field-of-view angle.
        :param zoom_pos: begin zoom position
        :param pan_pos: begin pan position
        :param tilt_pos: begin tilt position
        :param pan_increment: amount to increment pan by
        :param tilt_increment: "" ""
        :return:
        """

        self._camera.zoom_position = zoom_pos
        self._camera.capture()

        for tr in range(3):
            # add nearby position to reduce backlash
            self._pantilt.position = (pan_pos, tilt_pos)
            time.sleep(0.2)

            hfov_estimate = vfov_estimate = hfov = vfov = None
            reference_image = displaced_image = image2 = None
            reference_position = displacement = self._pantilt.position

            while True:
                image = self._camera.capture()
                if image is not None:
                    reference_image = image
                    break
            # capture image with pan motion
            for z in range(0, 900):
                i = z // 10
                self._pantilt.position = pan_pos + pan_increment * i, tilt_pos + tilt_increment * i
                # refocus
                self._camera.refocus()

                while True:
                    image = self._camera.capture()
                    if image is not None:
                        displaced_image = image
                        break
                if i == 0:
                    continue
                dx, dy = get_displacement_opencv(reference_image, displaced_image)
                if not dx or not dy:
                    # do next iteration becasue we cannot continue without dx or dy.
                    continue

                displacement = abs(self._pantilt.position[0] - reference_position[0]), abs(
                    self._pantilt.position[1] - reference_position[1])
                if abs(displacement[0] - (pan_increment * i)) > 1.0:
                    print("Displacement error {}".format(abs(displacement[0] - (pan_increment * i))))
                if abs(displacement[1] - (tilt_increment * i)) > 1.0:
                    print("Displacement error {}".format(abs(displacement[1] - (tilt_increment * i))))

                hfov_estimate = reference_image.shape[1] * displacement[0] / dx
                vfov_estimate = reference_image.shape[0] * displacement[1] / dy

                # old method of estimating fov
                # if pan_increment != 0:
                #     hfov_estimate = reference_image.shape[1] * pan_increment * i / dx
                # if tilt_increment != 0:
                #     vfov_estimate = reference_image.shape[0] * tilt_increment * i / dy
                if dx > 90 or dy > 90:
                    break
            else:
                # cant get initial guess.
                print("cant get initial guess")
                continue

            print("initial guess: ", (hfov_estimate, vfov_estimate))
            # reset ptz
            self._pantilt._position = pan_pos, tilt_pos
            time.sleep(0.1)

            # make an increment equal to 1/4 of FoV, we measure both of these now.
            quarter_pan_fov_estimate = 0.25 * hfov_estimate
            quarter_tilt_fov_estimate = 0.25 * vfov_estimate

            # ye olde method for posterity
            # if pan_increment != 0:
            #     quarter_pan_fov_estimate = 0.25 * hfov
            # else:
            #     quarter_pan_fov_estimate = 0.25 * vfov * reference_image.shape[1] / reference_image.shape[0]
            # no point in doing this....
            # if tilt_increment != 0:
            #     quarter_tilt_fov_estimate = 0.25 * vfov
            # else:
            #     quarter_tilt_fov_estimate = 0.25 * hfov * reference_image.shape[0] / reference_image.shape[1]

            self._pantilt.position = pan_pos + quarter_pan_fov_estimate, tilt_pos
            time.sleep(1)
            while True:
                # make sure camera finishes refocusing
                displaced_image = self._camera.capture()
                if displaced_image is not None:
                    break
            dx, dy = get_displacement_opencv(reference_image, displaced_image)
            if dx == 0 or dy == 0:
                print("couldnt get displacement for pan")
                continue

            displacement = abs(self._pantilt.position[0] - reference_position[0]), abs(
                self._pantilt.position[1] - reference_position[1])

            if abs(displacement[0] - quarter_pan_fov_estimate) > 1.0:
                print("Displacement error {}".format(abs(displacement[0] - quarter_pan_fov_estimate)))
            hfov = reference_image.shape[1] * displacement[0] / dx

            # ye olde methods of acquiring the fov from "asssumed, movement"
            # hfov = reference_image.shape[1] * quarter_pan_fov_estimate / dx
            # vfov = reference_image.shape[0] * quarter_tilt_fov_estimate / dy

            # do it again for vfov
            self._pantilt.position = pan_pos, tilt_pos + quarter_tilt_fov_estimate
            time.sleep(1)
            while True:
                # make sure camera finishes refocusing
                image2 = self._camera.capture()
                if image2 is not None:
                    break
            dx, dy = get_displacement_opencv(displaced_image, image2)
            if dx == 0 or dy == 0:
                print("couldnt get displacement for tilt")
                continue

            displacement = abs(self._pantilt.position[0] - reference_position[0]), abs(
                self._pantilt.position[1] - reference_position[1])

            if abs(displacement[1] - quarter_tilt_fov_estimate) > 1.0:
                print("Displacement error {}".format(abs(displacement[1] - quarter_tilt_fov_estimate)))
            vfov = reference_image.shape[0] * displacement[1] / dy

            print("final guess", (hfov, vfov))
            self._pantilt._position = pan_pos, tilt_pos
            time.sleep(1)
            return hfov, vfov

    @property
    def config_csv(self):
        if not os.path.isfile(self._config_csv):
            return None
        cfg = {"image_index": [], "pan_deg": [], "tilt_deg": [], "zoom_pos": [], "focus_pos": []}
        with open(self._config_csv) as file:
            csvread = csv.DictReader(file)
            for row in csvread:
                cfg["image_index"].append(int(row["image_index"]))
                cfg["pan_deg"].append(float(row["pan_deg"]))
                cfg["tilt_deg"].append(float(row["tilt_deg"]))
                cfg["zoom_pos"].append(int(row["zoom_pos"]))
                fp = row["focus_pos"]
                if fp == "None":
                    fp = self._camera.focus_position
                else:
                    fp = int(float(fp))

                cfg["focus_pos"].append(fp)
        return cfg

    @config_csv.setter
    def config_csv(self, value):
        if self._config_csv and os.path.isfile(self._config_csv):
            image_index, pan_pos, tilt_pos = value
            with open(self._config_csv, 'a') as File:
                File.write("{},{},{},{},{}\n".format(
                    image_index, pan_pos, tilt_pos,
                    self._camera.zoom_position,
                    self._camera.focus_position))

    @property
    def recovery_file(self):
        return self._recovery_file

    @recovery_file.setter
    def recovery_file(self, index):
        with open(self._recovery_filename, 'w') as file:
            data = {"cols": len(self._pan_pos_list),
                    "rows": len(self._tilt_pos_list),
                    "image_index": index,
                    "sec_per_image": self._seconds_per_image}
            file.write(json.dumps(data))

    def take_panorama(self):
        last_image_captured = 0
        cfg = self.config_csv
        now = datetime.now()
        start_time = time.time()
        focus_list = cfg.get("focus_pos", [])

        def cap(i, j, pan_pos, tilt_pos, image_index, lcap):
            self._pantilt.position = pan_pos, tilt_pos
            self._camera.refocus()

            if image_index < len(focus_list):
                self._camera.focus_position = focus_list[image_index]
                # todo: check to make sure that the camera returns a value
            time.sleep(0.1)

            self.config_csv = image_index, pan_pos, tilt_pos
            self.recovery_file = image_index

            for _ in range(0, 50):
                filename = os.path.join(self._output_folder,
                                        now.strftime("{pref}_%Y_%m_%d_%H_%M_00_00_{index:04}.jpg").format(
                                            pref=self._prefix, index=image_index))

                filename2 = self._camera.capture(file_name=filename)

                if filename2 == filename and os.path.getsize(filename) > 1000:
                    print("Wrote image {}".format(filename))
                    break
                else:
                    print("Warning: invalid image file size. Trying again.")
                    print("filename: {} - {}".format(filename, filename2))
                    time.sleep(0.1)
            else:
                print("failed capturing!")
                if os.path.exists(filename):
                    os.remove(filename)
                return lcap
            # update time per image
            current_time = time.time()
            lcap += 1
            self._seconds_per_image = (current_time - start_time) / lcap
            print("Time left: {}s".format(self._seconds_per_image))
            return lcap

        if self._scan_order in (1, 3):
            for j, tilt_pos in enumerate(self._tilt_pos_list):
                for i, pan_pos in enumerate(self._pan_pos_list):
                    image_index = i * len(self._tilt_pos_list) + j
                    if image_index < self.recovery_file.get("image_index", 0):
                        continue
                    last_image_captured = cap(i, j, pan_pos, tilt_pos, image_index, last_image_captured)
        else:
            for i, pan_pos in enumerate(self._pan_pos_list):
                for j, tilt_pos in enumerate(self._tilt_pos_list):
                    image_index = i * len(self._tilt_pos_list) + j
                    if image_index < self.recovery_file.get("image_index", 0):
                        continue
                    last_image_captured = cap(i, j, pan_pos, tilt_pos, image_index, last_image_captured)

        os.remove(self._recovery_filename)


pano = Panorama(config=pano_conf)

#
# def pano_demo(camera_ip,
#               camera_user,
#               camera_password,
#               pantilt_ip,
#               output_folder,
#               config_filename=None,
#               focus=None,
#               zoom=None, fov=None):
#     image_size = [1920, 1080]
#     #    Focus = 935
#     #    Zoom = 800  # 1050
#     zoom_list = range(50, 1100, 100)
#     camhfovlist = [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126, 12.782, 9.217, 7.050, 5.824]
#     camvfovlist = [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324, 7.7136, 4.787, 3.729, 2.448]
#
#     pan_range = [80, 200]
#     tilt_range = [-20, 20]
#     prefix = "pano-demo"
#
#     pano = Panorama(output_folder, prefix, camera_ip, camera_user, camera_password, pantilt_ip)
#     pano.image_size = image_size
#     pano.camera_zoom_list = zoom_list
#     pano.camera_hfov_list = camhfovlist
#     pano.camera_vfov_list = camvfovlist
#     pano.panorama_fov_range = (pan_range, tilt_range)
#     print("CamHFoV = {}, CamVFoV = {}".format(pano._camera.hfov, pano._camera.vfov))
#     if zoom is not None:
#         #        Pano.setZoom(Zoom)
#         pano.camera_fov_from_zoom = zoom
#     if focus is not None:
#         pano.focus = focus
#
#     if fov is not None:
#         pano.setCameraFoV(fov)
#     elif zoom is None and focus is None:
#         print("")
#
#     while True and os.path.exists(output_folder):
#         Config = None
#         if config_filename is not None:
#             with open(config_filename) as File:
#                 csvread = csv.DictReader(File)
#                 Config = {"ImgIndex": [], "PanDeg": [], "TiltDeg": [],
#                           "Zoom": [], "FocusPos": []}
#                 for row in csvread:
#                     Config["ImgIndex"].append(int(row["ImgIndex"]))
#                     Config["PanDeg"].append(float(row["PanDeg"]))
#                     Config["TiltDeg"].append(float(row["TiltDeg"]))
#                     Config["Zoom"].append(int(row["Zoom"]))
#                     Config["FocusPos"].append(int(float(row["FocusPos"])))
#
#         Now = datetime.now()
#         PanoFolder = os.path.join(output_folder,
#                                   Now.strftime("%Y"),
#                                   Now.strftime("%Y_%m"),
#                                   Now.strftime("%Y_%m_%d"),
#                                   Now.strftime("%Y_%m_%d_%H"))
#         RecoveryFilename = os.path.join(PanoFolder, "_data", "recovery.csv")
#         config_filename = os.path.join(PanoFolder, "_data", "config.csv")
#         if os.path.exists(RecoveryFilename):
#             with open(RecoveryFilename, "r") as File:
#                 # header "NoCols,NoRows,CurImgIndex,SecPerImg"
#                 try:
#                     line = File.readline()  # skip header
#                     line = File.readline()
#                     nums = [float(num) for num in line.split(",")]
#                 except:
#                     nums = None
#             if nums is not None and len(nums) == 4:
#                 RemainingSeconds = (nums[0] * nums[1] - nums[2]) * nums[3]
#                 if RemainingSeconds // 60 + int(Now.strftime("%M")) <= 60:
#                     # remove last file that may be corrupted
#                     FileList = glob.glob(
#                         os.path.join(PanoFolder, "{:04}.jpg".format(nums[2])))
#                     if len(FileList) > 0:
#                         for Filename in FileList:
#                             os.remove(Filename)
#
#                     pano.run(PanoFolder, last_image_index=nums[2], LastImageIndex=nums[2],
#                              recovery_filename=RecoveryFilename, config_filename=config_filename, config=Config)
#                     continue
#                 else:
#                     print("Found recovery data but it's too late to recover.")
#
#         Now = datetime.now()
#         PanoFolder = os.path.join(output_folder,
#                                   Now.strftime("%Y"),
#                                   Now.strftime("%Y_%m"),
#                                   Now.strftime("%Y_%m_%d"),
#                                   Now.strftime("%Y_%m_%d_%H"))
#         RecoveryFilename = os.path.join(PanoFolder, "_data", "recovery.csv")
#         config_filename = os.path.join(PanoFolder, "_data", "config.csv")
#         # run if finishing before the begining of the next o'clock
#         if int(Now.strftime("%M")) + pano.MaxNoImages * seconds_per_image // 60 <= 60:
#             print("Started recording new panorama at {}".format(PanoFolder))
#             #            Pano.test()
#             if os.path.exists(PanoFolder):
#                 shutil.rmtree(PanoFolder)
#             pano.run(PanoFolder, recovery_filename=RecoveryFilename, config_filename=config_filename,
#                      RecoveryFilename=RecoveryFilename, ConfigFilename=config_filename, config=Config)
#
#         Now = datetime.now()
#         RemainingMinutes = 60 - int(Now.strftime("%M"))
#         print("It's {}.".format(Now.strftime("%H:%M"))),
#         print("Wait for {} minutes before start.".format(RemainingMinutes))
#         time.sleep(RemainingMinutes * 60)

#
# if __name__ == "__main__":
#     Camera_IP = "192.168.1.100"
#     Camera_User = "Admin"
#     Camera_Password = "123456"
#     PanTil_IP = "192.168.1.101:81"
#     # On Raspberry Pi, run:
#     # $ mkdir /home/pi/Data/a_data
#     # $ sshfs chuong@percy.anu.edu.au:/network/phenocam-largedatasets/a_data /home/pi/Data/a_data
#     # and change OutputFolder
#     # OutputFolder = "/home/pi/Data/a_data/Gigavision/chuong_tests/"
#     OutputFolder = "/home/chuong/Data/a_data/Gigavision/chuong_tests/"
#     zoom = 800
#     #    ConfigFileName = "/home/chuong/Data/a_data/Gigavision/chuong_tests/2014/2014_12/2014_12_17/2014_12_17_18/_data/config.csv"
#     #    PanoDemo(Camera_IP, Camera_User, Camera_Password, PanTil_IP,
#     #             OutputFolder, Zoom=Zoom, ConfigFileName)
#     Focus = 935
#
#     pano_demo(Camera_IP, Camera_User, Camera_Password, PanTil_IP, OutputFolder, focus=Focus, Focus=Focus, zoom=zoom)
