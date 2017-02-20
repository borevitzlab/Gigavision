.. Gigavision root rst file.

.. toctree::
   :name: mastertoc
   :titlesonly:
   :hidden:

   ansible
   py-modindex


Gigavision
==========

Credits/License
---------------

The goal of this project is to create an open source, modular control interface for taking time lapse grid panoramas.

This project is open source but please `contact us <https://github.com/borevitzlab>`_ before using the code so we can know who is using it and please make sure to link back here in any code you use. This project is in active development but we are happy to work with other groups to develop new features so drop us a line if you are interested.


Features
--------

Currently supported and maintained:
 * Captures to JPEG & CR2 (RAW) images if using a DSLR, JPEG & TIF if using the Raspberry Pi camera module or an IP camera.
 * Has been tested with the AXIS Q6034-E, and a J-Systems Pan Tilt.
 * Tested with Canons (600D, 700D, 70D) but not extensively. Should work with Nikon cameras but not tested at all.
 * Resume function if panorama was interrupted and restarted within a time interval.
 * Captured photos are captured to ram, cached locally and then uploaded to a server of your choice via sftp or ftp.
 * Wifi and ethernet. Creates an ad-hoc wifi network no know network is found for easier config of new systems and in new wifi environments.
 * Ansible provisioning for Raspberry Pis control systems running Arch Linux.

Planned or in development:
 * DB-based camera management system
 * Cameras settings web interface
 * On device stitching and blending
 * Focal stacks
 * HDR

Automatically detects connected usb DSLRs and the Raspberry Pi camera (just duplicate *example.ini* to *picam.ini* and *eyepi.ini* and change the configuration values). DSLR's are given a unique ID based on hardware serial.

Camera name can be easily changed to a user friendly value.

Requirements
------------

*os:*
 * python3.5
 * python-cffi
 * gphoto2
 * libgphoto2
 * exiv2
 * opencv 3.1 `[Arch-Extra] <https://www.archlinux.org/packages/extra/x86_64/opencv/>`_
 * tor (optional)

*python/aur/git*
 * pyudev `[pip] <https://pypi.python.org/pypi/pyudev>`__
 * gphoto2-cffi `[git] <https://github.com/borevitzlab/gphoto2-cffi>`__
 * numpy
 * pillow `[pip] <https://pypi.python.org/pypi/Pillow/3.1.1>`__
 * picamera (optional) `[pip] <https://pypi.python.org/pypi/picamera/1.12>`__
 * py3exiv2 (optional) `[pip] <https://pypi.python.org/pypi/py3exiv2/0.2.1>`__
 * cryptography `[pip] <https://pypi.python.org/pypi/cryptography>`__
 * pysftp `[pip] <https://pypi.python.org/pypi/pysftp>`__
 * requests[socks] `[pip] <https://pypi.python.org/pypi/requests/2.11.1>`__
 * create_ap `[aur] <https://aur.archlinux.org/packages/create_ap>`__
 * schedule `[pip] <https://pypi.python.org/pypi/schedule>`__
 * pyyaml `[pip] <https://pypi.python.org/pypi/PyYAML/3.12>`__
 * `flask <http://flask.pocoo.org/>`__
 * flask-bcrypt `[pip] <https://pypi.python.org/pypi/Flask-Bcrypt>`__
 * flask-login `[pip] <https://pypi.python.org/pypi/Flask-Login>`__
 * WTForms `[pip] <https://pypi.python.org/pypi/WTForms>`__
 * browsepy `[pip] <https://pypi.python.org/pypi/browsepy/0.4.0>`__

Extra Details
-------------

If you are capturing using a Raspberry Pi camera or an IP camera you need to install **py3exiv2** if you want your images to have exif data, as the method of capture doesn't add exif data.

Documentation Links
-------------------

* :doc:`ansible`
* :ref:`genindex`
* :ref:`modindex`
