# btrfs-snapshot-backup-manager
A simple collection of bash scripts to manage BTRFS snapshots per subvolume and incremental backups


## Objectives

Want to create similar functionality to [snapper](https://github.com/openSUSE/snapper) but via scripting rather than c++. This is to allow for easier extensibilty and modification when BTRFS or something else changes. I also feel that this solution is closer to the unixy paradigm of small programs that were woven together with scripts.
