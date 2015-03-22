#!/usr/bin/env python
import socket, os, hashlib, subprocess, signal
import Crypto.Protocol.KDF
import anydbm
import datetime, re, fnmatch, shutil
import cPickle
import copy
import tarfile
import shutil
import time
from glob import glob
from functools import wraps
from flask import Flask, send_from_directory,redirect, url_for, request, send_file, abort, Response, render_template, jsonify
from ConfigParser import SafeConfigParser

config_filename = 'eyepi.ini'
otherconfig_filename = 'picam.ini'
example_filename = 'example.ini'

app = Flask(__name__, static_url_path='/static')
app.debug = True

"""    
          d8  
        ,8P'  
       d8"    
     ,8P'     
    d8"       
  ,8P'        
 d8"          
8P'           
              
              
"""
global counter
counter = 0

@app.route
def remove_tars():
	tars = glob(os.path.join(os.getcwd(),"*.tar"))
	for tar in tars:
		os.remove(tar)

@app.route("/killgphoto2")
def killgphoto2():
	p = subprocess.Popen(['ps', '-A'],stdout=subprocess.PIPE)
	out, err = p.communicate()
	gphotos_killed = 0
	for line in out.splitlines():
		if "gphoto2" in line:
			pid = int(line.split(None,1)[0])
			os.kill(pid,signal.SIGKILL)
			gphotos_killed +=1
	return "<html><body>gphoto2s killed: "+str(gphotos_killed)+"</body></html>"

def make_tar(path):
	try:
		full_path = os.path.abspath(os.path.join(os.getcwd(),path))
		with tarfile.open(str(path+".tar"),"w:") as tar:
			tar.add(full_path, arcname=str(path))
		#shutil.rmtree(full_path)
	except Exception as e:
		return abort(501)
	return send_from_directory(os.getcwd(),path+".tar",as_attachment=True)

@app.route("/get_tar_file",methods=['GET'])
def get_tar_file():
	if request.method == 'GET' and request.args["path"]:
		full_path = os.path.abspath(os.path.join(os.getcwd(),request.args["path"]))
		path=request.args["path"]
		if os.path.isdir(full_path):
			make_tar(path)
			return send_from_directory(os.getcwd(),path+".tar", as_attachment=True)
		elif os.path.isfile(os.path.join(os.getcwd(),path+".tar")):
			return send_from_directory(os.getcwd(),path+".tar", as_attachment=True)
		else:
			abort(404)
	else:
		return abort(400)


def get_images_from_camera(path):
	full_path = os.path.abspath(os.path.join(os.getcwd(),path))
	if not os.path.isdir(full_path):
		os.mkdir(full_path)
		try:
			a = subprocess.check_output("gphoto2 --get-all-files --filename='"+str(os.path.abspath(full_path))+"/"+path+"-%04n.%C' --force-overwrite ",shell=True)
			b = subprocess.check_output("gphoto2 --delete-all-files",shell=True)
			return full_path
		except CalledProcessError as e:
			return abort(400)
	else:
		return abort(400)

@app.route('/download_images_from_camera' ,methods=["GET"])
def download_images_from_camera():
	if request.method == 'GET' and request.args['path']:
		global counter
		counter = 0
		images_path = get_images_from_camera(request.args['path'])
		return "<html><body>Success</body></html>"
	else:
		return abort(400)

@app.route('/')
def config():
	a = subprocess.check_output("gphoto2 --auto-detect",shell=True)
	return "<html><body> <h1>GIGAVISION CAMERA CONTROL!<br></h1>"+a.replace("\n",'<br>')+"</body></html>"

def capture_photo():
	global counter
	try:
		a = subprocess.check_output("gphoto2 --capture-image",shell=True)
		counter += 1
		return True
	except subprocess.CalledProcessError as e:
		return False

def capture_preview():
	try:
		a=subprocess.check_output("gphoto2 --capture-preview --force-overwrite --filename='static/shm/preview.jpg'",shell=True)
	except subprocess.CalledProcessError as e:
		print str(e)

def capture_preview_picam():
	try:
		os.system("/opt/vc/bin/raspistill --nopreview -o /dev/shm/preview_pi.jpg")
	except Exception as e:
		print str(e)

@app.route("/preview")
def preview():
	preview = capture_preview()
	return "<html><body><img src="+url_for("static", filename="shm/preview.jpg")+"> </img></body></html>"

@app.route("/preview_picam")
def preview_picam():
	preview = get_preview_picam()
	return "<html><body><img src="+url_for("static", filename="shm/preview_pi.jpg")+"> </img></body></html>"


@app.route("/preview_and_capture")
def preview_and_capture():
	preview = capture_preview()
	if capture_photo():
		return "<html><body><img src="+url_for("static", filename="shm/preview.jpg")+"> </img></body></html>"
	else:
		return abort(503)

@app.route("/set_counter", methods=["GET"])
def set_counter():
	global counter
	if request.method == "GET" and request.args["counter"]:
		counter = int(request.args["counter"])
	return "<html>"+str(counter)+"</html>"

@app.route("/get_counter")
def get_counter():
	global counter
	return "<html>"+str(counter)+"</html>"

@app.route("/capture")
def capture():
	global counter
	if capture_photo():
		return "<html>"+str(counter)+"</html>"
	else:
		return abort(503)

"""                                           
                                                            88                                           
                                                            ""                                           
                                                                                                         
                            88,dPYba,,adPYba,   ,adPPYYba,  88  8b,dPPYba,                               
                            88P'   "88"    "8a  ""     `Y8  88  88P'   `"8a                              
                            88      88      88  ,adPPPPP88  88  88       88                              
                            88      88      88  88,    ,88  88  88       88                              
                            88      88      88  `"8bbdP"Y8  88  88       88                              
                                                                                                         
888888888888  888888888888                                                   888888888888  888888888888  
"""
if __name__ == "__main__":
	app.run(host='0.0.0.0')

