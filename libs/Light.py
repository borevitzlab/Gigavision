import datetime
import yaml
import logging.config
import os
import shutil
import time
import re
import numpy as np
from telnetlib import Telnet
from urllib import request as urllib_request
from collections import deque
from threading import Thread, Event
from libs.SysUtil import SysUtil
import csv


logging.config.fileConfig("logging.ini")


class Light(object):
    accuracy = 3

    def __init__(self, identifier: str=None,
                 queue: deque=None, **kwargs):
        # identifier is NOT OPTIONAL!
        # init with name or not, just extending some of the functionality of Thread

        self.communication_queue = queue or deque(tuple(), 256)
        self.logger = logging.getLogger(identifier)
        self.stopper = Event()
        self.identifier = identifier
        self.config_filename = SysUtil.identifier_to_ini(self.identifier)
        self.config = \
            self.section = \
            self.telnet_address = \
            self.wavelengths = \
            self.wavelengths = \
            self.multiplier = \
            self.set_command = \
            self.get_command = \
            self.set_all_command = \
            self.set_all_wl_command = \
            self.csv = \
            self.csv_fp = \
            self.out_of_range = \
            self.current_timepoint = None
        self.datetimefmt = None
        self._current_wavelength_intentisies = dict()
        self._current_csv_index = 0
        self.failed = list()
        self.re_init()

    def re_init(self):
        """
        re-initialisation.
        this causes all the confiuration values to be reacquired, and a config to be recreated as valid if it is broken.
        :return:
        """
        self.logger.info("Re-init...")
        self.config = SysUtil.ensure_config(self.identifier)

        self.section = self.config['lights']
        self.datetimefmt = None
        self.telnet_address = (self.section.get("telnet_host", fallback="192.168.1.111"),
                               self.section.getint("telnet_port", fallback=50630))
        self.multiplier = self.section.getfloat("multiplier", fallback=10.0)
        self.set_command = self.section.get("set_command", fallback="setwlrelpower")
        self.set_all_command = self.section.get("set_all_command", fallback="setall")
        self.set_all_wl_command = self.section.get("set_all_wl_command", fallback="setwlrelpower")
        self.get_command = self.section.get("get_command", fallback="getwlrelpower")

        wavelengths = self.section.get("wavelengths", fallback="400nm,420nm,450nm,530nm,630nm,660nm,735nm")
        self.wavelengths = [s.strip() for s in wavelengths.split(",")]
        csv_keys = self.section.get("csv_keys", fallback="LED1,LED2,LED3,LED4,LED5,LED6,LED7")
        self.csv_keys = [s.strip().lower() for s in csv_keys.split(",")]

        self.csv_fp = self.config.get("solarcalc", 'file_path', fallback="DEFAULT.csv")

        with open(self.csv_fp) as csv_fh:
            self.csv = [{k.lower(): v for k, v in x.items()} for x in
                        csv.DictReader(csv_fh, delimiter=',', quoting=csv.QUOTE_NONE)]

        self._current_wavelength_intentisies = {wl: 0 for wl in wavelengths}
        self._current_csv_index = 0

        def parse_datestring(datestring: str) -> datetime.datetime:
            """
            parses a datestring into a datetime.
            first tries the member self.datetimefmt to speed it up.
            Then tries getting it from timestamp (unix style)
            and then descending accuracies (and standardisation) of timestamp.
            the order and list is as follows:
            iso8601 datetime accurate to microseconds with timezone
            iso8601 datetime accurate to microseconds
            iso8601 datetime accurate to seconds with timezone
            iso8601 datetime accurate to seconds
            iso8601 datetime accurate to minutes
            timestream format (YY_mm_DD_HH_MM_SS) accurate to seconds
            timestream format accurate to minutes
            Alternate date format (YY/mm/DD) accurate to seconds
            Alternate date format accurate to minutes
            iso8601 with reverse ordered date part accurate to seconds
            iso8601 with reverse ordered date part accurate to minutes
            timestream format with reverse ordered date part accurate to seconds
            timestream format with reverse ordered date part accurate to minutes
            Alternate date format with reverse ordered date part accurate to seconds
            Alternate date format with reverse ordered date part accurate to minutes

            :param datestring: string to parse
            :rtype datetime:
            :return: datetime
            """
            datetime_fmts = ["%Y-%m-%dT%H:%M:%S.%f%z",
                             "%Y-%m-%dT%H:%M:%S.%f",
                             "%Y-%m-%dT%H:%M:%S%z",
                             "%Y-%m-%dT%H:%M:%SZ",
                             "%Y-%m-%d %H:%M:%S",
                             "%Y-%m-%d %H:%M",
                             "%Y_%m_%d_%H_%M_%S",
                             "%Y_%m_%d_%H_%M",
                             "%Y/%m/%d %H:%M:%S",
                             "%Y/%m/%d %H:%M",
                             "%d-%m-%Y %H:%M:%S",
                             "%d-%m-%Y %H:%M",
                             "%d_%m_%Y_%H_%M_%S",
                             "%d_%m_%Y_%H_%M",
                             "%d/%m/%Y %H:%M:%S",
                             "%d/%m/%Y %H:%M"]

            if self.datetimefmt:
                try:
                    return datetime.datetime.strptime(datestring, self.datetimefmt)
                except:
                    pass
            try:
                return datetime.datetime.fromtimestamp(datestring)
            except:
                pass
            for fmt in datetime_fmts:
                try:
                    q = datetime.datetime.strptime(datestring, fmt)
                    self.datetimefmt = fmt
                    return q
                except:
                    pass
            else:
                raise ValueError("Error parsing {} to a valida datetime".format(str(datestring)))

        for d in self.csv:
            # fix up all the datetimes so that they are actually real datetimes
            the_datestring = d.get('datetime', d.get('posix_timestamp', "{} {}"))
            if "datetime" not in d.keys() and "posix_timestamp" not in d.keys():
                date = d.get("date", d.get("d", ""))
                time = d.get("time", d.get("t", ""))
                the_datestring = the_datestring.format(date, time)
            try:
                d['datetime'] = parse_datestring(the_datestring)
            except Exception as e:
                self.logger.error(str(e))

            # fix up the intensities so they are real intensities
            d['intensities'] = {wl: 0 for wl in wavelengths}

            for idx, wl in enumerate(self.wavelengths):
                if idx >= len(csv_keys):
                    self.logger.warning("More wavelengths than matching keys in csv_keys field")
                    continue
                key = csv_keys[idx].lower()
                if key in d.keys():
                    d['intensities'][wl] = float(d[key])*self.multiplier
                    del d[key]
        self.current_timepoint = datetime.datetime.now()

        self.out_of_range = self.current_timepoint > self.csv[-1]['datetime']

    def calculate_current_state(self):
        """
        determines the current state the lights should be in.
        doesnt send the state.
        sets the internal state of the Light object
        :param nowdt:
        :return:
        """
        def nfunc(in_dt: datetime.datetime):
            """
            returns true if the current time is greater than that of the current csv
            :return:
            """

            csvdt = self.csv[self._current_csv_index]['datetime']
            if self.out_of_range:
                in_dt = in_dt.replace(year=csvdt.year, month=csvdt.month, day=csvdt.day)
            return in_dt > csvdt

        while nfunc(self.current_timepoint):
            self._current_csv_index += 1
            if self._current_csv_index > len(self.csv):
                self.out_of_range = True
                thedt = self.csv[-1]['datetime'] - datetime.timedelta(hours=24)
                while nfunc(thedt):
                    self._current_csv_index -=1
            self._current_wavelength_intentisies = self.csv[self._current_csv_index]['intensities']

    def test(self):
        self.current_timepoint = datetime.datetime(2016, 7, 1, 0, 0, 0)

        date_end = datetime.datetime(2016, 10, 4, 0, 0, 0)

        while self.current_timepoint < date_end:
            self.current_timepoint = self.current_timepoint + datetime.timedelta(seconds=5)
            wl = self._current_wavelength_intentisies
            self.calculate_current_state()
            if wl != self._current_wavelength_intentisies:
                self.logger.info("{0:05d} @ {1}".format(self._current_csv_index, self.current_timepoint.isoformat()))

    def send_state(self):
        intensities = " ".join(str(v) for k, v in sorted(self._current_wavelength_intentisies.items()))
        cmd = "{} {}".format(self.set_all_wl_command, intensities)
        while not self.do_telnet_command(cmd):
            self.logger.error("Failure running telnet command.")

    def do_telnet_command(self, cmd: str)->bool:
        """
        sends a telnet command to the host
        :param cmd:
        :return: bool successful
        """
        telnet = Telnet(self.telnet_address[0], self.telnet_address[1], 60)
        response = telnet.read_until(b'>', timeout=0.1)
        self.logger.debug("Intial response is: {0!s}".format(response.decode()))

        # we MUST wait a little bit before writing to ensure that the stream isnt being written to.
        time.sleep(0.5)
        # encode to ascii and add LF. unfortunately this is not to the telnet spec (it specifies CR LF or LF CR I'm ns)
        asciicmd = cmd.encode("ascii") + b"\n"
        telnet.write(asciicmd)
        # loopwait for 10 seconds with 0.01 second timeout until we have an actual response from the server
        cmd_response = b''
        for x in range(0, int(10.0/0.01)):
            cmd_response = telnet.read_until(b'>', timeout=0.01)
            if cmd_response:
                break
        else:
            self.logger.error("no response from telnet.")

        time.sleep(0.1)
        cmd_response = cmd_response.decode('ascii')
        if 'OK' in cmd_response:
            self.logger.debug("cmd response: {}".format(cmd_response))
            telnet.close()
            return True
        elif 'Error' in cmd_response:
            # raise ValueError('Light parameter error.\ncmd: "{}"\nresponse: "{}"'.format(cmd_response, cmd))
            self.logger.critical('Light parameter error.\ncmd: "{}"\nresponse: "{}"'.format(cmd_response, cmd))
            telnet.close()
            return False
        else:
            telnet.close()
            return False

    def stop(self):
        self.stopper.set()

    def communicate_with_updater(self):
        """
        communication member. This is meant to send some metadata to the updater thread.
        :return:
        """
        try:
            data = dict(
                name=self.camera_name,
                identifier=self.identifier,
                failed=self.failed,
                last_capture=int(self.current_capture_time.strftime("%s")))
            self.communication_queue.append(data)
            self.failed = list()
        except Exception as e:
            self.logger.error("thread communication error: {}".format(str(e)))

    def run(self):
        while True and not self.stopper.is_set():
            self.current_capture_time = datetime.datetime.now()
            # checking if enabled and other stuff
            if self.time_to_capture:
                try:
                    raw_image = self.timestamped_imagename
                    self.communicate_with_updater()
                except Exception as e:
                    self.logger.critical("Image Capture error - {}".format(str(e)))
            time.sleep(0.1)


class HelioS10(Light):
    """
    Camera class
    other cameras inherit from this class.
    identifier and usb_address are NOT OPTIONAL
    """

    def __init__(self, identifier: str=None, **kwargs):
        super(HelioS10, self).__init__(identifier=identifier, **kwargs)
        pass

    def re_init(self):
        super(HelioS10, self).re_init()


class HelioS20(Light):
    """
    Camera class
    other cameras inherit from this class.
    identifier and usb_address are NOT OPTIONAL
    """

    def __init__(self, identifier: str=None, **kwargs):
        super(HelioS20, self).__init__(identifier=identifier, **kwargs)
        pass

    def re_init(self):
        super(HelioS20, self).re_init()


class ThreadedLights(Thread):
    def __init__(self, *args, **kwargs):
        if hasattr(self, "identifier"):
            Thread.__init__(self, name=self.identifier)
        else:
            Thread.__init__(self)

        print("Threaded startup")
        super(ThreadedLights, self).__init__(*args, **kwargs)
        self.daemon = True
        if hasattr(self, "config_filename") and hasattr(self, "re_init"):
            SysUtil().add_watch(self.config_filename, self.re_init)


class ThreadedHelioS10(ThreadedLights, HelioS10):
    def __init__(self, *args, **kwargs):
        HelioS10.__init__(self, *args, **kwargs)
        super(ThreadedHelioS10, self).__init__(*args, **kwargs)
    def run(self):
        super(HelioS10, self).run()
#
#
# class ThreadedHelioS20(ThreadedLights, HelioS20):
#     def __init__(self, *args, **kwargs):
#         HelioS20.__init__(self, *args, **kwargs)
#         super(ThreadedHelioS20, self).__init__(*args, **kwargs)
#     def run(self):
#         super(HelioS20, self).run()
