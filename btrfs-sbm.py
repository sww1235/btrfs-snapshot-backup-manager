#!/usr/bin/env python3
"""
Script for managing btrfs snapshots and backups with backblaze b2
"""

import toml
import argparse
import subprocess
import os.path
import sys
from datetime import datetime, timedelta
import logging
import shutil
import fcntl

# external files
# - log = /var/log/btrfs-sbm.log
# - main settings = /etc/conf.d/btrfs-sbm.toml
# - default settings = /etc/conf.d/btrfs-sbm-default.toml (read only)

__version__ = "0.0.1"

testing = True

# make sure we are running with at least python 3.6
assert sys.version_info >= (3, 6) "You are running an old version of python less than version 3.6. Please upgrade or fix the script yourself."

# only let one instance of script run at a time
lockfile_path = os.path.join("/", "tmp", "btrfs-sbm.lock")
lockfile = open(lockfile_path, "a+")
try:
    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    sys.exit("Multiple instances of script cannot be running at the same time. Try running it again in a few minutes")

snapshot_subvol_name = ".snapshots"

def btrfs_take_snapshot(src, dest, ro):
    """take btrfs snapshot

    Uses btrfs-progs snapshot command to take a snapshot of the src subvolume
    Keyword arguments:
    src -- path to source subvolume as string
    dest -- path to destination snapshot as string. This includes the name of the snapshot itself.
    See the documentation of btrfs subvolume for further details.
    ro -- whether to take a read only snapshot
    """
    if ro :
        if testing:
            print("btrfs subvolume snapshot -r {src} {dest}")
        else:
            return_val = subprocess.run(["btrfs", "subvolume", "snapshot", "-r", src, dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.info("Taking new read only snapshot of {src} at {dest}")
    else:
        if testing:
            print("btrfs subvolume snapshot {src} {dest}")
        else:
            return_val = subprocess.run(["btrfs", "subvolume", "snapshot", src, dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("Taking new snapshot of {src} at {dest}")
    if not testing:
        # log stdout and stderr from btrfs commands
        logging.info(return_val.stdout)
        logging.error(return_val.stderr)

def btrfs_subvolume_exists(path):
    """Checks if path is a btrfs subvolume

    Uses btrfs subvolume show command to detect if a subvolume exists
    Keyword arguments:
    path -- path to subvolume as string
    """
    if testing:
        return True
    else:
        return_val =subprocess.run(["btrfs", "subvolume", "show",subvolume_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if return_val.returncode != 0:
            logging.error(return_val.stderr)
            return False
        else: return True

def btrfs_create_subvolume(path):
    """Creates a btrfs subvolume

    Uses btrfs-progs subvolume command to create a new subvolume
    Keyword arguments:
    path -- path to subvolume as string
    """
    if testing:
        print("btrfs subvolume create {path}")
    else:
        subprocess.run(["btrfs", "subvolume", "create", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(return_val.stdout)
        logging.error(return_val.stderr)
    logging.info("Creating new subvolume at {path}")

def btrfs_delete_subvolume(path):
    """Deletes a btrfs subvolume

    Uses btrfs-progs subvolume command to delete a subvolume. Cannot recursively delete subvolumes.
    Keyword arguments:
    path -- path to subvolume as string
    """
    if testing:
        print("btrfs subvolume delete {path}")
    else:
        subprocess.run(["btrfs", "subvolume", "delete", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(return_val.stdout)
        logging.error(return_val.stderr)
    logging.info("Deleting subvolume at {path}")
def read_config_file(path, type):
    """Reads TOML formatted config file safely

    Checks to make sure file exists before reading. Handles errors if it does not.
    """
    # try to read config file
    if os.path.exists(path):
        try:
            f = open(path, 'r') # force read only mode
        except IOError:
            logging.error("{type} config file was unable to be read: {path}!")
            return {}
        return toml.load(f)
    else:
        if type != "default":
            logging.critical("{type} config file did not exist at {path}!")
        else:
            logging.critical("{type} config file did not exist at {path}! Using backup values in script")
        return {}




# first thing, read command line options

parser = argparse.ArgumentParser()
action_group = parser.add_mutually_exclusive_group()
action_group.add_argument('--list-configs', action = 'store_true',default=False, help="Prints list of configs")
action_group.add_argument('--create-config', action = 'store', metavar= "/path/to/subvolume", help="Initializes subvolume snapshots and creates config file")
action_group.add_argument('--delete-config', action = 'store', metavar="config-name", help="removes config from table in main config file, does not delete snapshot")
parser.add_argument('--delete-snapshots', action = 'store_true', default=False, help="combine with --delete-config to delete snapshot directory, does nothing by itself")
action_group.add_argument('--show-config', action = 'store', metavar="config-name", help="prints configuration for specific subvolume")
action_group.add_argument('--edit-config', action = 'store', metavar="config-name", help="prompts to change values configuration for specific subvolume")
action_group.add_argument('--list-snapshots', action='store', metavar="config-name", help="prints all snapshots of config")
action_group.add_argument('--list-all-snapshots', action='store_true', default=False,help="print all snapshots in all subvolumes")
action_group.add_argument('--delete-snapshot', action='store', metavar="config-name", help="deletes snapshot from config-name. Snapshot is selected from list")
parser.add_argument('--sysconfig-dir', action='store', metavar="/path/to/configfile", help= "changes sysconfig directory",default=os.path.join("/","etc", "conf.d"))
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
default_config = {}

main_config = read_config_file(main_config_file_path, "main")

if not main_config: # empty dict evaluates as false
    logging.warning("main config file not found at {main_config_file_path}. No configs present. \
    Please run script with --create-config option to create a config. This will create a non empty config file.")

default_config = read_config_file(default_config_file_path, "default")



if not default_config: # empty dict evaluates as false
    logging.error("default config file not found at {default_config_file_path}. Using defaults in script")
    default_config = {'keep-hourly': 10, 'keep-daily': 10, 'keep-weekly': 0, 'keep-monthly': 10, 'keep-yearly': 10}


if main_config: # empty dict evaluates as false

    # main command select
    if args.list_configs:
        """Lists subvolume configurations"""
        fmt_string = "{name:<10}|{path:<20}"
        print(fmt_string.format(name="Config",path="Subvolume Path"))
        print(fmt_string.format(name="----------",path="--------------------"))
        for key, subvol in main_config['configs'].items(): # subvol is dict representing individual config
            print(fmt_string.format(name=subvol['name'],path=subvol['path']))
    elif args.create_config is not None:
        """Initializes subvolume backups"""
        subvolume_path = args.create_config
        if btrfs_subvolume_exists(subvolume_path):

            time_now = datetime.now()
            subvolume_name = os.path.basename(os.path.normpath(subvolume_path))

            snapshot_name = subvolume_name + "-"+ time_now.isoformat()

            snapshot_subvol_path = os.path.join(subvolume_path, snapshot_subvol_name)

            # add subvolume to config table
            if subvolume_name not in main_config['configs']:
                main_config['configs'][subvolume_name] = {} # init dicts
                main_config['configs'][subvolume_name]['options'] = {}
                main_config['configs'][subvolume_name]['snapshots'] = {}
                main_config['configs'][subvolume_name]['snapshots'][snapshot_name] = {}


                main_config['configs'][subvolume_name]['name'] = subvolume_name
                main_config['configs'][subvolume_name]['path'] = subvolume_path

                for config, value in default_config.items():
                    # print(config, value)
                    try:
                        tmp = input("How many {snapshot_type} snapshots to keep? (Default={default}): \
                                    ".format(snapshot_type=config.split('-')[1],default=value))
                    except SyntaxError:
                        tmp = ""
                    if tmp != "":
                        main_config['configs'][subvolume_name]['options'][config] = int(tmp)
                    else:
                        main_config['configs'][subvolume_name]['options'][config] = int(value)

                # create .snapshots subvolume
                if not btrfs_subvolume_exists(snapshot_subvol_path):
                    btrfs_create_subvolume(snapshot_subvol_path)

                # create first snapshot
                btrfs_take_snapshot(subvolume_path, os.path.join(snapshot_subvol_path, snapshot_name), True)

                main_config['configs'][subvolume_name]['snapshots'][snapshot_name]['name'] = snapshot_name
                main_config['configs'][subvolume_name]['snapshots'][snapshot_name]['path'] = os.path.join(subvolume_path, snapshot_subvol_name, snapshot_name)
                main_config['configs'][subvolume_name]['snapshots'][snapshot_name]['creation-date-time'] = str(time_now.isoformat())
                main_config['configs'][subvolume_name]['snapshots'][snapshot_name]['type'] = "init"
            else:
                print("subvolume config {config} already exists. Please use --show-config or --edit config instead".format(config=subvolume_name))
                sys.exit(1)

        else:
            print("{path} is not a btrfs subvolume. Make sure you typed it correctly")
            sys.exit(1)
    elif args.delete_config is not None:
        config_name = args.delete_config

        if config_name in main_config['configs']:
            if args.delete_snapshots: # also delete snapshots
                for snapshots, snapshot in main_config['configs'][config_name]['snapshots'].items():
                    if btrfs_subvolume_exists(snapshot['path']):
                        btrfs_delete_subvolume(snapshot['path'])
                    else:
                        logging.warning("Snapshot: {snapshot} did not exist at {path}. Ignoring".format(snapshot=snapshot['name'], path=snapshot['path']))
                # delete snapshot directory last
                snapshot_subvol_path = os.path.join(main_config['configs'][config]['path'], snapshot_subvol_name)
                if btrfs_subvolume_exists(snapshot_subvol_path):
                    btrfs_delete_subvolume(snapshot_subvol_path)
                else:
                    logging.warning("{snapshot_subvol_name} subvolume did not exist. This is odd")
            del main_config['configs'][config_name] # remove dictionary
        else:
            print("{config} did not exist in the list of configs. Make sure you typed it correctly or use --list-configs to view available configs".format(config=config_name))
            sys.exit(1)

    elif args.show_config is not None:
        config_name = args.show_config

        if config_name in main_config['configs']:
            print(toml.dumps(main_config['configs'][config_name]))
        else:
            print("{config} did not exist in the list of configs. Make sure you typed it correctly or use --list-configs to view available configs".format(config=config_name))
            sys.exit(1)

    elif args.edit_config is not None:
        config_name = args.edit_config

        if config_name in main_config['configs']:
            print(toml.dumps(main_config['configs'][config_name]))
            #TODO: look into python editor or implement subset myself
        else:
            print("{config} did not exist in the list of configs. Make sure you typed it correctly or use --list-configs to view available configs".format(config=config_name))
            sys.exit(1)

    else: # automatic functionality
        time_now = datetime.now()


else:
    pass # continue on and save main config file


if os.path.exists(main_config_file_path):
    try:
        shutil.copy2(main_config_file_path, main_config_file_path + ".bak")
    except IOError as e:
        logging.critical("failed to backup main config file. See exception {e}")
        sys.exit(1)
    try:
        f = open(main_config_file_path,'w') # overwrites file
    except IOError as e:
        logging.critical("main config file could not be opened. See exception {e}")
        sys.exit(1)
    toml.dump(main_config,f) # write config file
else:
    logging.warning("main config file did not exist. Creating now at {main_config_file_path}.")
    try:
        f = open(main_config_file_path,'w+') # create and update file (truncates)
    except IOError as e:
        logging.critical("Could not create new config file at {main_config_file_path}. See exception {e}")
        sys.exit(1)
