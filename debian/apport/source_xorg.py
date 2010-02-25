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
import glob
import subprocess
from apport.hookutils import *

def installed_version(pkg):
    script = subprocess.Popen(['apt-cache', 'policy', pkg], stdout=subprocess.PIPE)
    output = script.communicate()[0]
    return output.split('\n')[1].replace("Installed: ", "")

def add_info(report):
    tags = []

    # Build System Environment
    codename = command_output(['lsb_release','-c']).split(": ")[1]
    tags.append(codename)

    report['system']  = "distro:             Ubuntu\n"
    report['system'] += "codename:           " + codename
    report['system'] += "architecture:       " + command_output(['uname','-m'])
    report['system'] += "kernel:             " + command_output(['uname','-r'])

    attach_related_packages(report, [
            "xserver-xorg",
            "libgl1-mesa-glx",
            "libdrm2",
            "xserver-xorg-video-intel",
            "xserver-xorg-video-ati"
            "xserver-xorg-video-nouveau"
            ])

    # Verify the bug is valid to be filed
    version_signature = report.get('ProcVersionSignature', '')
    if not version_signature.startswith('Ubuntu '):
        report['UnreportableReason'] = _('The running kernel is not an Ubuntu kernel')
        return

    bios = report.get('dmi.bios.version', '')
    if bios.startswith('VirtualBox '):
        report['SourcePackage'] = "virtualbox-ose"
        return

    product_name = report.get('dmi.product.name', '')
    if product_name.startswith('VMware '):
        report['UnreportableReason'] = _('VMware is installed.  If you upgraded recently be sure to upgrade vmware to a compatible version.')
        return

    matches = command_output(['grep', 'fglrx', '/var/log/kern.log', '/proc/modules'])
    if (matches):
        report['SourcePackage'] = "fglrx-installer"

    matches = command_output(['grep', 'nvidia', '/var/log/kern.log', '/proc/modules'])
    if (matches):
        report['SourcePackage'] = "nvidia-graphics-drivers"

    attach_file_if_exists(report, '/etc/X11/xorg.conf', 'XorgConf')
    attach_file(report, '/var/log/Xorg.0.log', 'XorgLog')
    attach_file_if_exists(report, '/var/log/Xorg.0.log.old', 'XorgLogOld')

    # Capture hardware
    attach_hardware(report)
    report['PciDisplay'] = pci_devices(PCI_DISPLAY)
    
    if [ os.path.lexists('/var/lib/dkms') ]:
        # Gather any dkms make.log files for proprietary drivers
        for logfile in glob.glob("/var/lib/dkms/*/*/build/make.log"):
            attach_file(report, logfile, "make.log")

        # dkms status
        report['DkmsStatus'] = command_output(['dkms', 'status'])

    # Only collect the following data if X11 is available
    if os.environ.get('DISPLAY'):
        # For resolution/multi-head bugs
        report['Xrandr'] = command_output(['xrandr', '--verbose'])
        attach_file_if_exists(report,
                              os.path.expanduser('~/.config/monitors.xml'),
                              'monitors.xml')

        # For font dpi bugs
        report['xdpyinfo'] = command_output(['xdpyinfo'])

        # For 3D/Compiz/Mesa bugs
        report['glxinfo'] = command_output(['glxinfo'])

        # For keyboard bugs
        report['setxkbmap'] = command_output(['setxkbmap', '-print'])
        report['xkbcomp'] = command_output(['xkbcomp', ':0', '-w0', '-'])

    response = ui.yesno("Your gdm log files may help developers diagnose the bug, but may contain sensitive information.  Do you want to include these logs in your bug report?")
    if response == True:
        attach_file_if_exists(report, '/var/log/gdm/:0.log', 'GdmLog')
        attach_file_if_exists(report, '/var/log/gdm/:0.log.1', 'GdmLog1')
        attach_file_if_exists(report, '/var/log/gdm/:0.log.2', 'GdmLog2')

    report.setdefault('Tags', '')
    report['Tags'] += ' ' + ' '.join(tags)

## DEBUGING ##
if __name__ == '__main__':
    report = {}
    add_info(report)
    for key in report:
        print '[%s]\n%s' % (key, report[key])
