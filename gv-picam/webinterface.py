#!/usr/bin/env python
import socket, os, hashlib, subprocess
import Crypto.Protocol.KDF
import anydbm
import datetime, re, fnmatch, shutil
import cPickle
import copy
from glob import glob
from functools import wraps
from flask import Flask, redirect, url_for, request, send_file, abort, Response, render_template, jsonify
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

def tarzipphotos():
	pass

def istarzipready():
	return None

@app.route('/')
def config():
	a = subprocess.check_output("gphoto2 --auto-detect",shell=True)
	return "<html><body> <h1>GIGAVISION CAMERA CONTROL!<br></h1>"+a.replace("\n",'<br>')+"</body></html>"

@app.route('/download')
def download():
	try:
		a = subprocess.check_output("gphoto2 --get-all-files --force-overwrite",shell=True)
		return "<h1>done</h1><br>"
	except subprocess.CalledProcessError as e:
		return 404
	return "<html><body> <h1>donesies</h1></body></html>"

@app.route("/capture")
def capture():
	try:
		a = subprocess.check_output("gphoto2 --capture",shell=True)
		return "<h1>done"+a+"</h1>"
	except subprocess.CalledProcessError as e:
		return "<h1>broken"+e+"</h1>"



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

