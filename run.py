#!/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 10:24:49 2014

:author: chuong nguyen, chuong.nguyen@anu.edu.au
:author: Gareth Dunstone, gareth.dunstone@anu.edu.au


"""

import sys
import os, json
from datetime import datetime
import shutil
import tarfile
import logging, logging.config
import numpy as np
import time
import csv
import yaml
import tempfile
import re
from libs.IPCamera import IPCamera
from libs.PanTilt import PanTilt
from PIL import Image
import datetime

try:
    logging.config.fileConfig("logging.ini")
except:
    pass

try:
    import telegraf
except Exception as e:
    print(str(e))



logging.getLogger("paramiko").setLevel(logging.WARNING)


def sec2human(seconds) -> str:
    """
    formats a timedelta object into semi-fuzzy human readable time periods.

    :param seconds: seconds to format into a time period
    :type seconds: int or float
    :return: human readable string
    :rtype: str
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

regex = re.compile(r'((?P<hours>\d+?)hr)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')


def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return datetime.timedelta(**time_params)


class Panorama(object):
    """
    Panorama class.
    Provides the calibration and creation of tiled panoramas with a configuration file.
    """
    accuracy = 3

    def __init__(self, config=None, config_filename=None):

        if not config:
            config = dict()
        if config_filename:
            config = yaml.load(open(config_filename).read())
        config = config.copy()
        self.use_focus_at_center = config.get("use_focus_at_center", True)
        e = os.environ.get("USE_FOCUS_AT_CENTER", None)
        self.use_focus_at_center = e if e is not None else self.use_focus_at_center
        self.name = config.get("name", "DEFAULT_PANO_NAME")
        e = os.environ.get("NAME", None)
        self.name = e if e is not None else self.name
        self.logger = logging.getLogger(self.name)
        self._output_dir = config.get("output_dir", "/data")
        self.output_dir = self._output_dir

        start_time_string = str(config.get('starttime', "0000"))
        e = os.environ.get("START_TIME", None)
        start_time_string = e if e is not None else start_time_string
        end_time_string = str(config.get('stoptime', "2359"))
        e = os.environ.get("STOP_TIME", None)
        end_time_string = e if e is not None else end_time_string


        start_time_string = start_time_string.replace(":", "")

        end_time_string = end_time_string.replace(":", "")
        start_time_string = start_time_string[:4]
        end_time_string = end_time_string[:4]

        assert end_time_string.isdigit(), "Non numerical start time, {}".format(str(end_time_string))
        self.begin_capture = datetime.datetime.strptime(start_time_string, "%H%M").time()

        assert end_time_string.isdigit(), "Non numerical start time, {}".format(str(end_time_string))
        self.end_capture = datetime.datetime.strptime(end_time_string, "%H%M").time()

        interval = config.get("interval", "1hr")
        e = os.environ.get("INTERVAL", None)

        interval = e if e is not None else interval

        self.interval = parse_time(interval)
        camera = None
        ptz = None
        try:
            while not camera:
                camera_config = config.get("camera")
                if not camera_config:
                    raise ValueError("No 'camera' section found in config file.")
                camera = IPCamera(self.name, config=camera_config)
        except Exception as e:
            self.logger.error("Couldnt initialise Camera: " + str(e))
            time.sleep(30)
            camera = None

        self._camera = camera
        if self._camera:
            fov = config.get("camera_fov", None)
            e = os.environ.get("CAMERA_FOV", None)
            fov = e if e is not None else fov
            if type(fov) is str:
                fov = re.split("[\W+\|,|x|x|:]", fov)
                fov = [float(x) for x in fov]
            if fov is not None:
                self._camera.hfov, self._camera.vfov = fov
            self.logger.debug("Camera initialised")

        while not ptz:
            try:
                ptz_config = config.get("ptz")
                if not ptz_config:
                    raise ValueError("No 'ptz' section found in config file.")
                ptz = PanTilt(config=ptz_config)
                self.logger.debug("ptz initialised")
            except Exception as e:
                self.logger.error("Couldnt initialise PTZ: " + str(e))
                time.sleep(30)
                ptz = None

        self._pantilt = ptz
        self._zoom_position = config.get('ptz', {}).get('zoom', 800)

        self._image_overlap = float(config.get("overlap", 50))
        e = os.environ.get("OVERLAP", None)
        self._image_overlap = e if e is not None else self._image_overlap
        self._image_overlap /= 100

        self._seconds_per_image = 5
        # this is vital to create the output folder
        self._csv_log = None
        self._recovery_filepath = os.path.join("/persist", ".gv_recover_{}.json".format(self.name))
        self._recovery_file = dict(image_index=0)
        try:
            if os.path.exists(self._recovery_filepath):
                with open(self._recovery_filepath, "r") as file:
                    self._recovery_file = json.loads(file.read())
        except:
            with open(self._recovery_filepath, "w+") as f:
                f.write("{}")
                f.seek(0)
                self._recovery_file = json.loads(f.read())

        first_corner = config.get("first_corner", [100, 20])
        e = os.environ.get("FIRST_CORNER", None)
        first_corner = e if e is not None else first_corner
        if type(first_corner) is str:
            first_corner = re.split("[\W+\|,|x|x|:]", first_corner)
        second_corner = config.get("second_corner", [300, -20])
        e = os.environ.get("SECOND_CORNER", None)
        second_corner = e if e is not None else second_corner
        if type(second_corner) is str:
            second_corner = re.split("[\W+\|,|x|x|:]", second_corner)
        assert type(first_corner) in (list, tuple), "first corner must be a list or tuple"
        assert type(second_corner) in (list, tuple), "second corner must be a list or tuple"
        assert len(first_corner) == 2, "first corner must be of length 2"
        assert len(second_corner) == 2, "second corner must be of length 2"
        self._pan_range = sorted([first_corner[0], second_corner[0]])
        self._tilt_range = sorted([first_corner[1], second_corner[1]])
        self._pan_step = self._tilt_step = None
        self._pan_pos_list = self._tilt_pos_list = list()

        scan_order_unparsed = config.get("scan_order", "0")

        e = os.environ.get("SCAN_ORDER", None)
        scan_order_unparsed = e if e is not None else scan_order_unparsed
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


        try:
            telegraf_client = telegraf.TelegrafClient(host="telegraf", port=8092)
            metric = {
                "num_rows": len(self._tilt_pos_list),
                "num_cols": len(self._pan_pos_list),
                "recovery_index": int(self._recovery_file.get("image_index", 0)),
                "hfov": self.camera.hfov,
                "vfov": self.camera.vfov
            }
            telegraf_client.metric("gigavision", metric, tags={'name': self.name})
        except:
            pass

    def set_current_as_first_corner(self):
        """
        This and :func:`set_current_as_second_corner`, both internally call enumerate positions.

        """
        self.first_corner = self._pantilt.position

    def set_current_as_second_corner(self):
        """
        See :func:`set_current_as_first_corner`.
        """
        self.second_corner = self._pantilt.position

    def enumerate_positions(self):
        """
        Uses the currrent image overlap, camera fov and corners to calculate a "grid" of pan and tilt positions.

        Also sets the internal enumeration of pan/tilt positions.
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

        self._pan_pos_list = np.arange(pan_start, pan_stop, self._pan_step)
        self._tilt_pos_list = np.arange(tilt_start, tilt_stop, self._tilt_step)

        self.logger.debug("pan {}-{}".format(pan_start, pan_stop))
        self.logger.debug("tilt {}-{}".format(tilt_start, tilt_stop))

    @property
    def summary(self) -> str:
        """
        returns a human readable summary of the panorama parameters.
        These include pan step, camera fov etc.

        :return: information about the panorama
        :rtype: str
        """
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
    def camera(self) -> IPCamera:
        return self._camera

    @camera.setter
    def camera(self, value: IPCamera):
        self._camera = value

    @property
    def pantilt(self) -> PanTilt:
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
    def scan_order(self) -> str:
        return self._scan_order_translation_r.get(self._scan_order, "cols,right")

    @scan_order.setter
    def scan_order(self, value: str):
        self._scan_order = self._scan_order_translation.get(str(value).lower().replace(" ", ""), 0)

    @property
    def output_dir(self) -> str:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: str):
        assert type(value) is str, "Set the output folder to a string"
        if not os.path.isdir(value):
            os.makedirs(value)
        self._output_dir = value

    @property
    def panorama_fov(self) -> tuple:
        """
        Gets the total fov of the Panorama.

        :return: total fov of the panorama as (hfov, vfov)
        :rtype: tuple[float, float]
        """
        return self._pan_range, self._tilt_range

    @panorama_fov.setter
    def panorama_fov(self, value: tuple):
        """
        sets the pan range and tilt range of the panorama using the fov, and centre points

        :param value: 4 length tuple of pan_fov, tilt_fov, pan_centre, tilt_centre
        :type value: tuple
        """
        try:
            pan_fov, tilt_fov, pan_centre, tilt_centre = value
        except ValueError:
            raise ValueError("You must pass an iterable with the PanFov, TiltFov, PanCentre, TiltCentre")
        self._pan_range = [pan_centre - (pan_fov / 2), pan_centre + (pan_fov / 2)]
        self._tilt_range = [tilt_centre - (tilt_fov / 2), tilt_centre + (tilt_fov / 2)]
        self.enumerate_positions()

    @property
    def first_corner(self) -> tuple:
        """
        the starting corner of the panorama.
        :return: tuple of first corner as (pan,tilt)
        :rtype: tuple[float,float]
        """
        return self._pan_range[0], self._tilt_range[1]

    @first_corner.setter
    def first_corner(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range[0], self._tilt_range[1] = value
        self.enumerate_positions()

    @property
    def center(self) -> tuple:
        """
        :return: tuple of center position as (pan,tilt)
        :rtype: tuple[float,float]
        """
        return tuple((np.array(self.first_corner) + np.array(self.second_corner)) / 2)

    @property
    def second_corner(self):
        """
        the finishing corner of the panorama.
        :return: tuple of second corner as (pan,tilt)
        :rtype: tuple[float,float]
        """
        return self._pan_range[1], self._tilt_range[0]

    @second_corner.setter
    def second_corner(self, value):
        assert type(value) in (list, tuple), "must be a list or tuple"
        assert len(value) == 2, "must have 2 elements"
        self._pan_range[1], self._tilt_range[0] = value
        self.enumerate_positions()


    def _init_csv_log(self, path: str):
        self._csv_log = path
        if not os.path.exists(self._csv_log):
            with open(self._csv_log, 'w') as file:
                file.write("image_index,pan_deg,tilt_deg,zoom_pos,focus_pos\n")

    def load_csv_log(self) -> dict:
        """
        loads a csv log into a dictionary so that we can continue to write to it.

        :return: dict of values in the csv.
        """
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

    def write_csv_log(self, image_index, pan_pos, tilt_pos):
        """
        writes a new line of values to the csv log.

        :param image_index: current index to be written
        :param pan_pos: the current pan position
        :param tilt_pos: the current tilt position.
        """
        if self._csv_log and os.path.isfile(self._csv_log):
            with open(self._csv_log, 'a') as File:
                File.write("{},{},{},{},{}\n".format(
                    image_index, pan_pos, tilt_pos,
                    self._pantilt.zoom_position,
                    self._camera.focus_position))

    def write_to_recovery_file(self, index, started_time):
        """
        writes the current state to the recovery file.

        :param index: the current index into the panorama.
        :param started_time: the time the panorama was started.
        """
        self._recovery_file['image_index'] = index
        with open(self._recovery_filepath, 'w') as file:
            data = {"cols": len(self._pan_pos_list),
                    "rows": len(self._tilt_pos_list),
                    "image_index": index,
                    "sec_per_image": self._seconds_per_image,
                    "started_time": started_time}
            file.write(json.dumps(data))

    def take_panorama(self):
        """
        takes a panorama using the current values stored in this :class:`Panorama` object.
        """
        ts_fmt = "%Y_%m_%d_%H_%M_00"
        tar_fmt = "%Y_%m_%d_%H"
        last_image_captured = 0
        now = datetime.datetime.now()

        if self.use_focus_at_center:
            self.logger.debug("Moving to center to focus...")
            self._pantilt.position = np.mean(self._pan_range), np.mean(self._tilt_range)
            self._pantilt.zoom_position = self._zoom_position
            time.sleep(1)
            self._camera.focus()
            time.sleep(1)
            self._camera.focus_mode = "off"

        last_started = self._recovery_file.get('started_time', None)
        if last_started:
            try:
                last_started = datetime.datetime.strptime(last_started, ts_fmt)
                if int(now.timestamp()) - int(last_started.timestamp()) < self.interval.total_seconds():
                    now = last_started
                else:
                    self.logger.warning("Recovery exists, but its now too late. Starting from beginning.")
                    self.write_to_recovery_file(0, now.strftime(ts_fmt))
            except Exception as e: 
                self.logger.warning(str(e))
                self.write_to_recovery_file(0, now.strftime(ts_fmt))
        this_dir = os.path.join(self._output_dir, now.strftime("%Y/%Y_%m/%Y_%m_%d/%Y_%m_%d_%H"))
        os.makedirs(this_dir, exist_ok=True)

        self._csv_log = os.path.join(os.getcwd(), now.strftime("{name}-" + ts_fmt + ".csv").format(name=self.name))
        cfg = self.load_csv_log()
        focus_list = cfg.get('focus_pos', [])

        start_time = time.time()

        # this is just here in case you want to update overview.jpg
        # im1 = cv2.resize(self.camera.capture_image(), None, fx=0.1, fy=0.1)
        # overview = np.zeros((im1.shape[0]*len(self._tilt_pos_list),
        #                      im1.shape[1]*len(self._pan_pos_list),
        #                      3), np.uint8)
        # cv2.imwrite("overview.jpg", overview)
        try:
            telegraf_client = telegraf.TelegrafClient(host="telegraf", port=8092)
        except:
            pass
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
        recovery_index = self._recovery_file.get('image_index', 0)
        rolling = []
        preview_width = int(os.environ.get("PREVIEW_WIDTH", 320))
        preview_height = int(preview_width * self.camera._image_size[1] / self.camera._image_size[0])
        if os.environ.get("OVERVIEW", None) is not None:
            overview_width = len(pan_pos_list)*preview_width
            overview_height = len(tilt_pos_list)*preview_height
            overview_fn = os.path.join(this_dir, "{}_overview_{}.jpg".format(self.name, now.strftime(ts_fmt)))
            overview = None
            try:
                overview = Image.open(overview_fn)
                if not (overview.size[0] == overview_width and overview.size[1] == overview_height):
                    overview = Image.new('RGB', (overview_width, overview_height))
            except:
                overview = Image.new('RGB', (overview_width, overview_height))
        with tempfile.TemporaryDirectory(prefix=self.name) as spool:

            def cap(_pan_pos: float, _tilt_pos: float, _image_index: int, lcap: int, _i: int, _j: int) -> int:
                """
                captures an image for the position _pan_pos,_tilt_pos with the image index _image_index

                :param _pan_pos: the pan position to take an image
                :param _tilt_pos: the tilt position to take an image
                :param _image_index: index of the current image. used to write the image filename.
                :param lcap: used to calculate how long capture is taking.
                :return:
                """
                this_img_capture_s = time.time()
                self._pantilt.position = _pan_pos, _tilt_pos

                self.write_csv_log(_image_index, _pan_pos, _tilt_pos)
                self.write_to_recovery_file(_image_index, now.strftime(ts_fmt))
                for _ in range(0, 15):
                    filename = os.path.join(spool,
                                            now.strftime("{name}_" + ts_fmt + "_{index:04}").format(name=self.name,
                                                                                                    index=_image_index + 1))
                    try:
                        output_filenames = list(self._camera.capture_image(filename=filename))
                        # output_filenames = self._camera.capture_monkey(filename=filename)
                        if type(output_filenames) is list and len(output_filenames):
                            metric = dict()
                            try:
                                t = time.time()
                                image = self.camera._image.resize((preview_width,preview_height), Image.NEAREST)
                                yoff = _i * preview_height
                                xoff = _j * preview_width
                                if os.environ.get("OVERVIEW", None) is not None:
                                    overview.paste(image, (xoff, yoff))
                                    overview.save(overview_fn)

                                    metric['overview_resize_s'] = time.time()-t
                                telegraf_client.metric("gigavision", metric, tags={"name": self.name})
                            except Exception as e:
                                self.logger.error("couldnt write overview to {}".format(overview_fn))
                                self.logger.error(str(e))
                            for f in output_filenames:
                                shutil.move(f, os.path.join(this_dir, os.path.basename(f)))
                            self.logger.info("wrote image {}/{}".format(_image_index + 1,
                                                                        (len(self._pan_pos_list) * len(
                                                                            self._tilt_pos_list))))
                            lcap += 1
                            # update time per image
                            current_time = time.time()
                            self._seconds_per_image = (current_time - start_time) / lcap
                            self.logger.info("Seconds per image {0:.2f}s".format(self._seconds_per_image))
                            metric['image_capture_s'] = time.time()-this_img_capture_s
                            telegraf_client.metric("gigavision", metric, tags={"name": self.name})
                            return lcap
                    except Exception as e:
                        self.logger.error("Bad things happened: {}".format(str(e)))
                else:
                    self.logger.error("failed capturing!")
                    return lcap

            if self._scan_order >= 2:
                for i, tilt_pos in enumerate(tilt_pos_list):
                    for j, pan_pos in enumerate(pan_pos_list):
                        image_index = i * len(pan_pos_list) + j
                        if image_index < recovery_index:
                            continue
                        t = time.time()
                        last_image_captured = cap(pan_pos, tilt_pos, image_index, last_image_captured, i, j)
                        rolling.append(time.time()-t)
                    try:
                        metric = {'timing_avg_s': sum(rolling)/len(rolling), 'rolling_index': len(rolling)}
                        telegraf_client.metric("gigavision", metric, tags={"name": self.name})
                    except:
                        pass
            else:
                for j, pan_pos in enumerate(pan_pos_list):
                    for i, tilt_pos in enumerate(tilt_pos_list):
                        image_index = j * (len(tilt_pos_list)) + i
                        if image_index < recovery_index:
                            continue
                        t = time.time()
                        last_image_captured = cap(pan_pos, tilt_pos, image_index, last_image_captured, i, j)
                        rolling.append(time.time() - t)
                    try:
                        metric = {'timing_avg_s': sum(rolling) / len(rolling), 'rolling_index': len(rolling)}
                        telegraf_client.metric("gigavision", metric, tags={"name": self.name})
                    except:
                        pass
            try:
                metric = { 'timing_avg_s': sum(rolling) / len(rolling),
                            'total_images': len(rolling),
                            "num_cols": len(self._pan_pos_list),
                            "num_rows": len(self._tilt_pos_list)}
                telegraf_client.metric("gigavision", metric, tags={"name": self.name})
            except:
                pass

        self._recovery_file['image_index'] = 0
        t = time.time() - start_time
        self.logger.info("Panorama complete in {}".format(sec2human(t)))
        try:
            telegraf_client.metric("gigavision", {'timing_total_s': t}, tags={"name": self.name})
        except:
            pass

        try:
            shutil.move(self._csv_log, os.path.join(this_dir, now.strftime("{name}-" + ts_fmt + ".csv").format(name=self.name)))
        except Exception as e:
            self.logger.error("Couldnt move csv log.")
            # self.logger.error(e)
        try:
            os.remove(self._recovery_filepath)
        except Exception as e:
            self.logger.error("Couldnt remove recovery.")

    def calibrate_and_run(self):
        """
        calibrates, and takes a panorama.
        """
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
        """
        Prints the summary and takes a panorama
        """
        self.logger.info(self.summary)
        self.take_panorama()

    @staticmethod
    def time2seconds(t: datetime.datetime) -> int:
        """
        converts a datetime to an integer of seconds since epoch

        :return: seconds since 1970-01-01 00:00
        :rtype: int
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

        :return: whether we should start capturing images now or not
        :rtype: bool
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
        if not (self.time2seconds(current_capture_time) % self.interval.total_seconds() < Panorama.accuracy):
            return False
        return True

    @property
    def next_pano(self):
        """
        calculates the amount of time until the next panorama

        :return: time until the next panorama (in seconds)
        :rtype: int
        """
        nextin = self.time2seconds(datetime.datetime.now())
        nowstamp = self.time2seconds(datetime.datetime.now())
        while True:
            nextin += 1
            if (nextin % self.interval.total_seconds()) < Panorama.accuracy:
                break
        return nextin - nowstamp

    def run_loop(self):
        """
        runs the panorama taker in a loop based on the interval in the config file.
        """
        while True:
            if self.time_to_capture():
                self.logger.info(self.summary)
                self.take_panorama()
                self.logger.info("Next pano in {}".format(sec2human(self.next_pano)))
            time.sleep(1)


if __name__ == "__main__":
    config_file = sys.argv[-1]

    config = dict()
    if config_file.endswith(".yaml") or config_file.endswith(".yml") and os.path.exists(config_file):
        with open(config_file) as config_fh:
            config = yaml.load(config_fh.read())
    while True:
        try:
            pano = Panorama(config=config)
            break
        except:
            time.sleep(10)

    pano.take_panorama()
    pano.logger.info("Next pano in {}".format(sec2human(pano.next_pano)))
    pano.run_loop()
