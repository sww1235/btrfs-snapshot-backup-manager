import toml
import argparse


# external files
# - log = /var/log/btrfs-sbm.log
# - main settings = /etc/conf.d/btrfs-sbm.toml



# first thing, read command line options

#

def parse_cmd_line_args():
    # parse command line arguements
    parser = argparse.ArgumentParser()
    parser.add_argument('--hourly',) # takes hourly snapshot
    parser.add_argument('--daily') # takes daily snapshot
    parser.add_argument('--list-configs') # prints list of all known configs
    parser.add_argument('--create-config') # initializes subvolume snapshots and creates config file
    parser.add_argument('--delete-config') # removes config from table in main config file, does not delete snapshot
    parser.add_argument('--delete-snapshots') # combine with --delete-config to delete snapshot directory, does nothing by itself
    parser.add_argument('--show-config')
    parser.add_argument('--edit-config')
    parser.add_argument('--status')
    parser.add_argument('--sysconfig-dir')
    parser.add_argument('--version')


def take_snapshot(config_name, config_path):

def createconfig():
# add




# read main settings file

# read in settings files of all configs

# process, take snapshot,
