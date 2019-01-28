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
parser.add_argument('--log-level',action='store', default = "WARNING", help = "sets logging level")
args = parser.parse_args()

main_config_file_path = os.path.join(args.sysconfig_dir,"btrfs-sbm.toml")

default_config_file_path = os.path.join(args.sysconfig_dir, "btrfs-sbm-default.toml")

log_Path = os.path.join("/","var","log","btrfs-sbm.log")

numeric_log_level = getattr(logging, args.log_level.upper(), None)
if not isinstance(numeric_log_level, int):
    raise ValueError('Invalid log level: %s' % args.log_level)
    sys.exit(1)

logging.basicConfig(filename = log_Path,level = numeric_log_level )
logging.info("logging started")

main_config = {}


# try to read config file
if os.path.exists(main_config_file_path) and os.path.exists(default_config_file_path):# both files exist
    try:
        f = open(main_config_file_path)
    except IOError:
        logging.error("main config file did not exist at: " + main_config_file_path)
        sys.exit(1)
    main_config = toml.load(f)
elif os.path.exists(main_config_file_path) and not os.path.exists(default_config_file_path):
    logging.info("default config file does not exist: creating now")
    shutil.copy2(main_config_file_path, default_config_file_path) # preserve default config file with comments
    try:
        f = open(main_config_file_path)
    except IOError:
        logging.error("main config file did not exist at: " + main_config_file_path)
        sys.exit(1)
    main_config = toml.load(f)
else:
    logging.critical("config file did not exist! Aborting")
    sys.exit(1)



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
