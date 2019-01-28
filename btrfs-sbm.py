#!/usr/bin/env python3
"""
Script for managing btrfs snapshots and backups with backblaze b2
"""

import toml
import argparse
import subprocess
import os.path
import sys
import datetime
import logging
import shutil

# external files
# - log = /var/log/btrfs-sbm.log
# - main settings = /etc/conf.d/btrfs-sbm.toml

__version__ = "0.0.1"

assert sys.version_info >= (3, 6) # make sure we are running with at least python 3.6

def take_snapshot(src, dest, ro):
    """take btrfs snapshot"""
    if ro :
        subprocess.run(["btrfs", "subvolume", "snapshot", "-r", src, dest])
    else:
        subprocess.run(["btrfs", "subvolume", "snapshot", src, dest])


# first thing, read command line options

parser = argparse.ArgumentParser()
snapshot_type = parser.add_mutually_exclusive_group()
snapshot_type.add_argument('--hourly', action = 'store_true', default=False, help="takes hourly snapshot")
snapshot_type.add_argument('--daily', action = 'store_true', default=False, help="takes daily snapshot")
action_group = parser.add_mutually_exclusive_group()
action_group.add_argument('--list-configs', action = 'store_true',default=False, help="Prints list of configs")
action_group.add_argument('--create-config', action = 'store', help="Initializes subvolume snapshots and creates config file")
action_group.add_argument('--delete-config', action = 'store', help="removes config from table in main config file, does not delete snapshot")
parser.add_argument('--delete-snapshots', action = 'store_true', default=False, help="combine with --delete-config to delete snapshot directory, does nothing by itself")
action_group.add_argument('--show-config', action = 'store', help="prints configuration for specific subvolume")
action_group.add_argument('--edit-config', action = 'store', help="prompts to change values configuration for specific subvolume")
parser.add_argument('--status', action = 'store_true', default=False, help="prints status")
parser.add_argument('--sysconfig-dir', action='store', help= "changes sysconfig directory",default=os.path.join("/","etc", "conf.d"))
parser.add_argument('--version',action='version',version=__version__ )
args = parser.parse_args()

main_config_file_path = os.path.join(args.sysconfig_dir,"btrfs-sbm.toml"

# read config file
# TODO: need to make sure file and path exist first
main_config = toml.load(main_config_file_path)

log_Path = main_config['log-path']

# main command select
if args.list_configs:
    fmt_string = "{name:<10}|{path:<20}"
    print(fmt_string).format(name="Config",path="Subvolume Path")
    print(fmt_string).format(name="----------",path="--------------------")
    for subvol in main_config['configs']: # subvol is dict representing individual config
        print(fmt_string).format(name=subvol[name],path=subvol[path])
elif args.create_config != "":
    """Initializes subvolume backups"""
    now = datetime.datetime.now()
    subvolume_name = os.path.basename(os.path.normpath(subvolume_path))
    main_config['configs']

    # add subvolume to config table
    # create .shapshots directory
    # create first snapshot
    # btrfs snapshot [-r] <source> <dest>|[<dest>/]<name>
    # btrfs snapshot -r /path/to/subvolume/ /path/to/subvolume/.shapshots
    take_snapshot(subvolume_path, os.path.join(subvolume, ".shapshots", subvolume_name + now.isoformat()), true)


# dump config file
toml.dump(main_config, main_config_file_path)
