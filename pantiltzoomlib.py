# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
@author: Gareth Dunstone, gareth.dunstone@anu.edu.au
"""

import sys
import os, json
from datetime import datetime
from io import BytesIO
import shutil
import logging, logging.config
import numpy as np
import time
import csv
import yaml
import tempfile
from libs.Uploader import Uploader
from libs.Updater import Updater
from libs.Camera import Camera, GPCamera, IPCamera
from libs.PanTilt import PanTilt
import cv2
import datetime
from schedule import Scheduler

logging.config.fileConfig("logging.ini")
logging.getLogger("paramiko").setLevel(logging.WARNING)


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
    """
    Gets displacement (in pixels I think) difference between 2 images using opencv
    :param image0: reference image
    :param image1: target image
    :return:
    """
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
    cv2.imwrite("matches.jpg", img3)
    del img1
    del img2
    return dx_median, dy_median


def get_displacement(image0, image1):
    """
    Gets displacement (in pixels I think) difference between 2 images using scikit-image
    not as accurate as the opencv version i think.
    :param image0: reference image
    :param image1: target image
    :return:
    """
    from skimage.feature import (match_descriptors, ORB, plot_matches)
    from skimage.color import rgb2gray
    from scipy.spatial.distance import hamming
    from scipy import misc
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


def sec2human(seconds)->str:
    """
    formats a timedelta object into semi-fuzzy human readable time periods.
    :param seconds: float or int
    :return: human readable string
    """
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]
    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            fmt_st = "{val} {name}" if period_value == 1 else "{val} {name}s"
            strings.append(fmt_st.format(val=period_value, name=period_name))
    return ", ".join(strings)


class Panorama(object):
    accuracy = 3

    def __init__(self, output_folder=None, camera=None, ptz=None, config=None, config_filename=None, queue=None):

        if not config:
            config = dict()
        if config_filename:
            config = yaml.load(open(config_filename).read())
        config = config.copy()
        self.name = config.get("name", "DEFAULT_PANO_NAME")
        self.logger = logging.getLogger(self.name)

        start_time_string = str(config.get('starttime', "0000"))
        start_time_string = start_time_string.replace(":", "")
        end_time_string = str(config.get('stoptime', "2359"))
        end_time_string = end_time_string.replace(":", "")
        start_time_string = start_time_string[:4]
        end_time_string = end_time_string[:4]

        assert end_time_string.isdigit(), "Non numerical start time, {}".format(str(end_time_string))
        self.begin_capture = datetime.datetime.strptime(start_time_string, "%H%M").time()

        assert end_time_string.isdigit(), "Non numerical start time, {}".format(str(end_time_string))
        self.end_capture = datetime.datetime.strptime(end_time_string, "%H%M").time()

        self.interval = config.get("interval", 3600)
        camera = None
        ptz = None
        try:
            while not camera:
                camera_config = config.pop("camera", None)
                if not camera_config:
                    raise ValueError("No 'camera' section found in config file.")

                if camera_config == "DSLR":
                    camera = GPCamera(queue=queue)
                elif type(camera_config) is dict:
                    camera = IPCamera(self.name+"-cam", config=camera_config, queue=queue)
        except Exception as e:
            self.logger.error("Couldnt initialise Camera: " + str(e))
            time.sleep(30)
            camera = None

        self._camera = camera
        if self._camera:
            fov = config.pop("camera_fov", None)
            if fov:
                self._camera.hfov, self._camera.vfov = fov
            self.logger.debug("Camera initialised")

        while not ptz:
            try:
                ptz_config = config.pop("ptz", None)
                if not ptz_config:
                    raise ValueError("No 'ptz' section found in config file.")
                ptz = PanTilt(config=ptz_config, queue=queue)
                self.logger.debug("ptz initialised")
            except Exception as e:
                self.logger.error("Couldnt initialise PTZ: " + str(e))
                time.sleep(30)
                ptz = None

        self._pantilt = ptz

        self._output_dir = output_folder or config.pop("output_dir", "")
        self._spool_dir = tempfile.mkdtemp(prefix=self.name)
        self.output_dir = self._output_dir
        # this is vital to create the output folder

        self._image_overlap = float(config.pop("overlap", 50)) / 100
        self._seconds_per_image = 5
        self._csv_log = None
        self._recovery_filename = ".gv_recover.json"
        self._recovery_file = dict(image_index=0)
        try:
            if os.path.exists(os.path.join(os.getcwd(), self._recovery_filename)):
                with open(os.path.join(os.getcwd(), self._recovery_filename), "r") as file:
                    self._recovery_file = json.loads(file.read())
        except:
            with open(os.path.join(os.getcwd(), self._recovery_filename), "w+") as f:
                f.write("{}")
                f.seek(0)
                self._recovery_file = json.loads(f.read())

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
        self.logger.info(self.summary)

    def set_current_as_first_corner(self):
        """
        This and set_current_as_second_corner, both internally call enumerate positions, so
        :return:
        """
        self.first_corner = self._pantilt.position

    def set_current_as_second_corner(self):
        """

        :return:
        """
        self.second_corner = self._pantilt.position

    def enumerate_positions(self):
        """
        uses the currrent image overlap and camera fov to calculate a "grid" of pan and tilt positions
        :return:
        """
        self.logger.debug("Enumerating positions")
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
        # todo: verify this.
        # I think this is right?
        # self._pan_pos_list = np.arange(self._pan_range[0], self._pan_range[1], self._pan_step)
        # self._tilt_pos_list = np.arange(self._tilt_range[1], self._tilt_range[0] - self._tilt_step,
        #                                 -self._tilt_step)
        self._pan_pos_list = np.arange(pan_start, pan_stop, self._pan_step)
        self._tilt_pos_list = np.arange(tilt_start, tilt_stop, self._tilt_step)

        self.logger.debug("pan {}-{}".format(pan_start, pan_stop))
        self.logger.debug("tilt {}-{}".format(tilt_start, tilt_stop))

    @property
    def summary(self)->str:
        self.enumerate_positions()
        max_num_images = len(self._pan_pos_list) * len(self._tilt_pos_list)
        last_image_index = int(self._recovery_file.get("image_index", 0))
        s = "\n"
        s += "----- PANO SUMMARY -----\n"
        s += "This panorama has {}(H) x {}(V) = {} images\n".format(
            len(self._pan_pos_list), len(self._tilt_pos_list), max_num_images)
        s += "Camera fov {0:.2f}|{1:.2f}\n".format(self.camera.hfov, self.camera.vfov)

        minutes, seconds = divmod(self._seconds_per_image * (max_num_images - last_image_index), 60)
        if last_image_index > 0:
            s += "RECOVERY AT {}\n".format(last_image_index)
        s += "This will complete in approx {0:.2f} min {1:.2f} sec\n".format(minutes, seconds)
        s += "pan step = {0:.3f} deg, tilt step = {1:.3f} deg\n".format(self._pan_step, self._tilt_step)
        s += "------------------------\n"
        return s

    @property
    def camera(self)->Camera:
        return self._camera

    @camera.setter
    def camera(self, value: Camera):
        self._camera = value

    @property
    def pantilt(self) ->PanTilt:
        return self._pantilt

    @pantilt.setter
    def pantilt(self, value: PanTilt):
        self._pantilt = value

    @property
    def image_overlap(self):
        return self._image_overlap

    @image_overlap.setter
    def image_overlap(self, value):
        self._image_overlap = value

    @property
    def scan_order(self)->str:
        return self._scan_order_translation_r.get(self._scan_order, "cols,right")

    @scan_order.setter
    def scan_order(self, value: str):
        self._scan_order = self._scan_order_translation.get(str(value).lower().replace(" ", ""), 0)

    @property
    def output_dir(self)->str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: str):
        assert type(value) is str, "Set the output folder to a string"
        if not os.path.isdir(value):
            os.makedirs(value)
        self._output_dir = value

    @property
    def panorama_fov(self)->tuple:
        """
        Gets the total fov of the Panorama.
        :return:
        """
        return self._pan_range, self._tilt_range

    @panorama_fov.setter
    def panorama_fov(self, value: tuple):
        """
        sets the pan range and tilt range of the panorama using the fov, and centre points
        :param value: 4 length tuple of pan_fov, tilt_fov, pan_centre, tilt_centre
        :return:
        """
        try:
            pan_fov, tilt_fov, pan_centre, tilt_centre = value
        except ValueError:
            raise ValueError("You must pass an iterable with the PanFov, TiltFov, PanCentre, TiltCentre")
        self._pan_range = [pan_centre - (pan_fov / 2), pan_centre + (pan_fov / 2)]
        self._tilt_range = [tilt_centre - (tilt_fov / 2), tilt_centre + (tilt_fov / 2)]
        self.enumerate_positions()

    @property
    def first_corner(self)->tuple:
        return self._pan_range[0], self._tilt_range[1]

    @first_corner.setter
    def first_corner(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range[0], self._tilt_range[1] = value
        self.enumerate_positions()

    @property
    def center(self)->tuple:
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
    def format_calibration(fovlists: tuple, test: str)->str:
        """
        formats a list of calibrated tuple of lists of fields of view and gives some statistics about the measurements.
        :param fovlists: 2 length tuple of lists of hfov and vfov - tuple(list(hfov), list(vfov))
        :param test: prefix
        :return:
        """
        s = u"\n{test_num}).\n\tHFOV:\n{havg:.2f}±{havar:.4f},\tσ: {hstdev}\n\tVFOV:\n{vavg:.2f}±{vavar:.4f},\tσ: {vstdev:.4f}\n"
        h, v = fovlists
        return s.format(
            test_num=test,
            havg=np.average(h),
            havar=max(h) - min(h),
            hstdev=np.std(h),
            vavg=np.average(v),
            vavar=max(v) - min(v),
            vstdev=np.std(v)
        )

    def test_calibration(self, number_of_tests: int):
        """
        tests the calibration process
        :param number_of_tests:
        :return:
        """
        import random
        self.logger.info("Testing {} times".format(number_of_tests))

        # tests = dict((_, int(random.uniform(1, 4))) for _ in range(number_of_tests))
        def get_unif():
            a = random.uniform(2, 2)
            while abs(a) < 1:
                a = random.uniform(2, 2)
            return a

        tests = {_: 2 for _ in range(number_of_tests)}

        self._pantilt.position = np.mean(self._pantilt.pan_range), 0

        for test, inc in tests.items():
            self.logger.info("Testing with opencv {}".format(test))
            fovlists = self.calibrate_fov_list(increment=inc)
            self.logger.info(self.format_calibration(fovlists, test))
            self._pantilt._position = np.mean(self._pantilt.pan_range), 0
            self.logger.info("Testing without opencv {}".format(test))
            fovlists = self.calibrate_fov_list(increment=inc, use_opencv=False)

            self.logger.info(self.format_calibration(fovlists, test))
        self._pantilt.position = np.mean(self._pantilt.pan_range), 0

    def calibrate_fov_list(self,
                           zoom_list: list=range(50, 1000, 100),
                           panpos: float=None,
                           tiltpos: float=None,
                           increment: float=2,
                           use_opencv: bool=True)->tuple:
        """
        calibrates the Panorama on a list of zoom levels.
        :param zoom_list: list of zoom positions to calibrate
        :param panpos: pan position to calibrate
        :param tiltpos: tilt ""
        :param increment: pan increment amount for the calibration
        :param use_opencv: whether to use opencv
        :return: 2 length tuple of lists of hfov and vfov - tuple(list(hfov), list(vfov))
        """
        camhfovlist = []
        camvfovlist = []
        self._pantilt.zoom_position = zoom_list[0] - 5
        time.sleep(1)
        curpos = self._pantilt.position
        panpos = panpos or curpos[0]
        tiltpos = tiltpos or curpos[1]
        for idx, zoompos in enumerate(zoom_list):
            self._pantilt._position = np.mean(self._pantilt.pan_range), 0
            self.logger.info("Calibrating {}/{}".format(idx + 1, len(zoom_list)))
            self._pantilt.zoom_position = zoompos
            time.sleep(1)
            hf, vf = self.calibrate_fov(zoompos, panpos, tiltpos, increment, use_opencv=use_opencv)

            if hf and vf:
                camhfovlist.append(hf)
                camvfovlist.append(vf)
        time.sleep(1)
        self._pantilt.position = panpos, tiltpos
        return camhfovlist, camvfovlist

    def calibrate_fov(self,
                      zoom_pos: float,
                      pan_pos: float,
                      tilt_pos: float,
                      increment: float,
                      use_opencv: bool=True)->tuple:
        """
        Capture images at different pan/tilt angles, then measure the pixel
        displacement between the images to estimate the field-of-view angle.
        :param zoom_pos: begin zoom position
        :param pan_pos: begin pan position
        :param tilt_pos: begin tilt position
        :param increment: amount to increment to get displacement.
        :param use_opencv: Whether to use opencv or scikit image for displacement algorithm
        :return: tuple of hfov, vfov estimates
        """

        self._pantilt.zoom_position = zoom_pos
        self._camera.capture()
        hestimates = []
        vestimates = []
        # add nearby position to reduce backlash
        self._pantilt.position = (pan_pos, tilt_pos)
        time.sleep(0.2)

        hfov_estimate = vfov_estimate = hfov = vfov = None
        reference_image = displaced_image = None
        reference_position = self._pantilt.position

        while True:
            reference_image = self._camera.capture()
            if reference_image is not None:
                reference_image = reference_image
                break

        def reject_outliers(data, m=2.):
            try:
                d = np.abs(data - np.median(data))
                mdev = np.median(d)
                s = d / mdev if mdev else 0.
                return data[s < m]
            except:
                self.logger.error("Error rejecting outliers")
                return data

        def measure(movement: float) -> tuple:
            movement = (movement, movement)
            displ_image = None
            self._pantilt.position = pan_pos, tilt_pos
            pos = self._pantilt.position

            position = (pos[0] + movement[0], pos[1] + movement[1])

            # print("Measuring at {}|{}".format(*position))
            self._pantilt.position = position
            time.sleep(0.25)
            while True:
                # make sure camera finishes refocusing
                displ_image = self._camera.capture()
                if displ_image is not None:
                    break

            if use_opencv:
                dx, dy = get_displacement_opencv(reference_image, displ_image)
            else:
                dx, dy = get_displacement(reference_image, displ_image)

            assert dx != 0 and dy != 0, "Couldn't get displacement"

            dxp = dx / reference_image.shape[1]
            dyp = dy / reference_image.shape[0]
            if dxp > 0.35 or dyp > 0.35:
                return None, None

            ptzpos = self._pantilt.position

            displacement = abs(ptzpos[0] - reference_position[0]), abs(ptzpos[1] - reference_position[1])

            if abs(displacement[0] - movement[0]) > 1.0:
                self.logger.error("Displacement error pan {0:.4f}".format(abs(displacement[0] - movement[0])))
            if abs(displacement[1] - movement[1]) > 1.0:
                self.logger.error("Displacement error tilt {0:.4f}".format(abs(displacement[1] - movement[1])))

            hfovt = reference_image.shape[1] * displacement[0] / dx
            vfovt = reference_image.shape[0] * displacement[1] / dy
            self.logger.debug("Guess: {0:.3f}|{1:.3f}".format(hfovt, vfovt))
            return hfovt, vfovt

        hestimates = []
        vestimates = []

        for a in np.arange(1, 20, 0.25):
            h, v = measure(a * increment)
            if not all((h, v)):
                break
            hestimates.append(h)
            vestimates.append(v)
        else:
            self.logger.error("probably very wrong calibration for some reason")
            return None, None

        lh, lv = len(hestimates), len(vestimates)
        hestimates, vestimates = reject_outliers(np.array(hestimates)), reject_outliers(np.array(vestimates))
        self.logger.info("removed outliers: h{} v{} ".format(lh-len(hestimates), lv-len(vestimates)))
        hfov_estimate, vfov_estimate = np.mean(hestimates), np.mean(vestimates)

        self.logger.info(Panorama.format_calibration((hestimates, vestimates), "This guess: "))

        self._pantilt._position = np.mean(self._pantilt.pan_range), 0
        time.sleep(1)
        return hfov_estimate, vfov_estimate


    def quick_calibrate(self, increment):
        h, v = self.calibrate_fov(self._pantilt._zoom_position, float(np.mean(self._pan_range)),float(np.mean(self._tilt_range)), increment=increment)
        self._pantilt.zoom_list = [0]
        self._camera.vfov_list = [v]
        self._camera.hfov_list = [h]
        self._camera.hfov = h
        self._camera.vfov = v

    def _init_csv_log(self, path: str):
        self._csv_log = path
        if not os.path.exists(self._csv_log):
            with open(self._csv_log, 'w') as file:
                file.write("image_index,pan_deg,tilt_deg,zoom_pos,focus_pos\n")

    @property
    def csv_log(self)->dict:
        if not os.path.isfile(self._csv_log):
            self._init_csv_log(self._csv_log)
        cfg = {"image_index": [], "pan_deg": [], "tilt_deg": [], "zoom_pos": [], "focus_pos": []}
        with open(self._csv_log) as file:
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

    @csv_log.setter
    def csv_log(self, value: tuple):
        if self._csv_log and os.path.isfile(self._csv_log):
            image_index, pan_pos, tilt_pos = value
            with open(self._csv_log, 'a') as File:
                File.write("{},{},{},{},{}\n".format(
                    image_index, pan_pos, tilt_pos,
                    self._pantilt.zoom_position,
                    self._camera.focus_position))

    @property
    def recovery_file(self)->dict:
        return self._recovery_file

    @recovery_file.setter
    def recovery_file(self, data: tuple):
        index, started_time = data
        self._recovery_file['image_index'] = index
        with open(self._recovery_filename, 'w') as file:
            data = {"cols": len(self._pan_pos_list),
                    "rows": len(self._tilt_pos_list),
                    "image_index": index,
                    "sec_per_image": self._seconds_per_image,
                    "started_time": started_time}
            file.write(json.dumps(data))

    def take_panorama(self):
        ts_fmt = "%Y_%m_%d_%H_%M_00_00"
        last_image_captured = 0
        now = datetime.datetime.now()

        self.logger.debug("Moving to center to focus...")
        self._pantilt.position = np.mean(self._pan_range), np.mean(self._tilt_range)
        time.sleep(1)
        self._camera.focus()
        time.sleep(1)
        last_started = self.recovery_file.get('started_time', None)
        if last_started:
            last_started = datetime.datetime.strptime(last_started, ts_fmt)
            if int(now.timestamp())-int(last_started.timestamp()) < self.interval:
                now = last_started
            else:
                self.logger.warning("Recovery exists, but its now too late. Starting from beginning.")
                self.recovery_file = 0, now.strftime(ts_fmt)
        this_dir = os.path.join(self._output_dir, now.strftime("%Y_%m_%d_%H"))
        os.makedirs(this_dir, exist_ok=True)

        self._csv_log = now.strftime("{name}-"+ts_fmt+".csv").format(name=self.name)
        cfg = self.csv_log
        focus_list = cfg.get('focus_pos', [])

        start_time = time.time()
        # this is just here in case you want to update overview.jpg
        # im1 = cv2.resize(self.camera.capture(), None, fx=0.1, fy=0.1)
        # overview = np.zeros((im1.shape[0]*len(self._tilt_pos_list),
        #                      im1.shape[1]*len(self._pan_pos_list),
        #                      3), np.uint8)
        # cv2.imwrite("overview.jpg", overview)

        def cap(_i: int, _j: int, _pan_pos: float, _tilt_pos: float, _image_index: int, lcap: int)->int:
            self._pantilt.position = _pan_pos, _tilt_pos
            time.sleep(0.1)

            self.csv_log = _image_index, _pan_pos, _tilt_pos
            self.recovery_file = _image_index, now.strftime(ts_fmt)
            for _ in range(0, 15):
                filename = os.path.join(self._spool_dir,
                                        now.strftime("{name}_"+ts_fmt+"_{index:04}").format(name=self.name,
                                                                                            index=_image_index+1))
                try:
                    output_filenames = list(self._camera.capture(filename=filename))
                    # output_filenames = self._camera.capture_monkey(filename=filename)
                    self.camera.communicate_with_updater()
                    if type(output_filenames) is list and len(output_filenames):
                        # image = cv2.resize(self.camera.image.copy(),
                        #                    None, fx=0.1, fy=0.1,
                        #                    interpolation=cv2.INTER_NEAREST)

                        # yoff = _i * image.shape[0]
                        # xoff = _j * image.shape[1]
                        # overview[yoff:yoff+image.shape[0], xoff:xoff+image.shape[1]] = image
                        # cv2.imwrite("overview.jpg", overview)
                        for f in output_filenames:
                            shutil.move(f, os.path.join(this_dir, os.path.basename(f)))
                        self.logger.info("wrote image {}/{}".format(_image_index+1,
                                                                    (len(self._pan_pos_list) * len(self._tilt_pos_list))))
                        lcap += 1
                        # update time per image
                        current_time = time.time()
                        self._seconds_per_image = (current_time - start_time) / lcap
                        self.logger.info("Seconds per image {0:.2f}s".format(self._seconds_per_image))
                        return lcap
                except Exception as e:
                    self.logger.error("Bad things happened: {}".format(str(e)))
            else:
                self.logger.error("failed capturing!")
                return lcap


        # reverse it because we should start from top and go down
        tilt_pos_list = list(reversed(self._tilt_pos_list))
        pan_pos_list = self._pan_pos_list
        if self.scan_order == 1:
            # cols left
            pan_pos_list = self._pan_pos_list
            tilt_pos_list = list(reversed(self._tilt_pos_list))
        elif self.scan_order == 3:
            # rows up
            tilt_pos_list = self._tilt_pos_list
            pan_pos_list = list(reversed(self._pan_pos_list))
        recovery_index = self.recovery_file.get('image_index', 0)

        if self._scan_order >= 2:
            for i, tilt_pos in enumerate(tilt_pos_list):
                for j, pan_pos in enumerate(pan_pos_list):
                    image_index = i * len(pan_pos_list) + j
                    if image_index < recovery_index:
                        continue
                    last_image_captured = cap(i, j, pan_pos, tilt_pos, image_index, last_image_captured)

        else:
            for j, pan_pos in enumerate(pan_pos_list):
                for i, tilt_pos in enumerate(tilt_pos_list):
                    image_index = j * (len(tilt_pos_list)) + i
                    if image_index < recovery_index:
                        continue
                    last_image_captured = cap(i, j, pan_pos, tilt_pos, image_index, last_image_captured)

        shutil.move(self._csv_log, os.path.join(self._output_dir, os.path.basename(self._csv_log)))
        os.remove(self._recovery_filename)
        self._recovery_file['image_index'] = 0
        self.logger.info("Panorama complete in {}".format(sec2human(time.time() - start_time)))

    def calibrate_and_run(self):
        self._pantilt.position = np.mean(self._pantilt.pan_range), 0
        fovlists = self.calibrate_fov_list(zoom_list=list(range(2)), increment=2)

        self.logger.info("Calibration complete")
        self.logger.info(Panorama.format_calibration(fovlists, "Calibration results: "))
        h, v = fovlists
        try:
            self._camera.zoom_list = list(range(2))
            self._camera.vfov_list = v
            self._camera.hfov_list = h
            self._camera.hfov = np.mean(h)
            self._camera.vfov = np.mean(v)
            self.enumerate_positions()
            self.logger.info(self.summary)
        except Exception as e:
            self.logger.error(str(e))
        self.take_panorama()

    def run_from_config(self):
        self.logger.info(self.summary)
        self.take_panorama()

    @staticmethod
    def time2seconds(t: datetime.datetime)->int:
        """
        converts a datetime to an integer of seconds since epoch
        """
        try:
            return int(t.timestamp())
        except:
            # only implemented in python3.3
            # this is an old compatibility thing
            return t.hour * 60 * 60 + t.minute * 60 + t.second

    def time_to_capture(self):
        """
        filters out times for capture, returns True by default
        returns False if the conditions where the camera should NOT capture are met.
        :return:
        """
        current_capture_time = datetime.datetime.now()
        current_naive_time = current_capture_time.time()

        if self.begin_capture < self.end_capture:
            # where the start capture time is less than the end capture time
            if not self.begin_capture <= current_naive_time <= self.end_capture:
                return False
        else:
            # where the start capture time is greater than the end capture time
            # i.e. capturing across midnight.
            if self.end_capture <= current_naive_time <= self.begin_capture:
                return False

        # capture interval
        if not (self.time2seconds(current_capture_time) % self.interval < Panorama.accuracy):
            return False
        return True

    @property
    def next_pano(self):
        nextin = self.time2seconds(datetime.datetime.now())
        nowstamp = self.time2seconds(datetime.datetime.now())
        while True:
            nextin += 1
            if (nextin % self.interval) < Panorama.accuracy:
                break
        return nextin - nowstamp

    def run_loop(self):
        while True:
            if self.time_to_capture():
                self.logger.info(self.summary)
                self.take_panorama()
                self.logger.info("Next pano in {}".format(sec2human(self.next_pano)))
            time.sleep(1)

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage \"script.py /path/to/config.yml\"")
        sys.exit()

    config_file = sys.argv[-1]

    updater = Updater()
    # updater.start()

    pano = Panorama(config_filename=config_file, queue=updater.communication_queue)

    # pano.test_calibration(1)
    #uploader = Uploader(pano.camera.identifier,
    #                    queue=updater.communication_queue,
    #                    config_filename=config_file)
    #uploader.daemon = True
    #uploader.start()
    pano.take_panorama()
    pano.logger.info("Next pano in {}".format(sec2human(pano.next_pano)))
    pano.run_loop()