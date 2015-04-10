# -*- coding: utf-8 -*-
"""
Created on Tue May 13 14:37:47 2014

@author: chuong nguyen, chuong.nguyen@anu.edu.au
"""
from __future__ import absolute_import, division, print_function

import cv2
import sys, getopt
import os
import numpy as np
from multiprocessing import Pool
import glob


def readValueFromLineYML(line):
    name = line[:line.index(':')].strip()
    string = line[line.index(':')+1:].strip()
    if string[0] in '-+0123456789':
        if '.' in string:
            value =  float(string)
        else:
            value = int(string)
    else:
        value = string
        
    return name, value

def readOpenCVArrayFromYML(myfile):
    line = myfile.readline().strip()
    rname, rows = readValueFromLineYML(line)
    line = myfile.readline().strip()
    cname, cols = readValueFromLineYML(line)
    line = myfile.readline().strip()
    dtname, dtype = readValueFromLineYML(line)
    line = myfile.readline().strip()
    dname, data = readValueFromLineYML(line)
    if rname != 'rows' and cname != 'cols' and dtname != 'dt' \
        and dname != 'data' and '[' in data:
        print('Error reading YML file')
    elif dtype != 'd':
        print('Unsupported data type: dt = ' + dtype)
    else:
        if ']' not in data:
            while True:
                line = myfile.readline().strip()
                data = data + line
                if ']' in line:
                    break
        data = data[data.index('[')+1 : data.index(']')].split(',')
        dlist = [float(el) for el in data]
        if cols == 1:
            value = np.asarray(dlist)
        else:
            value = np.asarray(dlist).reshape([rows, cols])
    return value

def parseYML(YMLFile):
    with open (YMLFile, 'r') as myfile:
        print('  Read ' + YMLFile)
        parameters = {}
        while True:
            line = myfile.readline()
            if not line:
                break
            
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue
            
            if ':' in line:
                name, value = readValueFromLineYML(line)

                # if OpenCV array, do extra reading
                if isinstance(value, str) and 'opencv-matrix' in value:
                    value = readOpenCVArrayFromYML(myfile)

                # add parameters
                parameters[name] = value

    return parameters
    
def readCalibration(CalibFile):
    parameters = parseYML(CalibFile)

    SquareSize = parameters['square_size']
    ImageWidth = parameters['image_width']
    ImageHeight = parameters['image_height']
    ImageSize = (ImageWidth, ImageHeight)
    CameraMatrix = parameters['camera_matrix']
    DistCoefs = parameters['distortion_coefficients']
    RVecs = parameters['RVecs']
    TVecs = parameters['TVecs']
                    
    return ImageSize, SquareSize, CameraMatrix, DistCoefs, RVecs, TVecs
        
def readNameListFromFile(FileName, StepSize = 1, Path=''):
    with open (os.path.join(Path, FileName), 'r') as myfile:
        NameList=[line.rstrip() for line in myfile]
    Path = os.path.dirname(os.path.join(Path, FileName))
    return NameList[::StepSize], Path

# source: http://stackoverflow.com/questions/9041681/opencv-python-rotate-image-by-x-degrees-around-specific-point
def rotateImage(image, angle):
    center=tuple(np.array(image.shape[0:2])/2)
    rot_mat = cv2.getRotationMatrix2D(center,angle,1.0)
    return cv2.warpAffine(image, rot_mat, image.shape[0:2],flags=cv2.INTER_LINEAR)
    
def undistortImage(Arg):
    InputImageFile, OutputImageFile, MapX, MapY, RotationAngle = Arg
    print('  Process ' + InputImageFile)
    Image = cv2.imread(InputImageFile)
    ImageUndistorted = cv2.remap(Image, MapX, MapY, cv2.INTER_CUBIC)
    
    if abs(RotationAngle) == 180:
        ImageUndistorted = np.rot90(np.rot90(ImageUndistorted))
    elif RotationAngle != 0:
        ImageUndistorted = rotateImage(rotateImage, RotationAngle)
        
    ok = cv2.imwrite(OutputImageFile, ImageUndistorted)
    if not ok:
        print('Cannot write ' + OutputImageFile)

def main(argv):
    HelpString = 'undistortImages.py -i <input txt files> -c <calibration file> ' + \
                 '    [-o <output folder>] [-f]\n' + \
                 'Example:\n' + \
                 "$ ./undistortImages.py -i '/home/chuong/Data/GC03L-temp/*JPG' -c /home/chuong/Data/Calibration-Images/calib_parameters.yml -o corrected/"
    try:
        opts, args = getopt.getopt(argv,"hfi:c:r:o:",["ifiles=","calibfile=","rotation=", "outputfolder="])
    except getopt.GetoptError:
        print(HelpString)
        sys.exit(2)
    if len(opts) == 0:
        print(HelpString)
        sys.exit()
        
    InputFileList = []
    CalibFile = './camera_calibration.yml'
    OutputFolder = './corrected/'
    Forced = False
    RotationAngle = 0
    for opt, arg in opts:
        if opt == '-h':
            print(HelpString)
            sys.exit()
        elif opt in ("-f", "--forced"):
            Forced = True
        elif opt in ("-i", "--ifiles"):
            InputFileList.append(arg)
        elif opt in ("-o", "--outputfolder"):
            OutputFolder = arg
        elif opt in ("-c", "--calibfile"):
            CalibFile = arg
        elif opt in ("-r", "--rotation"):
            RotationAngle = float(arg)
    
    print('# Start a pool of multicore processes')
    ProcPool = Pool()
    
    print('Read calibration file')
    ImageSize, SquareSize, CameraMatrix, DistCoefs, RVecs, TVecs = readCalibration(CalibFile)
        
    InputFiles = []
    for n,InputFile in enumerate(InputFileList):
        if InputFile.endswith('.txt'):
            with open(InputFile, 'r') as text_file:
                FileList = [os.path.join(os.path.dirname(InputFile), line.strip()) for line in text_file]
                InputFiles = InputFiles + FileList
        else:
            InputFiles = InputFiles + sorted(glob.glob(InputFile))

    print('# Undistort images')
    MapX, MapY = cv2.initUndistortRectifyMap(CameraMatrix, DistCoefs, \
        None, CameraMatrix, ImageSize, cv2.CV_32FC1)
    ArgList = []
    for InputName in InputFiles:
        if OutputFolder[0] != os.path.sep:
            OutputFolder2 = os.path.join(os.path.dirname(InputName), OutputFolder)
        else:
            OutputFolder2 = OutputFolder
        if not os.path.exists(OutputFolder2):
            os.makedirs(OutputFolder2) 
        OutputName = os.path.join(OutputFolder2, os.path.basename(InputName))
        ArgList.append([InputName, OutputName, MapX, MapY, RotationAngle])
        
#    for Arg in ArgList:
#        undistortImage(Arg)
    ProcPool.map(undistortImage, ArgList)
        
if __name__ == "__main__":
   main(sys.argv[1:])
