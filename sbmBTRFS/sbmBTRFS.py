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
# TODO: add command to show snapshot diff changes.

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


def list_subvolumes():
    """List known subvolumes with index."""
    fmt_string = "{number:<2}|{name:<10}|{path:<20}"
    print(fmt_string.format(number="", name="Subvolume", path="Path"))
    print(
        fmt_string.format(number="--", name="----------",
                          path="--------------------"
                          )
         )
    for index, subvol in enumerate(subvolumes):
        print(fmt_string.format(number=str(index), name=subvol.name,
                                path=subvol.path
                                )
              )

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
action_group.add_argument(  # delete subvolume
    '--delete-subvolume',
    action='store',
    metavar="config-name",
    help=("removes subvolume configuration from known list, does not "
          "delete associated snapshots"
          )
)
parser.add_argument(  # delete snapshots
    '--delete-snapshots',
    action='store_true',
    default=False,
    help=("combine with --delete-subvolume to delete snapshot directory, does "
          "nothing by itself"
          )
)
action_group.add_argument(  # show subvolume
    '--show-subvolume',
    action='store',
    metavar="snapshot-name",
    help="prints configuration for specific subvolume"
)
action_group.add_argument(  # edit subvolume
    '--edit-subvolume',
    action='store',
    metavar="snapshot-name",
    help="prompts to change configuration values for specific subvolume"
)
action_group.add_argument(  # list snapshot
    '--list-snapshots',
    action='store',
    metavar="snapshot-name",
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
    metavar="subvolume-name",
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
                    f"Please run script with --init-subvolume option to "
                    f"initialize subvolume. This will create a non empty "
                    f"config file."
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
        snapshots_subvol = contents['snapshots-subvol']
        keep_hourly = contents['keep-hourly']
        keep_daily = contents['keep-daily']
        keep_weekly = contents['keep-weekly']
        keep_monthly = contents['keep-monthly']
        keep_yearly = contents['keep-yearly']
        temp_sub = btrfs.Subvolume(sub_path, keep_hourly,
                                   keep_daily, keep_weekly, keep_monthly,
                                   keep_yearly
                                   )
        for snapshot, data in contents['snapshots'].items():
            path = data['path']
            creation_date_time = datetime.fromisoformat(
                                 data['creation-date-time'])
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
        list_subvolumes()

    elif args.init_subvolume is not None:
        """Initializes subvolume backups"""
        subvolume_path = args.init_subvolume
        subvolume_name = os.path.basename(os.path.normpath(subvolume_path))

        for option, value in default_options.items():
            # print(config, value)
            try:
                tmp = input(f"How many {option.split('-')[1]} "
                            f"snapshots to keep? (Default={value}): ")
            except SyntaxError:  # empty input
                tmp = ""

            if option == "keep-hourly":
                if tmp != "":
                    keep_hourly = int(tmp)
                else:
                    keep_hourly = int(value)
            elif option == "keep-daily":
                if tmp != "":
                    keep_daily = int(tmp)
                else:
                    keep_daily = int(value)
            elif option == "keep-weekly":
                if tmp != "":
                    keep_weekly = int(tmp)
                else:
                    keep_weekly = int(value)
            elif option == "keep-monthly":
                if tmp != "":
                    keep_monthly = int(tmp)
                else:
                    keep_monthly = int(value)
            elif option == "keep-yearly":
                if tmp != "":
                    keep_yearly = int(tmp)
                else:
                    keep_yearly = int(value)

        temp_sub = btrfs.Subvolume(sub_path, snapshot_subvol_name,
                                   keep_hourly, keep_daily, keep_weekly,
                                   keep_monthly, keep_yearly
                                   )

        if temp_sub in subvolumes:
            print(f"subvolume {subvolume_name} is already configured. "
                  f"Please use --show-config or --edit config instead"
                  f"Subvolume names must be unique"
                  )
            sys.exit(1)  # because this will only be used in interactive mode
        elif temp_sub.physical:
            # create first snapshot
            init_snap = temp_sub.take_snapshot("init", True)
            # init_diff_path = init_snap.send_snapshot_diff()
            # TODO: send intial snapshot to b2
            # btrfs_send_snapshot_diff with no "new" path, then
            # use returned path into b2 uploader tool to do excrytption,
            # compression # and uploads

        else:
            print(f"{subvolume_path} is not a btrfs subvolume. Please verify "
                  f"you typed it correctly. Make sure to use"
                  )
            sys.exit(1)  # because this will only be used in interactive mode

    elif args.delete_subvolume is not None:
        subvolume_name = args.delete_subvolume

        # this is a conditional expression and list comprehension.
        # returns a subset of the subvolumes list that only has elements where
        # subvol.name == subvolume_name
        # In theory, since subvolume names should be unique, this will result
        # in a 1 element list.
        temp_sub_list = (subvol if subvol.name == subvolume_name else None for
                         subvol in subvolumes)
        if len(temp_sub_list) > 1:
            logging.critical(f"Subvolumes with duplicate names detected, this "
                             f"should not happen. Check config file for "
                             f"Multiple instances of {subvolume_name}"
                             )
        temp_sub = temp_sub_list[0]  # get only element of list
        if temp_sub:  # None == False
            if args.delete_snapshots:  # also delete snapshots
                for snapshot in temp_sub:
                    if snapshot.physical:
                        temp_sub.delete_snapshot(snapshot)  # instance method
                    else:
                        logging.warning(f"Snapshot: {snapshot.name} did "
                                        f"not exist at {snapshot.path}."
                                        f"Ignoring"
                                        )
                # delete snapshot directory last
                snapshot_subvol_path = os.path.join(temp_sub.path,
                                                    temp_sub.snapshots_subvol
                                                    )
                if temp_sub.exists(snapshot_subvol_path):  # class method
                    temp_sub.delete(snapshot_subvol_path)  # class method
                else:
                    logging.warning(f"{snapshot_subvol_name} subvolume did "
                                    f"not exist. This is odd"
                                    )
            # finally, remove subvolume object from list of subvolumes
            subvolumes.remove(temp_sub)
        else:
            print(f"{subvolume_name} did not exist in the list of subvolumes. "
                  f"Make sure you typed it correctly or use --list-subvolumes "
                  f"to view configured subvolumes"
                  )
            sys.exit(1)

    elif args.show_subvolume is not None:
        subvolume_name = args.show_subvolume

        temp_sub_list = (subvol if subvol.name == subvolume_name else None for
                         subvol in subvolumes)
        if len(temp_sub_list) > 1:
            logging.critical(f"Subvolumes with duplicate names detected, this "
                             f"should not happen. Check config file for "
                             f"Multiple instances of {subvolume_name}"
                             )
        temp_sub = temp_sub_list[0]  # get only element of list

        if temp_sub:
            print(temp_sub)
        else:
            print(f"{subvolume_name} did not exist in the list of configs. "
                  f"Make sure you typed it correctly or use --list-subvolumes "
                  f"to view configured snapshots"
                  )
            sys.exit(1)

    elif args.edit_subvolume is not None:
        pass
        # TODO: look into python editor or implement subset myself

    elif args.list_snapshots is not None:
        subvolume_name = args.list_snapshots
        temp_sub_list = (subvol if subvol.name == subvolume_name else None for
                         subvol in subvolumes)
        if len(temp_sub_list) > 1:
            logging.critical(f"Subvolumes with duplicate names detected, this "
                             f"should not happen. Check config file for "
                             f"Multiple instances of {subvolume_name}"
                             )
        temp_sub = temp_sub_list[0]  # get only element of list
        temp_sub.list_snapshots()  # prints all snapshots in subvolume

    elif args.list_all_snapshots:
        for subvolume in subvolumes:
            print("Snapshots in ", subvolume)
            subvolume.list_snapshots()

    elif args.delete_snapshot is not None:
        subvolume_name = args.delete_snapshot
        temp_sub_list = (subvol if subvol.name == subvolume_name else None for
                         subvol in subvolumes)
        if len(temp_sub_list) > 1:
            logging.critical(f"Subvolumes with duplicate names detected, this "
                             f"should not happen. Check config file for "
                             f"Multiple instances of {subvolume_name}"
                             )
        temp_sub = temp_sub_list[0]  # get only element of list
        temp_sub.list_snapshots()  # prints all snapshots in subvolume

        while True:
            try:
                tmp = input("Enter number of the snapshot you want "
                            "to delete: ")
            except SyntaxError:  # empty input
                tmp = ""
            if tmp == "":
                print("Exiting!")
                sys.exit(0)  # this is fine due to interactive command
            else:
                try:
                    index = int(tmp)
                except ValueError:
                    print(f"The value you entered, {tmp}, was not an integer. "
                          f"Please try again.")
                    continue
                if index < len(temp_sub):
                    break
                else:
                    print("You entered a number that does not correspond to a "
                          "known snapshot. Please try again.")
                    continue

        while True:
            try:
                answer = input(f"Is the following the snapshot you "
                               f"selected for "
                               f"deletion:\n{temp_sub[index]}\n"
                               f"Please enter \"Y\" or \"N\".")
            except SyntaxError:  # empty input
                continue
            if answer.upper() == "N":
                print("Exiting!")
                sys.exit(0)  # this is fine due to interactive command
            elif answer.upper() == "Y":
                break
                temp_sub.delete_snapshot(temp_sub[index])
            else:
                print("You did not enter \"Y\" or \"N\". Please try again.")
                continue

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
                # TODO: btrfs send diff between snapshots
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
