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

# TODO: remove in production version
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

def btrfs_send_snapshot_diff(old, new=None):
    """Outputs diff between two subvolumes (snapshots) to a file

    Keyword arguments:
    old -- path to older subvolume (snapshots) as string
    new -- path to newer subvolume (snapshots) as string. (optional)
    """
    if new:
        filename = os.path.basename(old) + "::" + os.path.basename(new)
        if testing:
            print("btrfs send -p {old} -f {filename} {new}")
        else:
            subprocess.run(["btrfs", "send", "-p", old, "-f", filename, new], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(return_val.stdout)
            logging.error(return_val.stderr)
        logging.info("Sending difference between {old} and {new} to {filename}")
    else:
        filename = "init" + "::" + os.path.basename(old)
        if testing:
            print("btrfs send -f {filename} {old}")
        else:
            subprocess.run(["btrfs", "send", "-f", filename, old], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(return_val.stdout)
            logging.error(return_val.stderr)
        logging.info("Sending {old} to {filename}")

# TODO: implement function to check if there is a difference between btrfs snapshots

def read_config_file(path, type):
    """Reads TOML formatted config file safely

    Checks to make sure file exists before reading. Handles errors if it does not.
    Keyword arguments:
    path -- path of config file as string
    type -- type of config file as string. Default handled differently.

    Returns dict
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

if testing:
    main_config_file_path = "./btrfs-sbm.toml"
    default_config_file_path = "./btrfs-sbm-default.toml"
else:
    main_config_file_path = os.path.join(args.sysconfig_dir,"btrfs-sbm.toml")
    default_config_file_path = os.path.join(args.sysconfig_dir, "btrfs-sbm-default.toml")

if testing:
    log_Path = "./testlog.log"
else:
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

    elif args.list_snapshots is not None:
        config_name = args.list_snapshots
        pass
        # TODO: implement list_snapshots
        # create custom pretty print function so it can be reused
        # have option to print snapshot numbers or not

    elif args.list_all_snapshots:
        pass
        # TODO: loop through all subvolumes and call list_snapshots

    elif args.delete_snapshot is not None:
        config_name = args.delete_snapshot
        # TODO:
        # - print list of snapshots in config.
        # use same mechanism as list_snapshots
        # but print and keep track of snapshot numbers
        # - prompt for snapshot number to delete
        # - delete snapshot after confirmation printout and prompt

    else: # automatic functionality
        time_now = datetime.now()


        # loop through all subvolume configs except default
        for key, subvolume in main_config['configs'].items():

            subvolume_name = subvolume['name']
            subvolume_path = subvolume['path']

            snapshot_name = subvolume_name + "-"+ time_now.isoformat()
            snapshot_subvol_path = os.path.join(subvolume_path, snapshot_subvol_name)

            newest_snapshot = max(subvolume['snapshots'].items(), key=lambda x: x[1]['creation-date-time'])[0]
            newest_snapshot_time = datetime.fromisoformat(subvolume['snapshots'][newest_snapshot]['creation-date-time'])
            # delta between last snapshot and now is at least 1 hour
            if time_now >= newest_snapshot_time + timedelta(hours=1):
                subvolume['snapshots'][snapshot_name] = {}
                # assuming subvol and .snapshot directory already exist
                btrfs_take_snapshot(subvolume['path'], os.path.join(snapshot_subvol_path, snapshot_name), True)
                subvolume['snapshots'][snapshot_name]['name'] = snapshot_name
                subvolume['snapshots'][snapshot_name]['path'] = os.path.join(subvolume_path, snapshot_subvol_name, snapshot_name)
                subvolume['snapshots'][snapshot_name]['creation-date-time'] = str(time_now.isoformat())

                if time_now.hour == 0 and not newest_snapshot_time.hour == 0:
                    subvolume['snapshots'][snapshot_name]['type'] = "daily"
                elif time_now.isoweekday() == 1 and not newest_snapshot_time.isoweekday() == 1: # begining of week = monday
                    subvolume['snapshots'][snapshot_name]['type'] = "weekly"
                elif time_now.day == 1 and not newest_snapshot_time.day == 1: # first day of month
                    subvolume['snapshots'][snapshot_name]['type'] = "monthly"
                elif(time_now.month == 1 and time_now.day == 1) and not (newest_snapshot_time.month == 1 and newest_snapshot_time.day == 1): # first day of year
                    subvolume['snapshots'][snapshot_name]['type'] = "yearly"
                else:
                    subvolume['snapshots'][snapshot_name]['type'] = "hourly"
                # # TODO: btrfs send diff between snapshots
                # send each snapshot diff to tmp directory, encrypt, then upload to B2, then delete from tmp folder

            num_snapshots = {'hourly' : 0, 'daily' : 0, 'weekly' : 0, 'monthly' : 0, 'yearly' : 0}
            snapshots_by_type = {'hourly' : {}, 'daily' : {}, 'weekly' : {}, 'monthly' : {}, 'yearly' : {}}

            # count number of each type of snapshot
            for snapshots, snapshot in subvolume['snapshots'].items():
                snapshot_type = snapshot['type']
                if snapshot_type != 'init':
                    num_snapshots[snapshot_type] += 1
                    snapshots_by_type[snapshot_type][snapshot['name']]= snapshot
                else: pass

            print(num_snapshots)

            # check if number of snapshots of each type are over limit, and remove oldest

            for type, value in num_snapshots.items():
                if value > subvolume['options']["keep-"+type]:
                    # list of snapshots
                    # lambda k: k[1]['creation-date-time'] the [1] is essentially selecting the value in the key value pair that is x
                    # where key = snapshots dict, and value is individual snapshot dict beneath it.
                    newlist = sorted(snapshots_by_type[type].items(), key=lambda k: k[1]['creation-date-time'])
                    # delete oldest snapshots up to max
                    for sel in range(value - subvolume['options']["keep-"+type]):
                        # newlist is list of tuples (snapshot name, snapshot dict) due to .items()
                        # need to select tuple within that, then select snapshot dict inside tuple
                        # print(newlist[sel][1]['path'])
                        btrfs_delete_subvolume(newlist[sel][1]['path'])
                        del subvolume['snapshots'][newlist[sel][0]]
                else:
                    pass
                    # print("false")

    # TODO: implement snapshot backup functionality
    # send each snapshot diff to tmp directory, encrypt, then upload to B2, then delete from temp folder
    # remember: snapshots are full "copies" of subvolume, snapshot diffs are "diffs"
    # need all diffs in order to recreate final state.
    # diffs should only be slighly larger than actual data

    # TODO: check if snapshot diff is empty, if it is discard snapshot. This won't affect
    # backup stuff, since the btrfs incremental send will be between the previously saved snapshot,
    # which is the one before deleted snapshot

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
