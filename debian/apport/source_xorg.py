#!/usr/bin/python

'''Xorg Apport interface

Copyright (C) 2007, 2008 Canonical Ltd.
Author: Bryce Harrington <bryce.harrington@ubuntu.com>

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.  See http://www.gnu.org/copyleft/gpl.html for
the full text of the license.

Testing:  APPORT_STAGING="yes"
'''

import os.path
import glob
import subprocess
from apport.hookutils import *
from launchpadlib.launchpad import Launchpad

core_x_packages = [
    'xorg', 'xorg-server', 'xserver-xorg-core', 'mesa'
    ]
keyboard_packages = [
    'xorg', 'xkeyboard-config', 'xserver-xorg-input-keyboard', 'xserver-xorg-input-evdev'
    ]

######
#
# Apport helper routines
#
######
def retrieve_ubuntu_release_statuses():
    '''
    Attempts to access launchpad to get a mapping of Ubuntu releases to status.

    Returns a dictionary of ubuntu release keywords to their current status,
    or None in cause of a failure reading launchpad.
    '''
    releases = { }
    try:
        lp = Launchpad.login_anonymously('apport', 'production')
        d = lp.distributions['ubuntu']
        for series in d.series:
            releases[series.name] = series.status
    except:
        releases = None
    return releases

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
    '''
    On errors, quell error message and just return empty string
    '''
    log = command_output(command_list)
    if log[:5] == "Error":
        return None
    return log

def root_collect_file_contents(path):
    '''
    Returns the contents of given file collected as root user
    '''
    log = root_command_output(['cat', path])
    if log[:5] == "Error":
        return "Not present"
    return log

def retval(command_list):
    '''
    Return the command exit code
    '''
    return subprocess.call(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def ubuntu_variant_name():
    '''
    Return 'ubuntu' or 'kubuntu' as appropriate
    '''
    if (retval(['which', 'kdesudo']) == 0 and
        retval(['pgrep', '-x', '-u', str(os.getuid()), 'ksmserver']) == 0):
        return "kubuntu"
    else:
        return "ubuntu"

def ubuntu_code_name():
    '''
    Return the ubuntu release code name, 'dapper', 'natty', etc.
    '''
    return command_output_quiet(['lsb_release','-sc'])


######
#
# Supportability tests
#
######

def check_is_supported(report, ui=None):
    '''
    Bug reports against the development release are higher priority than
    ones filed against already released versions.  We steer reporters of
    the latter towards technical support resources, which are better geared
    for helping end users solve problems with their installations.
    '''
    distro_codename = ubuntu_code_name()
    report['DistroCodename'] = distro_codename
    report['DistroVariant'] = ubuntu_variant_name()
    report['Tags'] += ' ' + report['DistroCodename']
    report['Tags'] += ' ' + report['DistroVariant']

    if not ui:
        return

    # Look up status of this and other releases
    release_status = retrieve_ubuntu_release_statuses()
    if not release_status or not report['DistroCodename']:
        # Problem accessing launchpad, can't tell anything about status
        # so assume by default that it's supportable.
        return True
    status = release_status.get(distro_codename, "Unknown")

    if status == "Obsolete":
        ui.information("Sorry, the '%s' version of Ubuntu is obsolete, which means the developers no longer accept bug reports about it." %(distro_codename))
        report['UnreportableReason'] = 'Unsupported Ubuntu Release'
        return False

    elif status == "Supported" or status == "Current Stable Release":
        response = ui.choice(
            "Development is completed for the '%s' version of Ubuntu, so\n"
            "you should use technical support channels unless you know for\n"
            "certain it should be reported here?" %(distro_codename),
            [
                "I don't know",
                "Yes, I already know the fix for this problem.",
                "Yes, The problem began right after doing a system software update.",
                "Yes, I have gone through technical support, and they have referred me here.",
                "No, please point me to a good place to get support.",
                ]
        )    

        # Fix is known
        if 1 in response:
            report['Tags'] += ' ' + 'patch'
            ui.information("Thanks for helping improve Ubuntu!  Tip:  If you attach the fix to the bug report as a patch, it will be flagged to the developers and should get a swifter response.")
            return True

        # Regression after a system update
        elif 2 in response:
            report['Tags'] += ' regression-update'
            response = ui.yesno("Thanks for reporting this regression in Ubuntu %s.  Do you know exactly which package and version caused the regression?" %(distro_codename))
            if response:
                ui.information("Excellent.  Please make sure to list the package name and version in the bug report's description.  That is vital information for pinpointing the cause of the regression, which will make solving this bug go much faster.")
                report['Tags'] += ' needs-reassignment'
                return True
            else:
                ui.information("Okay, your /var/log/dpkg.log will be attached.  Please indicate roughly when you first started noticing the problem.  This information will help in narrowing down the suspect package updates.")
                attach_file(report, "/var/log/dpkg.log", "DpkgLog")
                return True

        # Referred by technical support
        elif 3 in response:
            ui.information("Thanks for using technical support channels before filing this report.  In your bug report, please restate the issue and include a link or transcript of your discussion with them.")
            return True

        # Anything else should be redirected to technical support channels
        else:
            ui.information("http://askubuntu.com is the best place to get free help with technical issues.\n\n"
                           "See http://www.ubuntu.com/support for paid support and other free options.")
            report['UnreportableReason'] = 'Please work this issue through technical support channels first.'
            return False
 
    elif status == "Active Development":
        return True
    return True

#  You should try community support channels such as ubuntuforums.com or askubuntu.com.
def check_is_reportable(report, ui=None):
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

    return True

######
#
# Attach relevant data files
#
######

def attach_dkms_info(report, ui=None):
    '''
    DKMS is the dynamic kernel module service, for rebuilding modules
    against a new kernel on the fly, during boot.  Occasionally this fails
    such as when installing/upgrading with proprietary video drivers.
    '''
    if os.path.lexists('/var/lib/dkms'):
        # Gather any dkms make.log files for proprietary drivers
        for logfile in glob.glob("/var/lib/dkms/*/*/build/make.log"):
            attach_file(report, logfile, "make.log")
        report['DkmsStatus'] = command_output_quiet(['dkms', 'status'])

def attach_dist_upgrade_status(report, ui=None):
    '''
    This routine indicates whether a system was upgraded from a prior
    release of ubuntu, or was a fresh install of this release.
    '''
    if os.path.lexists('/var/log/dist-upgrade/apt.log'):
        # TODO: Not sure if this is quite exactly what I want, but close...
        upgraded = command_output_quiet(
            ['head', '-n', '1', '/var/log/dist-upgrade/apt.log'])
        if len(upgraded) > 0:
            report['DistUpgraded'] = "Yes, recently upgraded %s" %(upgraded)
        else:
            report['DistUpgraded'] = "Unknown"
        return True
    else:
        report['DistUpgraded'] = 'Fresh install'
        return False

def attach_graphic_card_pci_info(report, ui=None):
    '''
    Extracts the device system and subsystem IDs for the video card.
    Note that the user could have multiple video cards installed, so
    this may return a multi-line string.
    '''
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

def attach_xorg_package_versions(report, ui=None):
    for package in [
        "xserver-xorg",
        "libgl1-mesa-glx",
        "libdrm2",
        "xserver-xorg-video-intel",
        "xserver-xorg-video-ati",
        "xserver-xorg-video-nouveau"]:
        report['version.%s' %(package)] = package_versions(package)

def attach_2d_info(report, ui=None):
    attach_file_if_exists(report, '/var/log/plymouth-debug.log', 'PlymouthDebug')
    attach_file_if_exists(report, '/etc/X11/xorg.conf', 'XorgConf')
    attach_file_if_exists(report, '/var/log/Xorg.0.log', 'XorgLog')
    attach_file_if_exists(report, '/var/log/Xorg.0.log.old', 'XorgLogOld')

    if os.environ.get('DISPLAY'):
        # For resolution/multi-head bugs
        report['Xrandr'] = command_output_quiet(['xrandr', '--verbose'])
        attach_file_if_exists(report,
                              os.path.expanduser('~/.config/monitors.xml'),
                              'monitors.xml')

        # For font dpi bugs
        report['xdpyinfo'] = command_output_quiet(['xdpyinfo'])

    if ui and ui.yesno("Your gdm log files may help developers diagnose the bug, but may contain sensitive information.  Do you want to include these logs in your bug report?") == True:
        report['GdmLog']  = root_collect_file_contents('/var/log/gdm/:0.log')
        report['GdmLog1'] = root_collect_file_contents('/var/log/gdm/:0.log.1')
        report['GdmLog2'] = root_collect_file_contents('/var/log/gdm/:0.log.2')

def attach_3d_info(report, ui=None):
    if os.environ.get('DISPLAY'):
        if os.path.lexists('/usr/lib/nux/unity_support_test'):
            report['UnitySupportTest'] = command_output_quiet([
                '/usr/lib/nux/unity_support_test'])
        report['glxinfo'] = command_output_quiet(['glxinfo'])
        attach_file_if_exists(report,
                              os.path.expanduser('~/.drirc'),
                              'drirc')

        if command_output_quiet(['pidof', 'compiz']):
            report['CompositorRunning'] = 'compiz'
        elif command_output_quiet(['pidof', 'kwin']):
            report['CompisitorRunning'] = 'kwin'
        else:
            report['CompisitorRunning'] = 'None'

    # Detect software rasterizer
    glxinfo = report.get('glxinfo', '')
    xorglog = report.get('XorgLog', '')
    if len(glxinfo)>0:
        if 'renderer string: Software Rasterizer' in glxinfo:
            report['Renderer'] = 'Software'
        else:
            report['Renderer'] = 'Hardware acceleration'
    elif len(xorglog)>0:
        if 'reverting to software rendering' in xorglog:
            report['Renderer'] = 'Software'
        elif 'Direct rendering disabled' in xorglog:
            report['Renderer'] = 'Software'
        else:
            report['Renderer'] = 'Unknown'

    if ui and report['Renderer'] == 'Software':
        ui.information("Your system is providing 3D via software rendering rather than hardware rendering.  This is a compatibility mode which should display 3D graphics properly but the performance may be very poor.  If the problem you're reporting is related to graphics performance, your real question may be why X didn't use hardware acceleration for your system.")

    # Plugins
    report['CompizPlugins'] = command_output_quiet([
        'gconftool-2',
        '--get', '/apps/compiz-1/general/allscreens/options/active_plugins'])

    # User configuration
    report['GconfCompiz'] = command_output_quiet([
        'gconftool-2', '-R', '/apps/compiz-1'])

def attach_input_device_info(report, ui=None):
    # Only collect the following data if X11 is available
    if os.environ.get('DISPLAY'):
        # For keyboard bugs
        if report.get('SourcePackage','Unknown') in keyboard_packages:
            report['setxkbmap'] = command_output_quiet(['setxkbmap', '-print'])
            report['xkbcomp'] = command_output_quiet(['xkbcomp', ':0', '-w0', '-'])

        # For input device bugs
        report['peripherals'] = command_output_quiet(['gconftool-2', '-R', '/desktop/gnome/peripherals'])

def attach_nvidia_info(report, ui=None):
    # Attach information for upstreaming nvidia binary bugs
    if nonfree_graphics_module() == 'nvidia':        
        report['version.nvidia-graphics-drivers'] = package_versions("nvidia-graphics-drivers")

        for logfile in glob.glob('/proc/driver/nvidia/*'):
            if os.path.isfile(logfile):
                attach_file(report, logfile)

        for logfile in glob.glob('/proc/driver/nvidia/*/*'):
            if os.path.basename(logfile) != 'README':
                attach_file(report, logfile)

        if os.environ.get('DISPLAY'):
            # Attach output of nvidia-settings --query if we've got a display
            # to connect to.
            report['nvidia-settings'] = command_output_quiet(
                ['nvidia-settings', '-q', 'all'])

        # File any X crash with -nvidia involved with the -nvidia bugs
        if (report.get('ProblemType', '') == 'Crash' and 'Traceback' not in report):
            if report.get('SourcePackage','Unknown') in core_x_packages:
                report['SourcePackage'] = "nvidia-graphics-drivers"

def attach_fglrx_info(report, ui=None):
    if nonfree_graphics_module() == 'fglrx':

        report['version.fglrx-installer'] = package_versions("fglrx-installer")

        # File any X crash with -fglrx involved with the -fglrx bugs
        if report.get('SourcePackage','Unknown') in core_x_packages:
            if (report.get('ProblemType', '') == 'Crash' and 'Traceback' not in report):
                report['SourcePackage'] = "fglrx-installer"

def add_info(report, ui):
    report.setdefault('Tags', '')

    # Verify the bug is valid to be filed
    if check_is_reportable(report, ui) == False:
        return
    if check_is_supported(report, ui) == False:
        return

    attach_xorg_package_versions(report, ui)
    attach_dist_upgrade_status(report, ui)
    attach_graphic_card_pci_info(report, ui)
    attach_hardware(report)
    attach_drm_info(report)
    attach_dkms_info(report, ui)
    attach_nvidia_info(report, ui)
    attach_fglrx_info(report, ui)
    attach_2d_info(report, ui)
    attach_3d_info(report, ui)
    attach_input_device_info(report, ui)

    if ui:
        ui.information("Please also provide a step-by-step description of how the problem is produced in the bug description.  The logs being collected don't give this info, but it's really important.")

## DEBUGING ##
if __name__ == '__main__':
    report = {}
    add_info(report, None)
    for key in report:
        print '[%s]\n%s' % (key, report[key])
