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

keyboard_packages = [
    'xorg', 'xkeyboard-config', 'xserver-xorg-input-keyboard', 'xserver-xorg-input-evdev'
    ]

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

def command_output_quiet(command_list):
    log = command_output(command_list)
    if log[:5] == "Error":
        return None
    return log

def root_collect_file_contents(path):
    '''Returns the contents of given file collected as root user'''
    log = root_command_output(['cat', path])
    if log[:5] == "Error":
        return "Not present"
    return log

def retval(command_list):
    return subprocess.call(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def ubuntu_variant_name():
    if (retval(['which', 'kdesudo']) == 0 and
        retval(['pgrep', '-x', '-u', str(os.getuid()), 'ksmserver']) == 0):
        return "kubuntu"
    else:
        return "ubuntu"

def ubuntu_code_name():
    return command_output(['lsb_release','-sc'])

def attach_dkms_info(report):
    if os.path.lexists('/var/lib/dkms'):
        # Gather any dkms make.log files for proprietary drivers
        for logfile in glob.glob("/var/lib/dkms/*/*/build/make.log"):
            attach_file(report, logfile, "make.log")
        report['DkmsStatus'] = command_output_quiet(['dkms', 'status'])

def attach_dist_upgrade_status(report):
    if os.path.lexists('/var/log/dist-upgrade/apt.log'):
        report['DistUpgraded'] = command_output_quiet(
            ['head', '-n', '1', '/var/log/dist-upgrade/apt.log'])
        return True
    else:
        report['DistUpgraded'] = 'Fresh install'
        return False

def attach_pci_info(report):
    info = ''
    display_pci = pci_devices(PCI_DISPLAY)
    for paragraph in display_pci.split('\n\n'):
        for line in paragraph.split('\n'):
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            value = value.strip()
            key = key.strip()
            if "VGA compatible controller" in key:
                info += "%s\n" % (value)
            elif key == "Subsystem":
                info += "  %s: %s\n" %(key, value)
    report['GraphicsCard'] = info

def check_is_reportable(report):
    '''Checks system to see if there is any reason the configuration is not
    valid for filing bug reports'''

    version_signature = report.get('ProcVersionSignature', '')
    if version_signature and not version_signature.startswith('Ubuntu '):
        report['UnreportableReason'] = 'The running kernel is not an Ubuntu kernel: %s' %version_signature
        return False

    bios = report.get('dmi.bios.version', '')
    if bios.startswith('VirtualBox '):
        report['SourcePackage'] = "virtualbox-ose"
        return False

    product_name = report.get('dmi.product.name', '')
    if product_name.startswith('VMware '):
        report['UnreportableReason'] = 'VMware is installed.  If you upgraded recently be sure to upgrade vmware to a compatible version.'
        return False

    return True

def attach_xorg_package_versions(report):
    for package in [
        "xserver-xorg",
        "libgl1-mesa-glx",
        "libdrm2",
        "xserver-xorg-video-intel",
        "xserver-xorg-video-ati",
        "xserver-xorg-video-nouveau"]:
        report['version.%s' %(package)] = package_versions(package)

def add_info(report, ui):
    tags = []

    report['DistroVariant']  = ubuntu_variant_name()
    report['DistroCodename'] = ubuntu_code_name()
    tags.append(report['DistroCodename'])
    tags.append(report['DistroVariant'])

    # Verify the bug is valid to be filed
    if check_is_reportable(report) == False:
        return

    if os.path.exists('/var/log/nvidia-installer.log'):
        # User has installed nVidia drivers manually at some point.
        # This is likely to have caused problems.
        if ui and not ui.yesno("""It appears you may have installed the nVidia drivers manually from nvidia.com.  This can cause problems with the Ubuntu-supplied drivers.

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
            report['nvidia-settings'] = command_output(
                ['nvidia-settings', '-q', 'all'])
                                                       
    if (report.get('ProblemType', '') == 'Crash' and 'Traceback' not in report):
        nonfree_driver = nonfree_graphics_module()
        if (nonfree_driver == "fglrx"):
            report['SourcePackage'] = "fglrx-installer"

        elif (nonfree_driver == "nvidia"):
            report['SourcePackage'] = "nvidia-graphics-drivers"

    attach_file_if_exists(report, '/var/log/plymouth-debug.log', 'PlymouthDebug')
    attach_file_if_exists(report, '/etc/X11/xorg.conf', 'XorgConf')
    attach_file_if_exists(report, '/var/log/Xorg.0.log', 'XorgLog')
    attach_file_if_exists(report, '/var/log/Xorg.0.log.old', 'XorgLogOld')

    attach_xorg_package_versions(report)
    attach_hardware(report)
    attach_drm_info(report)
    attach_dkms_info(report)
    attach_dist_upgrade_status(report)
    attach_pci_info(report)

    # Only collect the following data if X11 is available
    if os.environ.get('DISPLAY'):
        # For resolution/multi-head bugs
        report['Xrandr'] = command_output_quiet(['xrandr', '--verbose'])
        attach_file_if_exists(report,
                              os.path.expanduser('~/.config/monitors.xml'),
                              'monitors.xml')

        # For font dpi bugs
        report['xdpyinfo'] = command_output_quiet(['xdpyinfo'])

        # For 3D/Compiz/Mesa bugs
        report['glxinfo'] = command_output_quiet(['glxinfo'])
        attach_file_if_exists(report,
                              os.path.expanduser('~/.drirc'),
                              'drirc')

        # For keyboard bugs
        if report.get('SourcePackage','Unknown') in keyboard_packages:
            report['setxkbmap'] = command_output_quiet(['setxkbmap', '-print'])
            report['xkbcomp'] = command_output_quiet(['xkbcomp', ':0', '-w0', '-'])

        # For input device bugs
        report['peripherals'] = command_output_quiet(['gconftool-2', '-R', '/desktop/gnome/peripherals'])

    if ui:
        response = ui.yesno("Your gdm log files may help developers diagnose the bug, but may contain sensitive information.  Do you want to include these logs in your bug report?")
        if response == True:
            report['GdmLog']  = root_collect_file_contents('/var/log/gdm/:0.log')
            report['GdmLog1'] = root_collect_file_contents('/var/log/gdm/:0.log.1')
            report['GdmLog2'] = root_collect_file_contents('/var/log/gdm/:0.log.2')

    report.setdefault('Tags', '')
    report['Tags'] += ' ' + ' '.join(tags)


## DEBUGING ##
if __name__ == '__main__':
    report = {}
    add_info(report, None)
    for key in report:
        print '[%s]\n%s' % (key, report[key])
