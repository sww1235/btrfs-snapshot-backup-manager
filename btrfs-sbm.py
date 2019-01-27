import toml
import argparse
import subprocess
import os.path
import datetime

# external files
# - log = /var/log/btrfs-sbm.log
# - main settings = /etc/conf.d/btrfs-sbm.toml

__version__ = "0.0.1"

def take_snapshot(src, dest, ro):
    """take btrfs snapshot"""
    if ro :
        subprocess.run(["btrfs", "snapshot", "-r", src, dest])
    else:
        subprocess.run(["btrfs", "snapshot", src, dest])

def createconfig(subvolume_path):
    """Initializes subvolume backups"""
    # init
    # add subvolume to config table
    # create .shapshots directory
    # create first snapshot
    # btrfs snapshot [-r] <source> <dest>|[<dest>/]<name>
    #subvolume_name = os.path.basename(os.path.normpath(subvolume_path))
    now = datetime.datetime.now()
    # btrfs snapshot -r /path/to/subvolume/ /path/to/subvolume/.shapshots
    take_snapshot(subvolume_path, os.path.join(subvolume, ".shapshots", subvolume_name + now.isoformat()), true)

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

main_config_file_path = os.path.join(args.sysconfig-dir,"btrfs-sbm.toml"

config = toml.load(main_config_file_path)







toml.dump(config, main_config_file_path)
