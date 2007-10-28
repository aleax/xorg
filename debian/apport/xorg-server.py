#!/usr/bin/python

'''Xorg Apport interface

Copyright (C) 2007 Canonical Ltd.
Author: Bryce Harrington <bryce.harrington@ubuntu.com>

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
the full text of the license.
'''

import os.path
import subprocess

XORG_CONF = '/etc/X11/xorg.conf'
XORG_LOG  = '/var/log/Xorg.0.log'

def add_info(report):
    # xorg.conf
    try:
        report['XorgConf'] = open(XORG_CONF).read()
    except IOError:
        pass

    # Xorg.0.log
    try:
        report['XorgLog']  = open(XORG_LOG).read()
    except IOError:
        pass

    try:
        report['ProcVersion']  = open('/proc/version').read()
    except IOError:
        pass

    try:
        script = subprocess.Popen(['lspci'], stdout=subprocess.PIPE)
        report['LsPci'] = script.communicate()[0]
    except OSError:
        pass

    try:
        script = subprocess.Popen(['lspci', '-vmm'], stdout=subprocess.PIPE)
        report['LsPciVVM'] = script.communicate()[0]
    except OSError:
        pass

    try:
        script = subprocess.Popen(['lsmod'], stdout=subprocess.PIPE)
        report['LsMod'] = script.communicate()[0]
    except OSError:
        pass

# TODO:
#
# xrandr --verbose


