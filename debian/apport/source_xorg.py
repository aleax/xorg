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

def nonfree_graphics_module(module_list = '/proc/modules'):
    '''
    Check loaded modules to see if a proprietary graphics driver is loaded.
    Return the first such driver found.
    '''
    try:
        mods = [l.split()[0] for l in open(module_list)]
    except IOError:
        return None

    for m in mods:
        if m == "nvidia" or m == "fglrx":
            return m

def add_info(report, ui):
    tags = []

    # Build System Environment
    codename = command_output(['lsb_release','-sc'])
    tags.append(codename)

    report['system']  = "distro:             Ubuntu\n"
    report['system'] += "codename:           " + codename + "\n"
    report['system'] += "architecture:       " + command_output(['uname','-m']) + "\n"
    report['system'] += "kernel:             " + command_output(['uname','-r']) + "\n"

    attach_related_packages(report, [
            "xserver-xorg",
            "libgl1-mesa-glx",
            "libdrm2",
            "xserver-xorg-video-intel",
            "xserver-xorg-video-ati",
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

    if os.path.exists('/var/log/nvidia-installer.log'):
        # User has installed nVidia drivers manually at some point.
        # This is likely to have caused problems.
        if not ui.yesno("""It appears you may have installed the nVidia drivers manually from nvidia.com.  This can cause problems with the Ubuntu-supplied drivers.

If you have not already uninstalled the drivers downloaded from nvidia.com, please uninstall them and reinstall the Ubuntu packages before filing a bug with Ubuntu.

Have you uninstalled the drivers from nvidia.com?"""):
            report['UnreportableReason'] = 'The drivers from nvidia.com are not supported by Ubuntu.  Please uninstall them and test whether your problem still occurs.'
            return
        attach_file(report, '/var/log/nvidia-installer.log', 'nvidia-installer.log')
        tags.append('possible-manual-nvidia-install')

    if nonfree_graphics_module() == 'nvidia':        
        # Attach information for upstreaming nvidia binary bugs
        for logfile in glob.glob('/proc/driver/nvidia/*'):
            if os.path.isfile(logfile):
                attach_file(report, logfile)
        for logfile in glob.glob('/proc/driver/nvidia/*/*'):
            if os.path.basename(logfile) != 'README':
                attach_file(report, logfile)
        if os.environ.get('DISPLAY'):
            # Attach output of nvidia-settings --query if we've got a display
            # to connect to.
            report['nvidia-settings'] = command_output(['nvidia-settings', 
                                                        '-q'])
                                                       

    if report['ProblemType'] == 'Crash' and 'Traceback' not in report:
        nonfree_driver = nonfree_graphics_module()
        if (nonfree_driver == "fglrx"):
            report['SourcePackage'] = "fglrx-installer"

        elif (nonfree_driver == "nvidia"):
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
        report['GdmLog'] = root_command_output(['cat', '/var/log/gdm/:0.log'])
        report['GdmLog1'] = root_command_output(['cat', '/var/log/gdm/:0.log.1'])
        report['GdmLog2'] = root_command_output(['cat', '/var/log/gdm/:0.log.2'])

    report.setdefault('Tags', '')
    report['Tags'] += ' ' + ' '.join(tags)

## DEBUGING ##
if __name__ == '__main__':
    report = {}
    add_info(report)
    for key in report:
        print '[%s]\n%s' % (key, report[key])
