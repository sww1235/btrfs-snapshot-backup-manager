"""Python interface to btrfs-progs commands."""

import os.path
import subprocess  # Calling btrfs commands
import logging
from datetime import datetime
from functools import total_ordering  # help with sorting methods

# TODO: remove in production version
TESTING = True

# Setup module based logging, attaches to logger from parent module
logger = logging.getLogger(__name__)

# TODO: Need to capture errors from btrfs commands as exceptions
# TODO: Change snapshot type into an enum
@total_ordering
class Subvolume:
    """Represents a btrfs subvolume."""

    def __init__(self, path, snapshots_subvol, hourly, daily,
                 weekly, monthly, yearly):
        """Initialize Subvolume class at path.

        This is used to create subvolume objects only, and may not represent a
        physical on-disk subvolume.
        This will be tested at creation time using the self.exists() method.
        """
        self.path = path
        self.name = os.path.basename(os.path.normpath(path))
        self.snapshots_subvol = snapshots_subvol
        self.num_snapshots = {
            'hourly': 0,
            'daily': 0,
            'weekly': 0,
            'monthly': 0,
            'yearly': 0
        }
        self.keep_snapshots = {
            'hourly': hourly,
            'daily': daily,
            'weekly': weekly,
            'monthly': monthly,
            'yearly': yearly
        }
        # if the subvolume physically exists, otherwise mark as non physical
        # and log
        if self.exists(self.path):
            self.physical = True
            # if .snapshots subvolume exists, otherwise create it
            if not self.exists(os.path.join(self.path, self.snapshot_subvol)):
                self.create(os.path.join(self.path, self.snapshot_subvol))
        else:
            self.physical = False
        self._snapshots = []

    def __repr__(self):
        """Return string representation of class."""
        return f"Subvolume {self.name} at {self.path}"

    def __str__(self):
        """Return useful string representation of class."""
        ret_str = f"Subvolume {self.name} at {self.path}\n"
        ret_str += f"It is configured to keep:\n"
        for name, value in self.keep_snapshots.items():
            ret_str += f"{value} {name} snapshots\n"
        return ret_str

    def __len__(self):
        """Length Method for iterating Snapshots in Subvolume."""
        return len(self._snapshots)

    def __getitem__(self, position):
        """Return a Snapshot associated with Subvolume."""
        return self._snapshots[position]

    def __eq__(self, other):
        """Check if Subvolumes are equal.

        Enforcing subvolume name has to be unique
        """
        return (self.name == other.name)

    def __lt__(self, other):
        """Check if subvolume is less than another subvolume.

        Sorts based on name.
        """
        return self.name < other.name

    @classmethod
    def exists(cls, path):
        """Check if path corresponds to a subvolume on disk.

        Uses btrfs subvolume show command to detect if a subvolume exists.
        """
        if TESTING:
            return True
        else:
            return_val = subprocess.run(
                ["btrfs", "subvolume", "show", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE)
            if return_val.returncode != 0:
                logger.error(return_val.stderr)
                return False
            else:
                return True

    @classmethod
    def create(cls, path):
        """Create a btrfs subvolume at path.

        Uses btrfs-progs subvolume command to create a new subvolume.
        Only used to create .snapshots subvolume if it doesn't exist
        """
        if TESTING:
            print(f"btrfs subvolume create {path}")
        else:
            return_val = subprocess.run(
                        ["btrfs", "subvolume", "create", path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
            logger.debug(return_val.stdout)
            logger.error(return_val.stderr)
        logger.info(f"Creating new subvolume at {path}")

    @classmethod
    def delete(cls, path):
        """Delete the btrfs subvolume at path.

        Uses btrfs-progs subvolume command to delete a subvolume. Cannot
        recursively delete subvolumes. Only used to delete .snapshots subvolume
        """
        if cls.physical:
            if TESTING:
                print(f"btrfs subvolume delete {path}")
            else:
                return_val = subprocess.run(
                            ["btrfs", "subvolume", "delete", path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
                logger.debug(return_val.stdout)
                logger.error(return_val.stderr)
            logger.info(f"Deleting subvolume at {path}")

        else:
            logger.error(f"Could not delete subvolume at {path}."
                         f"Did not exist on disk"
                         )

    def take_snapshot(self, type_, ro=True):
        """Take a snapshot of a btrfs subvolume.

        Uses btrfs-progs snapshot command to take a snapshot of the src
        subvolume
        Keyword arguments:
        dest -- path to destination snapshot as string. This includes the name
        of the snapshot itself.
        See the documentation of btrfs subvolume for further details.
        type -- indicates type of snapshot
        ro -- whether to take a read only snapshot
        Returns a snapshot object.
        """
        # TODO: check if snapshot diff is empty, if it is discard snapshot.
        # This won't affect backup stuff, since the btrfs incremental send
        # will be between the previously saved snapshot, which is the one
        # before deleted snapshot
        if self.physical:
            time_now = datetime.now()
            snapshot_name = self.name + "-" + str(time_now.isoformat())
            snapshot_path = os.path.join(self.path, self.snapshot_subvol,
                                         snapshot_name
                                         )
            if ro:
                if TESTING:
                    print(f"btrfs subvolume snapshot "
                          f"-r {self.path} {snapshot_path}"
                          )
                else:
                    return_val = subprocess.run(
                        ["btrfs", "subvolume", "snapshot", "-r",
                            self.path, snapshot_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                logger.info(f"Taking new read only snapshot of "
                            f"{self.path} at {snapshot_path}"
                            )
            else:
                if TESTING:
                    print(f"btrfs subvolume snapshot "
                          f"{self.path} {snapshot_path}"
                          )
                else:
                    return_val = subprocess.run(
                        ["btrfs", "subvolume", "snapshot", self.path,
                            snapshot_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                logger.info(f"Taking new snapshot of {self.path} "
                            f"at {snapshot_path}"
                            )
            if not TESTING:
                # log stdout and stderr from btrfs commands
                logger.debug(return_val.stdout)
                logger.error(return_val.stderr)
            temp_snapshot = Snapshot(snapshot_name, snapshot_path, type_,
                                     time_now, self, ro
                                     )
            self._snapshots.append(temp_snapshot)
            self.num_snapshots[type_] += 1
            return temp_snapshot
        else:
            logger.error(f"subvolume {self.name} does not exist on disk. "
                         f"Cannot take snapshot!"
                         )

    def delete_snapshot(self, snapshot):
        """Delete snapshot from subvolume list."""
        self.num_snapshots[snapshot.type_] -= 1
        snapshot.delete()
        self._snapshots.remove(snapshot)

    def append_snapshot(self, snapshot):
        """Append precreated snapshot object to list of snapshots.

        currently only used when reading existing config file
        """
        self._snapshots.append(snapshot)
        self.num_snapshots[snapshot.type_] += 1

    def list_snapshots(self):
        """List snapshots in Subvolume with index."""
        fmt_string = "{number:<3}|{name:<10}|{path:<20}"
        print(fmt_string.format(number="", name="Snapshot", path="Path"))
        print(
            fmt_string.format(number="---", name="----------",
                              path="--------------------"
                              )
             )
        for index, snapshot in enumerate(self._snapshots):
            print(fmt_string.format(number=str(index), name=snapshot.name,
                                    path=snapshot.path
                                    )
                  )

    def newest_snapshot(self, type_=None):
        """Return newest snapshot known to subvolume.

        If type is not none, return newest snapshot of type known to subvolume.
        """
        self.sort()  # make sure list of snapshots is sorted asending
        if type_:
            # create a new list with just type_ snapshots in order
            sublist = [snapshot for snapshot in self._snapshots
                       if snapshot.type_ == type_]
            sublist.sort()
            return sublist[-1]  # return last (newest) snapshot of type in list
        else:
            return self._snapshots[-1]  # return last (newest) snapshot in list

    def oldest_snapshot(self, type_=None):
        """Return oldest snapshot known to subvolume.

        If type is not none, return oldest snapshot of type known to subvolume.
        """
        self.sort()  # make sure list of snapshots is sorted asending
        if type_:
            # create a new list with just type_ snapshots in order
            sublist = [snapshot for snapshot in self._snapshots
                       if snapshot.type_ == type_]
            sublist.sort()
            return sublist[0]  # return first (oldest) snapshot of type in list
        else:
            return self._snapshots[0]  # return first (oldest) snapshot in list

    def sort(self):
        """Sort snapshots in Subvolume."""
        self._snapshots.sort()


@total_ordering  # add extra comparison operators
class Snapshot():
    """Represents a btrfs snapshot."""

    def __init__(self, name, path, type_, creation_date_time,
                 subvolume, read_only):
        """Initialize Snapshot class."""
        self.name = name
        self.path = path
        self.type_ = type_
        self.creation_date_time = creation_date_time
        self.read_only = read_only
        self.subvolume = subvolume
        # if the snapshot physically exists, otherwise mark as non physical
        # and log
        if self.exists(self.path):
            self.physical = True
        else:
            self.physical = False

    def __repr__(self):
        """Return string representation of class."""
        return f"Snapshot {self.name} of {self.type} at {self.path}"

    def __eq__(self, other):
        """Check if Snapshots are equal."""
        return (self.path == other.path
                and self.name == other.name
                and self.subvolume == other.subvolume
                and self.creation_date_time == other.creation_date_time
                and self.type_ == other.type_
                and self.read_only == other.read_only
                )
        # TODO: this should probably use the btrfs_snapshot_diff_check method

    def __lt__(self, other):
        """Check if Subvolumes are less than another subvolume.

        This is defined as being created earlier than the other
        """
        return self.creation_date_time < other.creation_date_time

    def exists(self):
        """Check if snapshot object corresponds to a subvolume on disk.

        Uses btrfs subvolume show command to detect if a subvolume exists.
        """
        if TESTING:
            return True
        else:
            return_val = subprocess.run(
                ["btrfs", "subvolume", "show", self.path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE)
            if return_val.returncode != 0:
                logger.error(return_val.stderr)
                return False
            else:
                return True

    def delete(self):
        """Delete the btrfs snapshot it is called on.

        Uses btrfs-progs subvolume command to delete a subvolume. Cannot
        recursively delete subvolumes.
        """
        if self.physical:
            if TESTING:
                print(f"btrfs subvolume delete {self.path}")
            else:
                return_val = subprocess.run(
                            ["btrfs", "subvolume", "delete", self.path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
                logger.debug(return_val.stdout)
                logger.error(return_val.stderr)
            logger.info(f"Deleting snapshot at {self.path}")
        else:
            logger.error(f"Could not delete snapshot at {self.path}."
                         f"Did not exist on disk."
                         )

    def snapshot_diff_check(self, new):
        """Check if there is a difference between two snapshots (Subvolumes).

        Keyword arguments:
        new -- snapshot object.

        returns (bool, string)
        -- bool = True if there are any material differences between the
        two snapshots
        -- string = list of files that changed during shapshot
        """
        # TODO: utilize btrfs-snapshot-diff to do this once it is refactored.
        pass

    def export_snapshot_diff(self, new=None):
        """Output diff between two snapshots (subvolumes) to a file.

        Keyword arguments:
        new -- snapshot object. (optional)
        """
        # TODO: Should this verify if new snapshot is actually newer?
        tmp_path = os.path.join("/", "tmp")
        # both snapshots exist on disk
        if new and new.physical and self.physical:
            diff_filename = (self.name + "::" + new.name)
            diff_filepath = os.path.join(tmp_path, diff_filename)
            if TESTING:
                print(f"btrfs send -p {self.path} -f {diff_filepath} "
                      f"{new.path}"
                      )
            else:
                return_val = subprocess.run(
                            ["btrfs", "send", "-p", self.path, "-f",
                                diff_filepath, new.path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
                logger.debug(return_val.stdout)
                logger.error(return_val.stderr)
            logger.info(f"Sending difference between {self.name} and "
                        f"{new.name} to {diff_filepath}"
                        )
        elif self.physical:
            diff_filename = "init" + "::" + self.name
            diff_filepath = os.path.join(tmp_path, diff_filename)
            if TESTING:
                print(f"btrfs send -f {diff_filepath} {self.path}")
            else:
                subprocess.run(["btrfs", "send", "-f", diff_filepath,
                               self.path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logger.debug(return_val.stdout)
                logger.error(return_val.stderr)
            logger.info(f"Sending {self.name} to {diff_filepath}")

        return filepath  # return path of snapshot diff
