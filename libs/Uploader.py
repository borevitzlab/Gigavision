import datetime
import ftplib
import logging
import os
import time
from glob import glob
from collections import deque
from threading import Thread, Event
import pysftp
from .CryptUtil import SSHManager
from .SysUtil import SysUtil

try:
    logging.config.fileConfig("logging.ini")
    logging.getLogger("paramiko").setLevel(logging.WARNING)
except:
    pass


class Uploader(Thread):
    """ Uploader class,
        used to upload,
    """
    # upload interval
    upload_interval = 120
    remove_source_files = True

    def __init__(self, identifier: str, queue: deque = None):
        # same thread name hackery that the Camera threads use
        Thread.__init__(self, name=identifier + "-Uploader")
        self.stopper = Event()
        if queue is None:
            queue = deque(tuple(), 256)

        self.communication_queue = queue
        self.identifier = identifier
        self.logger = logging.getLogger(self.getName())
        self.startup_time = datetime.datetime.now()

        self.ssh_manager = SSHManager()
        self.machine_id = SysUtil.get_machineid()
        self.last_upload_time = datetime.datetime.fromtimestamp(0)
        self.last_upload_list = []
        self.total_data_uploaded_tb = 0
        self.total_data_uploaded_b = 0

        self.config_filename = SysUtil.identifier_to_ini(self.identifier)
        self.config = \
            self.hostname = \
            self.username = \
            self.password = \
            self.camera_name = \
            self.source_dir = \
            self.server_dir = \
            self.upload_enabled = None

        self.re_init()
        SysUtil().add_watch(self.config_filename, self.re_init)

    def re_init(self):
        """
        setup to be run each time the config is reloaded

        """
        self.machine_id = SysUtil.get_machineid()
        self.config = SysUtil.ensure_config(self.identifier)
        self.hostname = self.config["ftp"]["server"]
        self.username = self.config["ftp"]["username"]
        self.password = self.config["ftp"]["password"]
        self.server_dir = self.config["ftp"]["directory"]
        self.camera_name = self.config["camera"]["name"]
        self.source_dir = self.config["localfiles"]["upload_dir"]
        self.upload_enabled = self.config.getboolean("ftp", "enabled")
        self.last_upload_list = []

    def upload(self, file_names):
        """
        uploads files via sftp.
        deletes the files as they are uploaded, creates new directories if needed.

        :param file_names: filenames to upload
        """
        try:
            self.logger.debug("Connecting sftp and uploading buddy")
            # open link and create directory if for some reason it doesnt exist
            params = dict(host=self.hostname, username=self.username)
            params['cnopts'] = pysftp.CnOpts(knownhosts='/home/.ssh/known_hosts')
            params['cnopts'].hostkeys = None

            if os.path.exists("/home/.ssh/id_rsa") and os.path.exists('/home/.ssh/known_hosts'):
                params['private_key'] = "/home/.ssh/id_rsa"
                params['cnopts'] = pysftp.CnOpts(knownhosts='/home/.ssh/known_hosts')
            else:
                params['password'] = self.password

            with pysftp.Connection(**params) as link:
                root = os.path.join(self.server_dir, self.camera_name)
                # make the root dir in case it doesnt exist.
                self.mkdir_recursive(link, root)
                self.logger.debug("Uploading...")

                # dump ze files.
                for f in file_names:
                    target_file = f.replace(self.source_dir, os.path.join(self.server_dir, self.camera_name)).replace("//", "/")
                    link.chdir("/")
                    if os.path.isdir(f):
                        self.mkdir_recursive(link, target_file)
                        continue

                    try:
                        link.put(f, target_file + ".tmp")
                        if link.exists(target_file):
                            link.remove(target_file)
                        link.rename(target_file + ".tmp", target_file)
                        link.chmod(target_file, mode=755)
                        self.total_data_uploaded_b += os.path.getsize(f)
                        if self.remove_source_files:
                            os.remove(f)
                            self.logger.debug(
                                "Successfully uploaded {} through sftp and removed from local filesystem".format(f))
                        else:
                            self.logger.debug("Successfully uploaded {} through sftp".format(f))
                        self.last_upload_time = datetime.datetime.now()
                    except Exception as e:
                        self.logger.error("sftp:{}".format(str(e)))
                self.logger.debug("Disconnecting, eh")
            if self.total_data_uploaded_b > 1000000000000:
                curr = (((self.total_data_uploaded_b / 1024) / 1024) / 1024) / 1024
                self.total_data_uploaded_b = 0
                self.total_data_uploaded_tb = curr
        except Exception as e:
            # log a warning if fail because SFTP is meant to fail to allow FTP fallback
            self.logger.error("SFTP failed: {}".format(str(e)))
            self.logger.debug("Looks like I can't make a connection using sftp, eh. Falling back to ftp.")
            try:
                self.logger.debug("Connecting ftp")
                # open link and create directory if for some reason it doesnt exist
                ftp = ftplib.FTP(self.hostname)
                ftp.login(self.username, self.password)
                self.mkdir_recursive(ftp, os.path.join(self.server_dir, self.camera_name))
                self.logger.info("Uploading")
                # dump ze files.
                for f in file_names:
                    ftp.storbinary('stor ' + os.path.basename(f), open(f, 'rb'), 1024)
                    os.remove(f)
                    self.logger.debug("Successfuly uploaded {} through ftp and removed from local filesystem".format(f))
                    self.last_upload_time = datetime.datetime.now()
            except Exception as e:
                # log error if cant upload using FTP. FTP is last resort.
                self.logger.error(str(e))

    def mkdir_recursive(self, link, remote_directory, mkdir=None, chdir=None):
        """
        Creates directories recursively on the remote server

        :param link: ftp/sftp connection object
        :param remote_directory:
        :param chdir: method used to change to a directory
        :param mkdir: method used to make a directory
        """
        if not (mkdir and chdir):
            if isinstance(link, pysftp.Connection):
                mkdir, chdir = link.mkdir, link.chdir
            elif isinstance(link, ftplib.FTP):
                mkdir, chdir = link.mkd, link.cwd
        try:
            if remote_directory in ('', "/"):
                return
            remote_dirname, basename = os.path.split(remote_directory)
            self.mkdir_recursive(link, os.path.dirname(remote_directory), mkdir=mkdir, chdir=chdir)
            try:
                chdir(basename)
            except IOError:
                self.logger.info("Sorry, just have to make some new directories, eh. ")
                mkdir(basename)
                chdir(basename)
        except Exception as e:
            self.logger.error("something went wrong making directories... {}".format(str(e)))
        chdir("/")


    def communicate_with_updater(self):
        """
        communication member. This is meant to send some metadata to the updater thread.
        :return:
        """
        if not self.communication_queue:
            return

        try:
            self.logger.debug("Collecting metadata")
            data = dict(
                identifier=self.identifier,
                uploaded=SysUtil.sizeof_fmt(self.total_data_uploaded_b),
                uploads=self.last_upload_list,
                last_upload=int(self.last_upload_time.strftime("%s"))
            )
            self.communication_queue.append(data)
        except Exception as e:
            self.logger.error("inter thread communication error: {}".format(str(e)))

    def run(self):
        """
        run method.
        main loop for Uploaders.
        :return:
        """
        while True and not self.stopper.is_set():
            try:
                upload_list = glob(os.path.join(self.source_dir, '**'), recursive=True)
                if len(upload_list) == 0:
                    self.logger.info("No files in upload directory")
                if (len(upload_list) > 0) and self.upload_enabled:
                    start_upload_time = time.time()
                    self.logger.info("Preparing to upload %d files" % len(upload_list))
                    try:
                        l_im = os.path.join(self.source_dir, "last_image.jpg")
                        if l_im in upload_list:
                            upload_list.insert(0, upload_list.pop(upload_list.index(l_im)))
                    except Exception as e:
                        self.logger.info(
                            "Something went wrong sorting the last image to the front of the list: {}".format(str(e)))
                    self.upload(upload_list)
                    self.communicate_with_updater()
                    self.logger.info(
                        "Average upload time: {0:.2f}s".format((time.time() - start_upload_time) / len(upload_list)))
                    self.logger.info("Total upload time: {0:.2f}s".format(time.time() - start_upload_time))
            except Exception as e:
                self.logger.error("Unhandled exception in uploader run method: {}".format(str(e)))
            time.sleep(Uploader.upload_interval)

    def stop(self):
        """
        stopper method
        :return:
        """
        self.stopper.set()


class GenericUploader(Uploader):
    """
    Generic uploader for uploading logs sensor data, etc.
    """
    remove_source_files = False

    def fill_me(self, dict_of_values: dict):
        for k, v in dict_of_values.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __init__(self,
                 identifier: str,
                 source_dir: str = None,
                 hostname: str = None,
                 config: dict = None,
                 queue: deque = None):
        # same thread name hackery that the Camera threads use
        Thread.__init__(self, name=identifier + "-Uploader")
        self.stopper = Event()

        queue = queue if queue is not None else deque(tuple(), 256)

        self.communication_queue = queue
        self.identifier = identifier
        self.camera_name = identifier
        self.source_dir = source_dir
        self.logger = logging.getLogger(self.getName())
        self.startup_time = datetime.datetime.now()
        self.ssh_manager = SSHManager()
        self.machine_id = SysUtil.get_machineid()
        self.last_upload_time = datetime.datetime.fromtimestamp(0)
        self.last_upload_list = []
        self.total_data_uploaded_tb = 0
        self.total_data_uploaded_b = 0
        self.hostname = hostname or "sftp.traitcapture.org"
        self.upload_enabled = True
        self.username = "picam"
        self.password = "INTENTIONALLY BLANK"
        self.server_dir = "/"

        if config and type(config) is dict:
            self.camera_name = config.get("name", self.camera_name)
            self.source_dir = config.get("output_dir", self.source_dir)
            if type(config.get("upload")) is dict:
                config = config.get("upload")
            self.fill_me(config)
            self.upload_enabled = config.get("enabled", True)

    def re_init(self):
        """
        Your config is in another castle.
        """
        self.last_upload_list = []

