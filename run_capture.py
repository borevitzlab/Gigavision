# -*- coding: utf-8 -*-
"""
Created on Wed May  6 14:26:27 2015

@author: Chuong, Gareth Dunstone
"""


# Python 3.x behavior
# changing to python3.

# from __future__ import absolute_import, division, print_function

from urllib import request, parse
from urllib import error as urlerror
import base64
import os
import io
from datetime import datetime
import numpy as np
import csv
import PIL.Image
from scipy import misc
import time
import yaml
import subprocess
import shutil

# This is for Axis camera
IPVAL = ''
USERVAL = ''
PASSVAL = ''
# Panorama parameters
ImageSize = [1920, 1080]  # [1280, 720]

# Panaroma 48 x 16 = 768
Zoom = 3500 # degree
FieldOfView = [5.6708, 3.1613]  # degree

## Panorama 75 x 25 = 1875
#Zoom = 5500
#FieldOfView = [3.5865, 1.9994]  # degree

## Panorama 95 x 32 = 3040
#Zoom = 7000
#FieldOfView = [2.8354, 1.58065]  # degree

Focus = 8027
TopLeftCorner = [-15.2804, 6.7060] # degree
BottomRightCorner = [147.0061, -23.3940] # degree
Overlap = 40  # percentage of image overlapping
max_no_tries = 3  # to deal with corrupted connection
# URL command patterns
# Ref: https://www.ispyconnect.com/man.aspx?n=Axis



def call_url(url, ip, username, password):
    """
    calls a url and returns the response or none if no data returned.
    :param url:
    :param ip:
    :param username:
    :param password:
    :return:
    """
    parsed_url = 'http://' + url
    parsed_url = parsed_url.format(ip_val=ip)

    password_mgr = request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, None, username, password)
    handler = request.HTTPBasicAuthHandler(password_mgr)
    opener = request.build_opener(handler)
    response = None
    try:
        response = opener.open(parsed_url, timeout=60)
    except urlerror.URLError as e:
        raise Exception("URL error: {}".format(e.reason))
    return response if response is None else response.read()

class Camera(object):
    """
    Camera class for the abstraction of cameras

    """
    def __init__(self):

        # TODO: implemenet loading different sets of these settings from file.
        # probably use something like:
        """
        for key, command in self.config['commands']:
            self.commands[key]=command
        or
        self.commands = dict(self.config['commands']
        """
        self.commands = {}
        self.commands['capture_bitmap'] = '{ip_val}/axis-cgi/bitmap/image.bmp?resolution={width_val}x{height_val}&compression=0'
        self.commands['capture_jpg'] = '{ip_val}/jpg/image.jpg?&resolution={width_val}x{height_val}'
        self.commands['set_pan_tilt'] = '{ip_val}/axis-cgi/com/ptz.cgi?pan={pan_val}&tilt={tilt_val}'
        self.commands['set_pan_tilt_zoom'] = '{ip_val}/axis-cgi/com/ptz.cgi?pan={pan_val}&tilt={tilt_val}&zoom={zoom_val}'
        self.commands['set_zoom'] = '{ip_val}/axis-cgi/com/ptz.cgi?zoom={zoom_val}'
        self.commands['set_focus_mode'] = '{ip_val}/axis-cgi/com/ptz.cgi?autofocus={focus_mode}'
        self.commands['get_zoom'] = '{ip_val}/axis-cgi/com/ptz.cgi?query=position'
        self.commands['ret_get_zoom'] = '*zoom={}*'
        self.commands['get_focus_mode'] = '{ip_val}/axis-cgi/com/ptz.cgi?query=position'
        self.commands['ret_get_focus_mode'] = '*autofocus={}*'
        # TODO: change this to a namedtuple
        self.image_size = [1920, 1080]
        self.ip = "something later"
        self.user = "Admin"
        self.password = "password"

    def capture_bitmap(self):
        """
        Captures a bitmap image and returns the image file as a numpy array.
        :return:
        """
        url = self.commands['capture_bitmap'].format(width_val=self.image_size[0],height_val=self.image_size[1])
        output = call_url(self.url, self.ip, self.user, self.password)
        byte_array = io.BytesIO(output)
        print('Captured successfully')
        image = np.array(PIL.Image.open(byte_array))
        return image


    def capture_jpeg_to_file(self, output_file_name):
        """
        Captures a jpeg image and writes it to a specific filename
        :param output_file_name:
        :return:
        """
        url = self.commmands['capture_jpg'].format(ip_val=self.ip, width_val=self.image_size[0],height_val=self.image_size[1])
        url = 'http://' + url
        jpeg_fh = open(output_file_name, 'wb')
        success = False
        try:
            data = request.urlopen(url)
            jpeg_fh.write(data.read())
            success = True
        except:
            print('Fail to capture JPG image')
        finally:
            jpeg_fh.close()
        print(' Wrote image successfully to ' + output_file_name)
        return success

    def capture_bitmap_to_file(self,output_file_name):
        """
        Captures a bitmap to file and saves the image using PIL
        :param output_file_name:
        :return:
        """
        try:
            image = self.capture_bitmap()
        except Exception as e:
            print('Error when capturing an image: {}'.format(e))
            return False
        try:
            print('Save to ' + output_file_name)
            misc.imsave(output_file_name, image)
            return True
        except Exception as e:
            print('Error when saving an image: {}'.format(e))
            return False


    def set_pan_tilt(self,pan, tilt):
        url = self.commands['set_pan_tilt'].format(pan_val=pan, tilt_val=tilt)
        try:
            call_url(url, self.ip, self.user, self.password)
            return True
        except Exception as e:
            print('Error when setting pan/tilt: {}'.format(e))
            return False


    def set_pan_tilt_zoom(self,pan, tilt, zoom):
        url = self.commands['set_pan_tilt_zoom'].format(pan_val=pan,tilt_val=tilt,zoom_val=zoom)
        try:
            call_url(url, self.ip, self.user, self.password)
            return True
        except Exception as e:
            print('Error when setting pan/tilt: {}'.format(e))
            return False


    def set_zoom(self,zoom):
        url = self.commands['set_zoom'].format(zoom_val=zoom)
        try:
            call_url(url, self.ip, self.user, self.password)
            return True
        except Exception as e:
            print('Error when setting zoom: {}'.format(e))
            return False


    def get_zoom(self):
        output = call_url("http://"+self.commands['get_zoom'], self.ip, self.user, self.password)
        if output is None:
            print("something went wrong getting the zoom")
            return None
        return self.extract_info(output, self.commands['ret_get_zoom'])


    def set_autofocus_mode(self,FOCUSMODE):
        url = self.commands['set_focus_mode'].replace("FOCUSMODE", str(FOCUSMODE))
        print(url)
        try:
            call_url(url, self.ip, self.user, self.password)
            return True
        except Exception as e:
            print('Error when setting autofocus mode: {}'.format(e))
            return False


    def is_camera_available(self):
        try:
            self.get_zoom()
            return True
        except:
            return False


    def extract_info(self, input_text, return_string):
            string_list = return_string.split("*")
            string_list = [s for s in string_list if len(s)]
            return_values = []
            for s in string_list:
                word_list = s.split("{}")
                word_list = [w for w in word_list if len(w)]
                if len(word_list) == 1:
                    position = input_text.find(word_list[0])
                    if position >= 0:
                        value = input_text[position + len(word_list[0]):]
                        value_list = value.split("\n")
                        return_values.append(value_list[0].strip())
                elif len(word_list) == 2:
                    pos1 = input_text.find(word_list[0])
                    pos2 = input_text.find(word_list[1], pos1 + len(word_list[0]))
                    if pos1 >= 0 and pos2 >= pos1:
                        return_values.append(input_text[pos1 + len(word_list[0]):pos2])
                else:
                    print("Unhandled case {}". format(s))
            return return_values[0]


    def read_run_info(self,file_name):
        with open(file_name, 'r') as f:
            csvread = csv.DictReader(f)
            config = {"Index": [], "Col": [], "Row": [],
                         "PanDeg": [], "TiltDeg": [],
                         "Zoom": [], "Focus": [], "FileName": []}
            for row in csvread:
                config["Index"].append(int(row["Index"]))
                config["Col"].append(int(row["Col"]))
                config["Row"].append(int(row["Row"]))
                config["PanDeg"].append(float(row["PanDeg"]))
                config["TiltDeg"].append(float(row["TiltDeg"]))
                config["Zoom"].append(int(row["Zoom"]))
                config["Focus"].append(row["Focus"])
                config["FileName"].append(row["FileName"])
            return config
        return None


    def write_run_info(self,file_name, config):
        with open(file_name, 'w') as f:
            field_names = ["Index", "Col", "Row", "PanDeg", "TiltDeg", "Zoom",
                          "Focus", "FileName"]
            f.write(','.join(field_names))
            for i in range(len(config["Index"])):
                row = [str(config[key][i]) for key in field_names]
                f.write('\n' + ','.join(row))
            return True
        return False


    def get_pano_folder(self,root_folder, camera_name, no_pano_in_same_hour=-1):
        time_now = datetime.now()
        if no_pano_in_same_hour < 0:
            # no hour subfolder
            pano_folder = os.path.join(
                root_folder,
                camera_name,
                time_now.strftime("%Y"),
                time_now.strftime("%Y_%m"),
                time_now.strftime("%Y_%m_%d"),
                time_now.strftime("%Y_%m_%d_%H"))
            if not os.path.exists(pano_folder):
                os.makedirs(pano_folder)
                return pano_folder
        else:
            # create hour subfolders
            pano_folder = os.path.join(
                root_folder,
                camera_name,
                time_now.strftime("%Y"),
                time_now.strftime("%Y_%m"),
                time_now.strftime("%Y_%m_%d"),
                time_now.strftime("%Y_%m_%d_%H"),
                "{}_{}_{:02}".format(camera_name,
                                     time_now.strftime("%Y_%m_%d_%H"),
                                     no_pano_in_same_hour))
            if not os.path.exists(pano_folder):
                os.makedirs(pano_folder)
                return pano_folder
            return None


    def get_file_name(self,pano_folder, camera_name, pano_image_number, extension='jpg'):
        time_now = datetime.now()
        file_name = os.path.join(pano_folder,
                                "{}_{}_00_00_{:04}.{}".format(
                                    camera_name,
                                    time_now.strftime("%Y_%m_%d_%H_%M"),
                                    pano_image_number, extension))
        return file_name


    def set_focus_at(self,pan_degress, tilt_degrees, zoom):
        # set focus at the middle of field of view
        # this may work only with Axis camera
        self.set_autofocus_mode("on")
        self.set_zoom(zoom)
        self.set_pan_tilt(pan_degress, tilt_degrees)
        time.sleep(5)
        self.capture_bitmap()
        self.set_autofocus_mode("off")

    def save_black_image_to_file(self,output_file_name):
        black_img = np.zeros([self.image_size[1], self.image_size[0], 3], dtype=np.uint8)
        try:
            misc.imsave(output_file_name, black_img)
        except:
            print('Failed to save empty image')

    def create_panorama_summary(self,image_folder, max_width=4096):
        def scale(input_folder, output_folder, output_size, file_p):
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            cmd = ['mogrify', '-scale',
                       str(output_size), '-path', output_folder, file_p]
            return subprocess.call(cmd, cwd=input_folder)
        # Load running info
        config = self.read_run_info(os.path.join(image_folder, '_data', 'RunInfo.csv'))

        # Get total width of joined image
    #    FilePath = os.path.join(ImageFolder,
    #                            os.path.basename(RunConfig['FileName'][0]))
        import glob
        file_list = glob.glob(os.path.join(image_folder, '*.jpg'))
        file_list.sort()
        file_path = file_list[0]

        image_width = misc.imread(file_path).shape[1]
        joint_width = image_width*config['Col'][-1]

        output_percentage = '{:0.3f}%'.format(100*float(max_width)/float(joint_width))
        scaled_folder = os.path.join(image_folder, '_data', 'scale')
        file_pattern = '*.jpg'
        ret = scale(image_folder, scaled_folder, output_percentage, file_pattern)
        print(ret)

        # Scaled total size
    #    ScaledFilePath = os.path.join(ScaledFolder,
    #                                  os.path.basename(RunConfig['FileName'][0]))
        scaled_file_path = os.path.join(scaled_folder, os.path.basename(file_list[0]))
        self.image_size = misc.imread(scaled_file_path).shape
        print(self.image_size)
        joint_size = [self.image_size[0]*(RunConfig['Row'][-1]+1),
                     self.image_size[1]*(RunConfig['Col'][-1]+1),
                     self.image_size[2]]
        # Create scaled joint image
        if self.image_size[0]*self.image_size[1]*self.image_size[2] < 4096*4096*3:
            joint_image = np.zeros(joint_size, dtype=np.uint8)
        else:
            print('Error: joint image size {} is too large'.format(self.image_size))
            exit(-1)
        for i in config['Index']:
    #        scaled_file_path = os.path.join(
    #            scaled_folder, os.path.basename(RunConfig['FileName'][i]))
            scaled_file_path = os.path.join(scaled_folder,
                                          os.path.basename(file_list[i]))
            scaled_image = misc.imread(scaled_file_path)
            iCol = RunConfig['Col'][i]
            jRow = RunConfig['Row'][i]
            joint_image[jRow*self.image_size[0]:(jRow+1)*self.image_size[0],
                       iCol*self.image_size[1]:(iCol+1)*self.image_size[1], :] = scaled_image
        joint_file_path = os.path.join(image_folder, '_data', 'joint_image.jpg')
        misc.imsave(joint_file_path, joint_image)

        # Remove the scale folder
        shutil.rmtree(scaled_folder)

if __name__ == '__main__':
    # settings information
    # TODO: makes these commandline options
    RootFolder = '/media/TBUltrabookBackup/phenocams'
#    RootFolder = '/home/chuong/data/phenocams'
    CameraName = 'ARB-GV-HILL-1'
    StartHour = 8
    EndHour = 18
    LoopIntervalMinute = 60  # take panoram every 1 hour
    PanoWaitMin = 15  # minutes
    DelayBetweenColumns = 3  # seconds
    DelayBetweenImages = 0.5  # seconds
    MultiRunPerHour = False  # ON/OFF hour subfolder
    RunInfoFileName = ''  # '/home/pi/workspace/Gigavision/RunInfo.cvs'
    CamConfigFile = '/home/pi/workspace/Gigavision/AxisCamera_Q6115-E.yml'
#    RunInfoFileName = '/home/chuong/workspace/Gigavision/RunInfo.cvs'
#    CamConfigFile = '/home/chuong/workspace/Gigavision/AxisCamera_Q6115-E.yml'

    CamConfig = yaml.load(open(CamConfigFile, 'r'))
    IPVAL = CamConfig['IPVAL']
    USERVAL = CamConfig['USERVAL']
    PASSVAL = CamConfig['PASSVAL']
    if os.path.exists(RunInfoFileName):
        RunConfig = readRunInfo(RunInfoFileName)
    else:
        print('Generate RunConfig')
        RunConfig = {'Index': [], 'Col': [], 'Row': [],
                     'PanDeg': [], 'TiltDeg': [],
                     'Zoom': [], 'Focus': [], 'FileName': []}
        [LeftPan, TopTilt] = TopLeftCorner
        [RightPan, BottomTilt] = BottomRightCorner
        HFoV, VFoV = FieldOfView
        PanoRows = int(round((TopTilt - BottomTilt)/VFoV/(1.0-Overlap/100.0)))
        PanoCols = int(round((RightPan - LeftPan)/HFoV/(1.0-Overlap/100.0)))
        print('Row = {}, Col = {}'.format(PanoRows, PanoCols))
        Index = 0
        print('Index, Col', 'Row, PanDeg, TiltDeg, Zoom, Focus')
        for iCol in range(PanoCols):
            for jRow in range(PanoRows):
                PanDeg  = TopLeftCorner[0] + iCol*HFoV*(1.0 - Overlap/100.0)
                TiltDeg = TopLeftCorner[1] - jRow*VFoV*(1.0 - Overlap/100.0)
                RunConfig['Index'].append(Index)
                RunConfig['Col'].append(iCol)
                RunConfig['Row'].append(jRow)
                RunConfig['PanDeg'].append(PanDeg)
                RunConfig['TiltDeg'].append(TiltDeg)
                RunConfig['Zoom'].append(Zoom)
                RunConfig['Focus'].append(Focus)
                print('{},{},{},{},{},{},{}'.format(Index, iCol, jRow, PanDeg, TiltDeg, Zoom, Focus))
                Index += 1
    while True:
        Start = datetime.now()
        WithinHourRange = (Start.hour >= StartHour and
                           Start.hour <= EndHour)
        if WithinHourRange:
            # wait until camera is available
            while not isCameraAvailable():
                print('Camera is not available. Check again in 15 min.')
                time.sleep(15*60)  # sleep 15 minute

            # make sure zoom is set at begining
            while True:
                try:
                    setZoom(RunConfig["Zoom"][0])
                    break
                except:
                    print('Sleep 1 secs to set zoom')
                    time.sleep(1)
            while True:
                try:
                    Zoom0 = getZoom()
                    break
                except:
                    print('Sleep 1 secs to get zoom')
                    time.sleep(1)

            # set focus at the middle of field of view
            PanDegMin = min(RunConfig["PanDeg"])
            PanDegMax = max(RunConfig["PanDeg"])
            TiltDegMin = min(RunConfig["TiltDeg"])
            TiltDegMax = max(RunConfig["TiltDeg"])
            PanMiddle = (PanDegMin+PanDegMax)/2
            TiltMiddle= (TiltDegMin+TiltDegMax)/2
            while True:
                try:
                    setFocusAt(PanMiddle, TiltMiddle, RunConfig["Zoom"][0])
                    break
                except:
                    print('Failed to focus the camera. Camera is likely down.')
                    print('Try focusing again in 5 minutes')
                    time.sleep(5*60)

            if MultiRunPerHour:
                for h in range(10):
                    PanoFolder = getPanoFolder(RootFolder, CameraName, h)
                    if PanoFolder is not None:
                        break
            else:
                PanoFolder = getPanoFolder(RootFolder, CameraName)

            setPanTiltZoom(RunConfig["PanDeg"][0], RunConfig["TiltDeg"][0],
                           RunConfig["Zoom"][0])
            time.sleep(3)
            RunConfig['FileName'] = []
            for i in RunConfig["Index"]:
                ImageFileName = getFileName(PanoFolder, CameraName, i, 'jpg')
                RunConfig['FileName'].append(ImageFileName)
                j = 0
                while j < max_no_tries:
                    if setPanTiltZoom(RunConfig["PanDeg"][i],
                                      RunConfig["TiltDeg"][i],
                                      RunConfig["Zoom"][i]):
                        break
                    else:
                        j += 1
                        time.sleep(1)

                # check if it is moving to the next column
                if i > 0 and RunConfig["Col"][i-1] != RunConfig["Col"][i]:
                    # move to next column needs more time
                    time.sleep(DelayBetweenColumns)
                    print('Sleep {} secs between columns'.format(DelayBetweenColumns))
                else:
                    time.sleep(DelayBetweenImages)

                while j < max_no_tries:
#                    if captureImage2File(ImageFileName):  # crash reset the camera after certain number of images
                    if captureJPGImage2File(ImageFileName):
                        break
                    else:
                        j += 1
                        print('Failed to capture an image. Try again.')
                        time.sleep(1)
                if j >= max_no_tries:
                    print('Fail to capture an image after {} tries.'
                          ' Save a black image.'.format(max_no_tries))
                    saveBlackImage2File(ImageFileName)

            # write panoram config file
            os.makedirs(os.path.join(PanoFolder, '_data'))
            RunConfigFile = os.path.join(PanoFolder, '_data', 'RunInfo.csv')
            writeRunInfo(RunConfigFile, RunConfig)
            createPanoramaSummary(PanoFolder)

            print('Finished one panorama')

            # wait until next hour
            while True:
                End = datetime.now()
                Quotient, Remainder = divmod((End.hour*60 + End.minute),
                                             LoopIntervalMinute)
                if Remainder <= PanoWaitMin:
                    break
                DueTime = (Quotient+1)*LoopIntervalMinute
                WaitMin = DueTime - (End.hour*60 + End.minute)
                print("Wait for {} minutes before start.".format(WaitMin))
                time.sleep(WaitMin*60)
        else:
            # sleep until start of hour range
            Now = datetime.now()
            DueTime = StartHour*60
            WaitMin = DueTime - (Now.hour*60 + Now.minute)
            if WaitMin < 0:
                DueTime = (24 + StartHour)*60
                WaitMin = DueTime - (Now.hour*60 + Now.minute)   
            Hours, Mins = divmod(WaitMin, 60)
            print("Wait {} hours and {} minutes".format(Hours, Mins))
            time.sleep(WaitMin*60)
