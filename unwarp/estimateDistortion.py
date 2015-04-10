# -*- coding: utf-8 -*-
"""
Created on Tue May 13 11:03:53 2014

@author: Chuong Nguyen, chuong.nguyen@anu.edu.au
"""
from __future__ import absolute_import, division, print_function

import numpy as np
import cv2
import sys, getopt, os
#from multiprocessing import Pool
import datetime


def getTargetPhysicalPoints(GridSize, SquareSize):
    ObjPoints = np.zeros( (np.prod(GridSize), 3), np.float32 )
    ObjPoints[:,:2] = np.indices(GridSize).T.reshape(-1, 2)
    ObjPoints *= SquareSize
    return ObjPoints
        
def readNameListFromFile(FileName, StepSize = 1, Path=''):
    Path = os.path.dirname(os.path.join(Path, FileName))
    with open (os.path.join(Path, FileName), 'r') as myfile:
        NameList=[line.rstrip() for line in myfile]
    return NameList[::StepSize], Path

def detectTargetImagePoints(FileName, PatternType, GridSize):
    Criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    print('  Process ' + FileName)
    # Read image and convert to grayscale
    Img = cv2.imread(FileName)
    Gray = cv2.cvtColor(Img, cv2.COLOR_BGR2GRAY)

    if PatternType.lower() in 'chessboard':
        # detect pattern in pyramid fashion to speed up detection process
        PyramidLevels = 1 + int(round(np.log(Gray.shape[1] / 1024.0) / np.log(2.0)))
        for i in range(PyramidLevels):
            if i == 0:
                PyramidGrays = [Gray]
            else:
                PyramidGrays.append(cv2.pyrDown(PyramidGrays[i-1]))

        # start from the top of 
        ret, ImgPoints = cv2.findChessboardCorners(PyramidGrays[PyramidLevels-1], GridSize, None)
        if ret == False:
            return np.array([]), Img.shape[2::-1]
        else:
            for i in range(PyramidLevels-1, -1, -1):
                if i != PyramidLevels-1:
                    ImgPoints = ImgPoints*2.0
                cv2.cornerSubPix(PyramidGrays[i], ImgPoints,(11,11),(-1,-1), Criteria)

#                cv2.drawChessboardCorners(PyramidGrays[i], GridSize, ImgPoints, ret)
#                cv2.imshow('Detected Corners', cv2.resize(PyramidGrays[i], PyramidGrays[PyramidLevels-1].shape[::-1]))
#                cv2.moveWindow('Detected Corners', 0,0)
#                cv2.waitKey(2000)
#                cv2.destroyAllWindows()

            return ImgPoints.reshape(-1, 2), Img.shape[1::-1]
    else:
        print( PatternType + ' is not currently supported')
        return np.array([]), Img.shape[2::-1]

def calibrateCamera(ObjPointsList, ImgPointsList2, ImageSize, Flags):
    RMS, CameraMatrix, DistCoefs, RVecs, TVecs = \
        cv2.calibrateCamera(ObjPointsList, ImgPointsList2, ImageSize, \
        None, None, None, None, Flags)
    return RMS, CameraMatrix, DistCoefs, RVecs, TVecs


def saveCalibrationData(CalibFileName, SquareSize, ImageSize, CameraMatrix, DistCoefs, RVecs, TVecs, RMS):
    with open (CalibFileName, 'w') as myfile:
        print('  Write to ' + CalibFileName)
        myfile.write('%YAML:1.0\n')
        myfile.write('calibration_time: "' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '"\n')
        myfile.write('calibration_RMS: %f\n' %RMS)
        myfile.write('# physical square size [mm] or distance between control points\n')
        myfile.write('# if it equals 1, the physical size is not provided\n')
        myfile.write('square_size: %f\n' %SquareSize)    
        myfile.write('image_width: %d\n' %ImageSize[0])
        myfile.write('image_height: %d\n' %ImageSize[1])
        myfile.write('camera_matrix: !!opencv-matrix\n')
        myfile.write('   rows: 3\n')
        myfile.write('   cols: 3\n')
        myfile.write('   dt: d\n')
        myfile.write('   data: [ %f, %f, %f, %f, %f, %f, %f, %f, %f]\n' \
            %(CameraMatrix[0,0], CameraMatrix[0,1], CameraMatrix[0,2], \
              CameraMatrix[1,0], CameraMatrix[1,1], CameraMatrix[1,2], \
              CameraMatrix[2,0], CameraMatrix[2,1], CameraMatrix[2,2]))
        myfile.write('distortion_coefficients: !!opencv-matrix\n')
        myfile.write('   rows: 5\n')
        myfile.write('   cols: 1\n')
        myfile.write('   dt: d\n')
        myfile.write('   data: [ %f, %f, %f, %f, %f]\n' \
                %(DistCoefs[0][0], DistCoefs[0][1], DistCoefs[0][2], DistCoefs[0][3], DistCoefs[0][4]))
        myfile.write('# rotation vectors of the camera\n')
        myfile.write('RVecs: !!opencv-matrix\n')
        myfile.write('   rows: %d\n' %len(RVecs))
        myfile.write('   cols: 3\n')
        myfile.write('   dt: d\n')
        myfile.write('   data: [ ')
        datalist = []
        for RVec in RVecs:
            datalist = datalist + ['%f' %RVec[0], '%f' %RVec[1], '%f' %RVec[2]]
        myfile.write(', '.join(datalist))
        myfile.write('         ]\n')
                
        myfile.write('# translation vectors of the camera\n')
        myfile.write('TVecs: !!opencv-matrix\n')
        myfile.write('   rows: %d\n' %len(TVecs))
        myfile.write('   cols: 3\n')
        myfile.write('   dt: d\n')
        myfile.write('   data: [ ')
        datalist = []
        for TVec in TVecs:
            datalist = datalist + ['%f' %TVec[0], '%f' %TVec[1], '%f' %TVec[2]]
        myfile.write(', '.join(datalist))
        myfile.write('         ]\n')

def main(argv):
    HelpString = 'estimateDistortion.py -i <image list file>' + \
                    '-W <pattern width> -H <pattern height> -S <square size>' + \
                    '-o <output file>' + \
                 'Example:\n' + \
                 "$ ./estimateDistortion.py -i /home/chuong/Data/GC03L-temp/image_list.txt -o /home/chuong/Data/GC03L-temp/IMG_6425/calib_param.yml"
    try:
        opts, args = getopt.getopt(argv,"hi:W:H:S:o:",["ifile=","gwidth=","gheight=","ssize=","ofolder="])
    except getopt.GetoptError:
        print(HelpString)
        sys.exit(2)
    if len(opts) == 0:
        print(HelpString)
        sys.exit()
        
    
    InputListFile = ''
    OutputFile = ''  
    GridWidth = 12
    GridHeight = 12
    SquareSize = 40.0 #mm
    PatternType = 'chessboard'
#    Flags = cv2.CALIB_FIX_ASPECT_RATIO + cv2.CALIB_ZERO_TANGENT_DIST
    Flags = cv2.CALIB_FIX_PRINCIPAL_POINT + \
            cv2.CALIB_FIX_ASPECT_RATIO #+ \
#            cv2.CALIB_ZERO_TANGENT_DIST #+ \
#            cv2.CALIB_FIX_K3
    for opt, arg in opts:
        if opt == '-h':
            print(HelpString)
            sys.exit()
        elif opt in ("-i", "--ifile"):
            InputListFile = arg
        elif opt in ("-W", "--gwidth"):
            GridWidth = int(arg)
        elif opt in ("-H", "--gheight"):
            GridHeight = int(arg)
        elif opt in ("-S", "--ssize"):
            SquareSize = float(arg)
        elif opt in ("-o", "--ofile"):
            OutputFile = arg
            
    GridSize = (GridWidth, GridHeight)    
    ObjPoints = getTargetPhysicalPoints(GridSize, SquareSize)

    NameList, Path = readNameListFromFile(InputListFile)
    NameList = filter(None, NameList)

    ImgPointsList = []
    ObjPointsList = []
    for FileName in NameList:
        ImgPoints, ImageSize = detectTargetImagePoints(os.path.join(Path, FileName), PatternType, GridSize)
        if len(ImgPoints) == 0:
            print('Cannot detect pattern from', FileName)
            continue
        ImgPointsList.append(ImgPoints)
        ObjPointsList.append(ObjPoints)
        
    RMS, CameraMatrix, DistCoefs, RVecs, TVecs = \
        calibrateCamera(ObjPointsList, ImgPointsList, ImageSize, Flags) 
    print('Calibration RMS = %f' %RMS)
    
    saveCalibrationData(OutputFile, SquareSize, ImageSize, CameraMatrix, DistCoefs, RVecs, TVecs, RMS)
    
if __name__ == "__main__":
   main(sys.argv[1:])