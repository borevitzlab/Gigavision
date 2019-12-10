import datetime
import logging.config
import os
import re
import time
import numpy
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from xml.etree import ElementTree
from PIL import Image
from io import BytesIO


try:
    logging.config.fileConfig("logging.ini")
except:
    pass

exiv2_exists = False
try:
    import pyexiv2
    exiv2_exists = True
except Exception as e:
    logging.debug("Couldnt import pyexiv2: {}".format(str(e)))


class IPCamera(object):


    def __init__(self, identifier=None, config=None, **kwargs):
        if not config:
            config = dict()
        self.config = config.copy()
        self.return_parser = config.get("return_parser", "plaintext")
        e = os.environ.get("RETURN_PARSER", None)
        e = os.environ.get("CAMERA_RETURN_PARSER", e)
        self.return_parser = e if e is not None else self.return_parser
        self.logger = logging.getLogger(identifier)
        self.identifier = identifier

        self.camera_name = config.get("camera_name", identifier)
        self.interval = int(config.get("interval", 300))
        self.current_capture_time = datetime.datetime.now()

        self._image = None

        self._notified = []

        format_str = config.get("format_url", "http://{HTTP_login}@{ip}{command}")
        e = os.environ.get("FORMAT_URL", None)

        e = os.environ.get("CAMERA_FORMAT_URL", e)
        format_str = e if e is not None else format_str

        self.auth_type = config.get("auth_type", "basic")
        e = os.environ.get("AUTH_TYPE", None)
        e = os.environ.get("CAMERA_AUTH_TYPE", e)
        self.auth_type = e if e is not None else self.auth_type
        self.auth_object = None

        username = config.get("username", "admin")
        e = os.environ.get("AUTH_USERNAME", None)
        e = os.environ.get("CAMERA_AUTH_USERNAME", e)
        username = e if e is not None else username
        password = config.get("password", "admin")
        e = os.environ.get("AUTH_PASSWORD", None)
        e = os.environ.get("CAMERA_AUTH_PASSWORD", e)
        username = e if e is not None else username
        if format_str.startswith("http://{HTTP_login}@"):
            format_str = format_str.replace("{HTTP_login}@", "")
            self.auth_object = HTTPBasicAuth(username, password)
            self.auth_object_digest = HTTPDigestAuth(username, password)
            self.auth_object = self.auth_object_digest if self.auth_type == "digest" else self.auth_object

        self._HTTP_login = config.get("HTTP_login", "{user}:{password}").format(
            user=username,
            password=password)

        ip = config.get("ip", "192.168.1.101:81")
        e = os.environ.get("IP", None)
        e = os.environ.get("CAMERA_IP", e)
        ip = ip if e is None else e
        self._url = format_str.format(
            ip=ip or e,
            HTTP_login=self._HTTP_login,
            command="{command}")

        self._url = format_str.format(
            ip=ip,
            HTTP_login=self._HTTP_login,
            command="{command}")

        self._image_size = config.get("image_size", [1920, 1080])
        e = os.environ.get("CAMERA_IMAGE_SIZE", None)
        self._image_size = e if e is not None else self._image_size
        if type(self._image_size) is str:
            self._image_size = re.split("[\W+|\||,|x|x|:]", self._image_size)
            self._image_size = [ int(float(x)) for x in self._image_size ]

        image_quality = config.get("image_quality", 100)
        e = os.environ.get("CAMERA_IMAGE_QUALITY", None)
        self._image_size = e if e is not None else self._image_size

        self._image_quality = image_quality
        # no autofocus modes by default.
        self._autofocus_modes = config.get("autofocus_modes", [])

        self._hfov_list = config.get("horizontal_fov_list",
                                     [71.664, 58.269, 47.670, 40.981, 33.177, 25.246, 18.126, 12.782, 9.217, 7.050,
                                      5.82])

        self._vfov_list = config.get("vertical_fov_list",
                                     [39.469, 33.601, 26.508, 22.227, 16.750, 13.002, 10.324, 7.7136, 4.787, 3.729,
                                      2.448])
        self._hfov = self._vfov = None
        self._zoom_list = config.get("zoom_list", [50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1000])

        self._focus_range = config.get("focus_range", [1, 99999])

        # set commands from the rest of the config.
        self.command_urls = config.get('urls', {})
        self.return_keys = config.get("keys", {})

        self.image_quality = self.image_quality
        self.logger.info(self.status)

    def _make_request(self, command_string, *args, **kwargs):
        """
        Makes a generic request formatting the command string and applying the authentication.

        :param command_string: command string like read stream raw
        :type command_string: str
        :param args:
        :param kwargs:
        :return:
        """
        url = self._url.format(*args, command=command_string, **kwargs)
        if "&" in url and "?" not in url:
            url = url.replace("&", "?", 1)
        response = None
        try:
            response = requests.get(url, timeout=60, auth=self.auth_object)
            if response.status_code == 401:
                self.logger.debug("Auth is not basic, trying digest")
                response = requests.get(url, timeout=60, auth=self.auth_object_digest)
            if response.status_code not in [200, 204]:
                self.logger.error(
                    "[{}] - {}\n{}".format(str(response.status_code), str(response.reason), str(response.url)))
                return
            return response
        except Exception as e:
            self.logger.error("Some exception got raised {}".format(str(e)))
            return


    def _read_stream(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string
        :type command_string: str
        :param command_string: url to go to with parameters
        :return: string of data returned from the camera
        """
        response = self._make_request(command_string, *args, **kwargs)
        if response is None:
            return
        return response.text

    def _read_stream_raw(self, command_string, *args, **kwargs):
        """
        opens a url with the current HTTP_login string

        :param command_string: url to go to with parameters
        :type command_string: str
        :return: string of data returned from the camera
        """
        response = self._make_request(command_string, *args, **kwargs)
        if response is None:
            return
        return response.content

    def _get_cmd(self, cmd):
        cmd_str = self.command_urls.get(cmd, None)
        if not cmd_str and cmd_str not in self._notified:
            print("No command available for \"{}\"".format(cmd))
            self._notified.append(cmd_str)
            return None, None
        keys = self.return_keys.get(cmd, [])
        if type(keys) not in (list, tuple):
            keys = [keys]
        return cmd_str, keys

    @staticmethod
    def get_value_from_xml(message_xml, *args):
        """
        gets float, int or string values from a xml string where the key is the tag of the first element with value as
        text.

        :param message_xml: the xml to searach in.
        :param args: list of keys to find values for.
        :rtype: dict
        :return: dict of arg: value pairs requested
        """
        return_values = dict()
        if not len(args):
            return return_values
        if not len(message_xml):
            return return_values
        # apparently, there is an issue parsing when the ptz returns INVALID XML (WTF?)
        # these seem to be the tags that get mutilated.
        illegal = ['\n', '\t', '\r',
                   "<CPStatusMsg>", "</CPStatusMsg>", "<Text>",
                   "</Text>", "<Type>Info</Type>", "<Type>Info",
                   "Info</Type>", "</Type>", "<Type>"]
        for ill in illegal:
            message_xml = message_xml.replace(ill, "")

        root_element = ElementTree.Element("invalidation_tag")
        try:
            root_element = ElementTree.fromstring(message_xml)

        except Exception as e:
            print(str(e))
            print("Couldnt parse XML!!!")
            print(message_xml)

        return_values = dict
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

        return return_values

    @staticmethod
    def get_value_from_plaintext(message, *args):
        """
        gets float, int or string values from a xml string where the key is the tag of the first element with value as
        text.

        :param message:
        :param args: list of keys to find values for.
        :rtype: dict
        :return: dict of arg: value pairs requested
        """
        return_values = dict()
        if not len(args):
            return return_values
        if not len(message):
            return return_values
        for line in message.split("\n"):
            line = line.replace("= ", "=").replace(" =", "=").strip()
            name, value = line.partition("=")[::2]
            name, value = name.strip(), value.strip()
            types = [float, int, str]
            if name in args:
                for t in types:
                    try:
                        v = t(value)
                        if str(v).lower() in ['yes', 'no', 'true', 'false', 'on', 'off']:
                            v = str(v).lower() in ['yes', 'true', 'on']
                        return_values[name] = v
                        break
                    except ValueError:
                        pass
                else:
                    print("Couldnt cast an plaintext element text attribute to str. What are you feeding the parser?")
        return return_values

    def get_value_from_stream(self, stream, *keys):
        """
        Gets a value from some text data (xml or plaintext = separated values)
        returns a dict of "key":value pairs.

        :param stream: text data to search for values
        :type stream: str
        :param keys:
        :type keys: list
        :return: dict of values
        :rtype: dict
        """
        if self.return_parser == 'plaintext':
            return self.get_value_from_plaintext(stream, *keys)
        elif self.return_parser == 'xml':
            return self.get_value_from_xml(stream, *keys)
        else:
            return dict()

    def encode_write_image(self, img: Image, fn: str) -> list:
        """
        takes an image from PIL and writes it to disk as a tif and jpg
        converts from rgb to bgr for cv2 so that the images save correctly
        also tries to add exif data to the images

        :param PIL.Image img: 3 dimensional image array, x,y,rgb
        :param str fn: filename
        :return: files successfully written.
        :rtype: list(str)
        """
        # output types must be valid!
        fnp = os.path.splitext(fn)[0]
        successes = list()
        output_types = ["jpg", "tiff"]
        e = os.environ.get("OUTPUT_TYPES", None)
        if e is not None:
            output_types = re.split("[\W+|\||,|:]", e)

        for ext in output_types:
            fn = "{}.{}".format(fnp, ext)
            s = False
            try:
                if ext in ("tiff", "tif"):
                    if fn.endswith(".tiff"):
                        fn = fn[:-1]
                    img.save(fn, format="TIFF", compression='tiff_lzw')
                else:
                    img.save(fn)
                s = True
            except Exception as e:
                self.logger.error("Couldnt write image")
                self.logger.error(e)

            # im = Image.fromarray(np.uint8(img))
            # s = cv2.imwrite(fn, img)

            if s:
                successes.append(fn)
                try:
                    # set exif data
                    if exiv2_exists:
                        meta = pyexiv2.ImageMetadata(fn)
                        meta.read()
                        for k, v in self.exif.items():
                            try:
                                meta[k] = v
                            except:
                                pass
                        meta.write()
                except Exception as e:
                    self.logger.debug("Couldnt write the appropriate metadata: {}".format(str(e)))
        return successes


    def capture_image(self, filename=None) -> numpy.array:
        """
        Captures an image with the IP camera, uses requests.get to acqire the image.

        :param filename: filename without extension to capture to.
        :return: list of filenames (of captured images) if filename was specified, otherwise a numpy array of the image.
        :rtype: numpy.array or list
        """
        st = time.time()
        cmd, keys = self._get_cmd("get_image")
        if "{width}" in cmd and "{height}" in cmd:
            cmd = cmd.format(width=self._image_size[0], height=self.image_size[1])
        if not cmd:
            self.logger.error("No capture command, this is wrong...")
            return self._image

        url = self._url.format(command=cmd)
        for x in range(10):
            try:
                # fast method
                a = self._read_stream_raw(cmd)
                # b = numpy.fromstring(a, numpy.uint8)
                self._image = Image.open(BytesIO(a))
                if filename:
                    rfiles = self.encode_write_image(self._image, filename)
                    self.logger.debug("Took {0:.2f}s to capture".format(time.time() - st))
                    return rfiles
                else:
                    self.logger.debug("Took {0:.2f}s to capture".format(time.time() - st))
                    break
            except Exception as e:
                self.logger.error("Capture from network camera failed {}".format(str(e)))
            time.sleep(0.2)
        else:
            self.logger.error("All capture attempts (10) for network camera failed.")
        return self._image

    # def set_fov_from_zoom(self):
    #     self._hfov = numpy.interp(self._zoom_position, self.zoom_list, self.hfov_list)
    #     self._vfov = numpy.interp(self._zoom_position, self.zoom_list, self.vfov_list)

    @property
    def image_quality(self) -> float:
        """
        Image quality as a percentage.

        :getter: cached.
        :setter: to camera.
        :rtype: float
        """
        return self._image_quality

    @image_quality.setter
    def image_quality(self, value: float):
        assert (1 <= value <= 100)
        cmd, keys = self._get_cmd("get_image_quality")
        if cmd:
            self._read_stream(cmd.format(value))

    @property
    def image_size(self) -> list:
        """
        Image resolution in pixels, tuple of (width, height)

        :getter: from camera.
        :setter: to camera.
        :rtype: tuple
        """
        cmd, keys = self._get_cmd("get_image_size")
        if cmd:
            stream = self._read_stream(cmd)
            output = self.get_value_from_stream(stream, keys)
            width,height = self._image_size
            for k,v in output.items():
                if "width" in k:
                    width = v
                if "height" in k:
                    height = v
            self._image_size = [width, height]
        return self._image_size

    @image_size.setter
    def image_size(self, value):
        assert type(value) in (list, tuple), "image size is not a list or tuple!"
        assert len(value) == 2, "image size doesnt have 2 elements width,height are required"
        value = list(value)
        cmd, keys = self._get_cmd("set_image_size")
        if cmd:
            self._read_stream(cmd.format(width=value[0], height=value[1]))
            self._image_size = value

    @property
    def focus_mode(self) -> str:
        """
        TODO: this is broken, returns the dict of key: value not value

        Focus Mode

        When setting, the mode provided must be in 'focus_modes'

        :getter: from camera.
        :setter: to camera.
        :rtype: list
        """
        cmd, keys = self._get_cmd("get_focus_mode")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        return self.get_value_from_stream(stream_output, keys)['mode']

    @focus_mode.setter
    def focus_mode(self, mode: str):
        assert (self._autofocus_modes is not None)
        if str(mode).upper() not in [x.upper() for x in self._autofocus_modes]:
            print("Focus mode not in list of supported focus modes, not setting.")
            return

        cmd, keys = self._get_cmd("set_focus_mode")
        if cmd:
            self._read_stream(cmd.format(mode=mode))

    @property
    def focus_position(self):
        """
        Focal position as an absolute value.

        :getter: from camera.
        :setter: to camera.
        :rtype: float
        """
        cmd, keys = self._get_cmd("get_focus")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        result = self.get_value_from_stream(stream_output, keys)
        return next(iter(result), float(99999))

    @focus_position.setter
    def focus_position(self, absolute_position):
        self.logger.debug("Setting focus position to {}".format(absolute_position))
        cmd, key = self._get_cmd("set_focus")
        if not cmd:
            assert (self._focus_range is not None and absolute_position is not None)
            absolute_position = min(self._focus_range[1], max(self._focus_range[0], absolute_position))
            assert (self._focus_range[0] <= absolute_position <= self._focus_range[1])
            self._read_stream(cmd.format(focus=absolute_position))

    def focus(self):
        """
        focuses the camera by cycling it through its autofocus modes.
        """
        self.logger.debug("Focusing...")
        tempfocus = self.focus_mode
        cmd, key = self._get_cmd("set_autofocus_mode")
        if not cmd or len(self._autofocus_modes) < 1:
            return
        for mode in self._autofocus_modes:
            self.focus_mode = mode
            time.sleep(2)
        self.focus_mode = tempfocus
        self._read_stream(cmd.format(mode=self._autofocus_modes[0]))
        time.sleep(2)
        self.logger.debug("Focus complete.")

    @property
    def focus_range(self):
        """
        Information about the focus of the camera

        :return: focus type, focus max, focus min
        :rtype: list [str, float, float]
        """
        cmd, keys = self._get_cmd("get_focus_range")
        if not cmd:
            return None
        stream_output = self._read_stream(cmd)
        values = self.get_value_from_stream(stream_output, keys)
        return values[2:0:-1]

    @property
    def hfov_list(self):
        """
        List of horizontal FoV values according to focus list.

        :getter: cached.
        :setter: cache.
        :rrtype: list(float)
        """
        return self._hfov_list

    @hfov_list.setter
    def hfov_list(self, value):
        assert type(value) in (list, tuple), "must be either list or tuple"
        # assert len(value) == len(self._zoom_list), "must be the same length as zoom list"
        self._hfov_list = list(value)

    @property
    def vfov_list(self):
        """
        List of vertical FoV values according to focus list.

        :getter: cached.
        :setter: cache.
        :rrtype: list(float)
        """
        return self._vfov_list

    @vfov_list.setter
    def vfov_list(self, value):
        assert type(value) in (list, tuple), "must be either list or tuple"
        # assert len(value) == len(self._zoom_list), "must be the same length as zoom list"
        self._vfov_list = list(value)

    @property
    def hfov(self):
        """
        Horizontal FoV

        :getter: calculated using cached zoom_position, zoom_list and hfov_list.
        :setter: cache.
        :rrtype: list(float)
        """
        # self._hfov = numpy.interp(self._zoom_position, self.zoom_list, self.hfov_list)
        return self._hfov

    @hfov.setter
    def hfov(self, value: float):
        self._hfov = value

    @property
    def vfov(self):
        """
        Vertical FoV

        :getter: calculated using cached zoom_position, zoom_list and vfov_list.
        :setter: cache.
        :rrtype: list(float)
        """
        # self._vfov = numpy.interp(self._zoom_position, self.zoom_list, self.vfov_list)
        return self._vfov

    @vfov.setter
    def vfov(self, value: float):
        self._vfov = value

    @property
    def status(self) -> str:
        """
        Helper property for a string of the current zoom/focus status.

        :return: informative string of zoom_pos zoom_range focus_pos focus_range
        :rtype: str
        """
        # fmt_string = "zoom_pos:\t{}\nzoom_range:\t{}"
        fmt_string = "".join(("\nfocus_pos:\t{}\nfocus_range:\t{}"))
        return fmt_string.format(self.focus_position, self.focus_range)
