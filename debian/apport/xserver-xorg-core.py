#!/usr/bin/python

'''Xorg Apport interface

Copyright (C) 2007, 2008 Canonical Ltd.
Author: Bryce Harrington <bryce.harrington@ubuntu.com>

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
the full text of the license.
'''

import os.path
import subprocess

def add_info(report):
    try:
        report['XorgConf'] = open('/etc/X11/xorg.conf').read()
    except IOError:
        pass

    try:
        report['XorgLog']  = open('/var/log/Xorg.0.log').read()
    except IOError:
        pass

    try:
        report['ProcVersion']  = open('/proc/version').read()
    except IOError:
        pass

    try:
        script = subprocess.Popen(['lspci', '-vvnn'], stdout=subprocess.PIPE)
        report['LsPci'] = script.communicate()[0]
    except OSError:
        pass

    try:
        script = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
        report['LsMod'] = script.communicate()[0]
    except OSError:
        pass

    try:
        script = subprocess.Popen(['xrandr --verbose'], stdout=subprocess.PIPE)
        report['Xrandr'] = script.communicate()[0]
    except OSError:
        pass

    try:
        script = subprocess.Popen(['xdpyinfo'], stdout=subprocess.PIPE)
        report['xdpyinfo'] = script.communicate()[0]
    except OSError:
        pass


