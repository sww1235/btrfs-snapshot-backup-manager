#!/usr/bin/env python3
"""Script for managing btrfs snapshots and backups with backblaze b2."""

import argparse  # command line arguments
import fcntl  # lock files
import logging
import os.path
import shutil  # config file backups
import subprocess
import sys
from datetime import datetime, timedelta

import toml

import btrfs_control as btrfs

# TODO: refactor code with classes for snapshots and subvolumes.
# TODO: add b2 file as well.
# TODO: add init, requirements.txt and main stuff.
# TODO: add command to show shapshot diff changes.

# TODO: provide a mechanism to list all snapshot diffs on server, and list
# changes. maybe store complete file diff, metadata only diff and shasum of
# complete file diff on server.

# external files
# - log = /var/log/btrfs-sbm.log
# - main settings = /etc/conf.d/btrfs-sbm.toml
# - default settings = /etc/conf.d/btrfs-sbm-default.toml (read only)

__version__ = "0.1.1"

# TODO: remove in production version
TESTING = True


# make sure we are running with at least python 3.6
assert sys.version_info >= (
    3, 6
), "You are running an old version of python less than version 3.6. Please \
    upgrade or fix the script yourself."

# only let one instance of script run at a time
lockfile_path = os.path.join("/", "tmp", "btrfs-sbm.lock")
lockfile = open(lockfile_path, "a+")
try:
    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    sys.exit("Multiple instances of script cannot be running at the same "
             "time. Try running it again in a few minutes"
             )

snapshot_subvol_name = ".snapshots"


def b2_send_file(filepath, subvolume):
    """Use b2 python libraries to send snapshot diffs to b2 container.

    only send to one bucket since they are limited.
    Keyword arguments:
    filepath -- path to snapshot diff file as string
    subvolume -- which subvolume "folder" to prefix the file with
    """
    # TODO: implement snapshot backup functionality
    # send each snapshot diff to tmp directory, encrypt, then upload to B2,
    # then delete from temp folder
    # remember: snapshots are full "copies" of subvolume, snapshot diffs
    # are "diffs"
    # need all diffs in order to recreate final state.
    # diffs should only be slighly larger than actual data
    pass


def read_config_file(path, type_):
    """Read TOML formatted config file safely.

    Checks to make sure file exists before reading. Handles errors if it
    does not.
    Keyword arguments:
    path -- path of config file as string
    type -- type of config file as string. Default handled differently.

    Returns dict
    """
    # try to read config file
    if os.path.exists(path):
        try:
            f = open(path, 'r')  # force read only mode
        except IOError:
            logging.error(f"{type_} config file was unable to be "
                          f"read at {path}!"
                          )
            return {}
        return toml.load(f)
    else:
        if type_ != "default":
            logging.critical(f"{type_} config file did not exist at {path}!")
        else:
            logging.critical(f"{type_} config file did not exist at {path}! "
                             f"Using backup values in script"
                             )
        return {}


# first thing, read command line options

parser = argparse.ArgumentParser()
action_group = parser.add_mutually_exclusive_group()
action_group.add_argument(  # list subvolumes
    '--list-subvolumes',
    action='store_true',
    default=False,
    help="Prints list of snapshots"
)
action_group.add_argument(  # init subvolume
    '--init-subvolume',
    action='store',
    metavar="/path/to/subvolume",
    help="Initializes subvolume with initial snapshot and configuration"
)
action_group.add_argument(  # delete subvolumes
    '--delete-subvolume',
    action='store',
    metavar="config-name",
    help=("removes subvolume from list in main config file, does not"
          "delete associated snapshots"
          )
)
parser.add_argument(  # delete snapshot
    '--delete-snapshots',
    action='store_true',
    default=False,
    help=("combine with --delete-subvolume to delete snapshot directory, does"
          "nothing by itself"
          )
)
action_group.add_argument(  # show subvolume
    '--show-subvolume',
    action='store',
    metavar="config-name",
    help="prints configuration for specific subvolume"
)
action_group.add_argument(  # edit subvolume
    '--edit-subvolume',
    action='store',
    metavar="config-name",
    help="prompts to change values configuration for specific subvolume"
)
action_group.add_argument(  # list snapshot
    '--list-snapshots',
    action='store',
    metavar="config-name",
    help="prints all snapshots of subvolume"
)
action_group.add_argument(  # list all snapshots
    '--list-all-snapshots',
    action='store_true',
    default=False,
    help="print all snapshots in all subvolumes"
)
action_group.add_argument(  # delete snapshot
    '--delete-snapshot',
    action='store',
    metavar="config-name",
    help="deletes snapshot from subvolume. Snapshot is selected from list"
)
parser.add_argument(  # sysconfig dir
    '--sysconfig-dir',
    action='store',
    metavar="/path/to/configfile",
    help="changes sysconfig directory",
    default=os.path.join("/", "etc", "conf.d")
)
parser.add_argument('--version', action='version', version=__version__)
parser.add_argument(  # log level
    '--log-level',
    action='store',
    default="WARNING",
    help="sets logging level"
)
args = parser.parse_args()

if TESTING:
    main_config_file_path = "../test/btrfs-sbm.toml"
    default_options_file_path = "../test/btrfs-sbm-default.toml"
else:
    main_config_file_path = os.path.join(args.sysconfig_dir, "btrfs-sbm.toml")
    default_options_file_path = os.path.join(args.sysconfig_dir,
                                             "btrfs-sbm-default.toml")

if TESTING:
    log_Path = "../test/testlog.log"
else:
    log_Path = os.path.join("/", "var", "log", "btrfs-sbm.log")

numeric_log_level = getattr(logging, args.log_level.upper(), None)
if not isinstance(numeric_log_level, int):
    raise ValueError(f"Invalid log level: {args.log_level}")
    sys.exit(1)

logging.basicConfig(filename=log_Path, level=numeric_log_level)
logging.info("logging started")

main_configuration = {}
default_options = {}

main_configuration = read_config_file(main_config_file_path, "main")

if not main_configuration:  # empty dict evaluates as false
    logging.warning(f"main configuration file not found at "
                    f"{main_config_file_path}. No subvolumes configured. "
                    f"Please run script with --create-config option to create "
                    f"a config. This will create a non empty config file."
                    )

default_options = read_config_file(default_options_file_path, "default")

if not default_options:  # empty dict evaluates as false
    logging.error(f"default configuration file not found at "
                  f"{default_options_file_path}. Using defaults in script"
                  )
    default_options = {
        'keep-hourly': 10,
        'keep-daily': 10,
        'keep-weekly': 0,
        'keep-monthly': 10,
        'keep-yearly': 10
    }

if main_configuration:  # empty dict evaluates as false

    subvolumes = []

    # creating subvolume and snapshot objects
    # for string, dict
    for subvolume, contents in main_config.items():
        sub_name = subvolume
        sub_path = contents['path']
        temp_sub = btrfs.Subvolume(sub_name, sub_path)
        for snapshot, data in contents['snapshots'].items():
            path = data['path']
            creation_date_time = data['creation-date-time']
            type_ = data['type']
            temp_snapshot = btrfs.Snapshot(snapshot, path, type_,
                                           creation_date_time, self, True
                                           )
            temp_sub.append_snapshot(temp_snapshot)
        temp_sub.sort()  # make sure all snapshots are ordered by creation date
        subvolumes.append(temp_sub)

    subvolumes.sort()  # alphabetize subvolume objects in list

    # main command select
    if args.list_subvolumes:
        """Lists known subvolumes"""
        fmt_string = "{name:<10}|{path:<20}"
        print(fmt_string.format(name="Subvolume", path="Path"))
        print(
            fmt_string.format(name="----------", path="--------------------"))
        for subvol in subvolumes:
            print(fmt_string.format(name=subvol.name, path=subvol.path))

    elif args.init_subvolume is not None:
        """Initializes subvolume backups"""
        subvolume_path = args.init_subvolume
        if btrfs_subvolume_exists(subvolume_path):

            time_now = datetime.now()
            subvolume_name = os.path.basename(os.path.normpath(subvolume_path))

            snapshot_name = subvolume_name + "-" + time_now.isoformat()

            snapshot_subvol_path = os.path.join(subvolume_path,
                                                snapshot_subvol_name)

            # add subvolume to config table
            if subvolume_name not in main_config['configs']:
                main_config['configs'][subvolume_name] = {}  # init dicts
                main_config['configs'][subvolume_name]['options'] = {}
                main_config['configs'][subvolume_name]['snapshots'] = {}
                main_config['configs'][subvolume_name]['snapshots'][
                    snapshot_name] = {}

                main_config['configs'][subvolume_name]['name'] = subvolume_name
                main_config['configs'][subvolume_name]['path'] = subvolume_path

                for config, value in default_config.items():
                    # print(config, value)
                    try:
                        tmp = input(f"How many {config.split('-')[1]} "
                                    f"snapshots to keep? (Default={value}): ")
                    except SyntaxError:
                        tmp = ""
                    if tmp != "":
                        main_config['configs'][subvolume_name]['options'][
                            config] = int(tmp)
                    else:
                        main_config['configs'][subvolume_name]['options'][
                            config] = int(value)

                # create .snapshots subvolume
                if not btrfs_subvolume_exists(snapshot_subvol_path):
                    btrfs_create_subvolume(snapshot_subvol_path)

                # create first snapshot
                btrfs_take_snapshot(
                    subvolume_path,
                    os.path.join(snapshot_subvol_path, snapshot_name), True)

                main_config['configs'][subvolume_name]['snapshots'][
                    snapshot_name]['name'] = snapshot_name
                main_config['configs'][subvolume_name]['snapshots'][
                    snapshot_name]['path'] = os.path.join(
                        subvolume_path, snapshot_subvol_name, snapshot_name)
                main_config['configs'][subvolume_name]['snapshots'][
                    snapshot_name]['creation-date-time'] = str(
                        time_now.isoformat())
                main_config['configs'][subvolume_name]['snapshots'][
                    snapshot_name]['type'] = "init"

                # TODO: send intial snapshot to b2
                # btrfs_send_snapshot_diff with no "new" path, then
                # use returned path into b2 uploader tool to do excrytption,
                # compression # and uploads
            else:
                print(f"subvolume config {subvolume_name} already exists. "
                      f"Please use --show-config or --edit config instead"
                      )
                sys.exit(1)

        else:
            print(f"{path} is not a btrfs subvolume. Make sure you typed it "
                  f"correctly"
                  )
            sys.exit(1)

    elif args.delete_subvolume is not None:
        config_name = args.delete_subvolume

        if config_name in main_config['configs']:
            if args.delete_snapshots:  # also delete snapshots
                for snapshots, snapshot in main_config['configs'][config_name][
                        'snapshots'].items():
                    if btrfs_subvolume_exists(snapshot['path']):
                        btrfs_delete_subvolume(snapshot['path'])
                    else:
                        logging.warning(f"Snapshot: {snapshot['name']} did "
                                        f"not exist at {snapshot['path']}."
                                        f"Ignoring"
                                        )
                # delete snapshot directory last
                snapshot_subvol_path = os.path.join(
                    main_config['configs'][config]['path'],
                    snapshot_subvol_name)
                if btrfs_subvolume_exists(snapshot_subvol_path):
                    btrfs_delete_subvolume(snapshot_subvol_path)
                else:
                    logging.warning(f"{snapshot_subvol_name} subvolume did "
                                    f"not exist. This is odd"
                                    )
            del main_config['configs'][config_name]  # remove dictionary
        else:
            print(f"{config_name} did not exist in the list of configs. Make "
                  f"sure you typed it correctly or use --list-configs to view "
                  f"available configs"
                  )
            sys.exit(1)

    elif args.show_subvolume is not None:
        config_name = args.show_subvolume

        if config_name in main_config['configs']:
            print(toml.dumps(main_config['configs'][config_name]))
        else:
            print(f"{config_name} did not exist in the list of configs. Make "
                  f"sure you typed it correctly or use --list-configs to view "
                  f"available configs"
                  )
            sys.exit(1)

    elif args.edit_subvolume is not None:
        config_name = args.edit_subvolume

        if config_name in main_config['configs']:
            print(toml.dumps(main_config['configs'][config_name]))
            # TODO: look into python editor or implement subset myself
        else:
            print(f"{config_name} did not exist in the list of configs. Make "
                  f"sure you typed it correctly or use --list-configs to view "
                  f"available configs"
                  )
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

    else:  # automatic functionality
        time_now = datetime.now()

        # loop through all subvolume configs except default
        for key, subvolume in main_config['configs'].items():

            subvolume_name = subvolume['name']
            subvolume_path = subvolume['path']

            snapshot_name = subvolume_name + "-" + time_now.isoformat()
            snapshot_subvol_path = os.path.join(subvolume_path,
                                                snapshot_subvol_name)

            newest_snapshot = max(
                subvolume['snapshots'].items(),
                key=lambda x: x[1]['creation-date-time'])[0]
            newest_snapshot_time = datetime.fromisoformat(
                subvolume['snapshots'][newest_snapshot]['creation-date-time'])
            # delta between last snapshot and now is at least 1 hour
            if time_now >= newest_snapshot_time + timedelta(hours=1):
                subvolume['snapshots'][snapshot_name] = {}
                # assuming subvol and .snapshot directory already exist
                btrfs_take_snapshot(
                    subvolume['path'],
                    os.path.join(snapshot_subvol_path, snapshot_name), True)
                subvolume['snapshots'][snapshot_name]['name'] = snapshot_name
                subvolume['snapshots'][snapshot_name]['path'] = os.path.join(
                    subvolume_path, snapshot_subvol_name, snapshot_name)
                subvolume['snapshots'][snapshot_name][
                    'creation-date-time'] = str(time_now.isoformat())

                if time_now.hour == 0 and not newest_snapshot_time.hour == 0:
                    subvolume['snapshots'][snapshot_name]['type'] = "daily"
                # begining of week = monday
                elif (
                        time_now.isoweekday() == 1
                        and not newest_snapshot_time.isoweekday() == 1):
                    subvolume['snapshots'][snapshot_name]['type'] = "weekly"
                # first day of month
                elif time_now.day == 1 and not newest_snapshot_time.day == 1:
                    subvolume['snapshots'][snapshot_name]['type'] = "monthly"
                # first day of year
                elif (
                        (time_now.month == 1 and time_now.day == 1) and not (
                        newest_snapshot_time.month == 1 and
                        newest_snapshot_time.day == 1)):
                    subvolume['snapshots'][snapshot_name]['type'] = "yearly"
                else:
                    subvolume['snapshots'][snapshot_name]['type'] = "hourly"
                # # TODO: btrfs send diff between snapshots
                # btrfs_send_snapshot_diff with no "new" path, then
                # use returned path into b2 updloader tool to do excrytption,
                # compression and uploads
            num_snapshots = {
                'hourly': 0,
                'daily': 0,
                'weekly': 0,
                'monthly': 0,
                'yearly': 0
            }
            snapshots_by_type = {
                'hourly': {},
                'daily': {},
                'weekly': {},
                'monthly': {},
                'yearly': {}
            }

            # count number of each type of snapshot
            for snapshots, snapshot in subvolume['snapshots'].items():
                snapshot_type = snapshot['type']
                if snapshot_type != 'init':
                    num_snapshots[snapshot_type] += 1
                    snapshots_by_type[snapshot_type][
                        snapshot['name']] = snapshot
                else:
                    pass

            print(num_snapshots)

            # check if number of snapshots of each type are over limit, and
            # remove oldest

            for type, value in num_snapshots.items():
                if value > subvolume['options']["keep-" + type]:
                    # list of snapshots
                    # lambda k: k[1]['creation-date-time'] the [1] is
                    # essentially selecting the value in the key value pair
                    # that is x where key = snapshots dict, and value is
                    # individual snapshot dict beneath it.
                    newlist = sorted(
                        snapshots_by_type[type].items(),
                        key=lambda k: k[1]['creation-date-time'])
                    # delete oldest snapshots up to max
                    for sel in range(value -
                                     subvolume['options']["keep-" + type]):
                        # newlist is list of tuples (snapshot name, snapshot
                        # dict) due to .items()
                        # need to select tuple within that, then select
                        # snapshot dict inside tuple
                        btrfs_delete_subvolume(newlist[sel][1]['path'])
                        del subvolume['snapshots'][newlist[sel][0]]
                else:
                    pass
                    # print("false")


else:
    pass  # continue on and save main config file

if os.path.exists(main_config_file_path):
    try:
        shutil.copy2(main_config_file_path, main_config_file_path + ".bak")
    except IOError as e:
        logging.critical(f"failed to backup main config file. "
                         f"See exception {e}"
                         )
        sys.exit(1)
    try:
        f = open(main_config_file_path, 'w')  # overwrites file
    except IOError as e:
        logging.critical(f"main config file could not be opened. "
                         f"See exception {e}"
                         )
        sys.exit(1)
    toml.dump(main_config, f)  # write config file
else:
    logging.warning(f"main config file did not exist. Creating now "
                    f"at {main_config_file_path}."
                    )
    try:
        f = open(main_config_file_path,
                 'w+')  # create and update file (truncates)
    except IOError as e:
        logging.critical(f"Could not create new config file at "
                         f"{main_config_file_path}. See exception {e}"
                         )
        sys.exit(1)

logging.shutdown()
