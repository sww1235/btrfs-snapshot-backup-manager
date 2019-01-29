# btrfs-snapshot-backup-manager
A simple collection of scripts to manage BTRFS snapshots per subvolume and incremental backups.


## Objectives

Want to create similar functionality to [snapper](https://github.com/openSUSE/snapper) but via scripting rather than c++. This is to allow for easier extensibilty and modification when BTRFS or something else changes. I also feel that this solution is closer to the unixy paradigm of small programs that were woven together with scripts. Snapper tries to do too much and so suffers from multiple APIs and dependancies and the lossage that accompanies.

This project will be attempting to follow the KISS principle as much as possible.

I will also be including scripts to automatically upload and manage snapshots with backblaze's B2 cloud backup service.

**NOTE:** This is only targeted at BTRFS snapshotting at present in order to be simpler. I presently only have use for BTRFS snapshotting and B2 backups so I will only implement those.

## Design Requirements

*   Support BTRFS snapshots
*   Support Backblaze B2 linux backup client.
*   Support multiple separate subvolumes with separate options
*   Support BTRFS quota system per subvolume
*   Utilize cron as scheduling system
*   Number and age cleanup algorithms
*   Manual snapshot creation functionality with ability to override deletion algorithms
*   ~~Filters for files/directories to not be snapshotted~~ (maybe, since this is not meant as a root snapshotting solution)
*   commands for create, list and delete configs
*   commands to list and delete snapshots
*   commands to diff snapshots

## Usage

The usage intention is to run the script every hour using cron or a cron
equivalent.

Make sure to implement locking using a mechanism like below in order to prevent
multiple instances of script running

```cron
# m h dom mon dow user  command
*/20 *  *  *  *  root /usr/bin/flock -w 0 /var/cron.lock /usr/bin/myscript
```
(<https://serverfault.com/questions/748943/using-flock-with-cron>)

## Notes

use `.snapshots` subvolume to store snapshots like snapper. ~~TODO: figure out snapshot naming scheme.~~

create config script:
(~~bash~~ or python, python might be easier since I could use .json or .yaml config files with dicts. Python also is required for b2 integration anyways.)

check for config name in list of configs, prompt user for unique name (maybe use something like hash of path or something as key in a dict)
checks for existing `.snapshot` subvolume and prompt user if it exists
creates `.snapshot` subvolume in appropriate location
add config to list of configs
ask user if they want to create first snapshot and backup now?

layout:

probably one main script, with a separate create config script (maybe).

main script has cmd line options in order to tell if it is being called hourly or daily

## Package Requirements

toml
