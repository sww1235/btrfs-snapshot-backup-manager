"""Python interface to btrfs-progs commands."""

import os.path
import subprocess  # Calling btrfs commands
from datetime import datetime, timedelta
from functools import total_ordering  # help with sorting methods

# TODO: remove in production version
TESTING = True


# TODO: Need to capture errors from btrfs commands as exceptions
@total_ordering
class Subvolume:
    """Represents a btrfs subvolume."""

    def __init__(self, path, name, hourly, daily, weekly, monthly, yearly):
        """Initialize Subvolume class at path.

        This is used to create subvolume objects only, and may not represent a
        physical on-disk subvolume.
        This will be tested at creation time using the self.exists() method.
        """
        self.path = path
        self.name = name
        self.keep_hourly = hourly
        self.keep_daily = daily
        self.keep_weekly = weekly
        self.keep_monthly = monthly
        self.keep_yearly = yearly
        # if the subvolume physically exists, otherwise create it
        if self.exists():
            self.physical = True
        else:
            self.create()
            self.physical = True
        self._snapshots = []

    def __repr__(self):
        """Return string representation of class."""
        return f"Subvolume {self.name} at {self.path}"

    def __len__(self):
        """Length Method for iterating Snapshots in Subvolume."""
        return len(self._snapshots)

    def __getitem__(self, position):
        """Return a Snapshot associated with Subvolume."""
        return self._snapshots[position]

    def __eq__(self, other):
        """Check if Subvolumes are equal."""
        return (self.path == other.path
                and self.name == other.name
                and self.physical == other.physical
                )

    def __lt__(self, other):
        """Check if Subvolumes are less than another subvolume.

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
                logging.error(return_val.stderr)
                return False
            else:
                return True

    @classmethod
    def create(cls, path):
        """Create a btrfs subvolume at path.

        Uses btrfs-progs subvolume command to create a new subvolume
        only used to create .snapshots subvolume if it doesn't exist
        """
        if TESTING:
            print(f"btrfs subvolume create {path}")
        else:
            subprocess.run(["btrfs", "subvolume", "create", path],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            logging.info(return_val.stdout)
            logging.error(return_val.stderr)
        logging.info(f"Creating new subvolume at {path}")
        subvolume_name = os.path.basename(os.path.normpath(path))
        return cls(self.path, subvolume_name)

    def delete(self):
        """Delete a btrfs subvolume at path.

        Uses btrfs-progs subvolume command to delete a subvolume. Cannot
        recursively delete subvolumes.
        Keyword arguments:
        path -- path to subvolume as string
        """
        if self.physical:
            if TESTING:
                print(f"btrfs subvolume delete {self.path}")
            else:
                subprocess.run(["btrfs", "subvolume", "delete", self.path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            logging.info(f"Deleting subvolume at {self.path}")
        else:
            logging.error(f"Could not delete subvolume at {self.path}."
                          f"Did not exist on disk"
                          )

    def btrfs_take_snapshot(self, dest, type_, ro):
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
        # TODO: append snapshot to list of snapshots in subvol
        if self.physical:
            time_now = datetime.now()
            snapshot_name = self.name + "-" + time_now.isoformat()
            if ro:
                if TESTING:
                    print(f"btrfs subvolume snapshot -r {self.path} {dest}")
                else:
                    return_val = subprocess.run(
                        ["btrfs", "subvolume", "snapshot", "-r",
                            self.path, dest],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                logging.info(f"Taking new read only snapshot of "
                             f"{self.path} at {dest}"
                             )
            else:
                if TESTING:
                    print(f"btrfs subvolume snapshot {self.path} {dest}")
                else:
                    return_val = subprocess.run(
                        ["btrfs", "subvolume", "snapshot", self.path, dest],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                logging.info(f"Taking new snapshot of {self.path} at {dest}")
            if not TESTING:
                # log stdout and stderr from btrfs commands
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            return Snapshot(snapshot_name, type_, time_now, self, ro)
        else:
            logging.error(f"subvolume {self.name} does not exist on disk.")
            return None

    def append_snapshot(self, snaphot):
        """Append precreated snapshot object to list of snapshots.

        currently only used when reading existing config file
        """
        self._snapshots.append(snapshot)

    def sort(self):
        """Sort snapshots in Subvolume."""
        self._snapshots.sort()

    def btrfs_send_snapshot_diff(self, new=None):
        """Output diff between two subvolumes (snapshots) to a file.

        Keyword arguments:
        new -- snapshot object. (optional)
        """
        # TODO: Should this verify if new snapshot is actually newer?
        tmp_path = os.path.join("/", "tmp")
        # both snapshots exist on disk
        if new and new.physical and self.physical:
            diff_filename = (self.name + "::" + new.name)
            diff_filepath = os.path.join(tmp_path, diff_filename)
            if testing:
                print(f"btrfs send -p {self.path} -f {diff_filepath} "
                      f"{new.path}"
                      )
            else:
                subprocess.run(["btrfs", "send", "-p", self.path, "-f",
                                diff_filepath, new.path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            logging.info(f"Sending difference between {self.name} and "
                         f"{new.name} to {diff_filepath}"
                         )
        elif self.physical:
            diff_filename = "init" + "::" + self.name
            diff_filepath = os.path.join(tmp_path, diff_filename)
            if testing:
                print(f"btrfs send -f {diff_filepath} {self.path}")
            else:
                subprocess.run(["btrfs", "send", "-f", diff_filepath,
                               self.path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            logging.info(f"Sending {self.name} to {diff_filepath}")

        return filepath  # return path of snapshot diff


@total_ordering  # add extra comparison operators
class Snapshot(Subvolume):
    """Represents a btrfs snapshot, which is a special case of subvolume."""

    def __init__(self, name, path, snapshot_type, creation_date_time,
                 subvolume, read_only):
        """Initialize Snapshot class."""
        self.name = name
        self.path = path
        self.snapshot_type = snapshot_type
        self.creation_date_time = creation_date_time
        self.read_only = read_only
        self.subvolume = subvolume
        self._snapshots = None  # don't want snapshots of snapshots
        super().__init__(self)  # add instance variables from superclass

    def __repr__(self):
        """Return string representation of class."""
        return f"Snapshot {self.name} of {self.type} at {self.path}"

    def __eq__(self, other):
        """Check if Snapshots are equal."""
        return (self.path == other.path
                and self.name == other.name
                and self.subvolume == other.subvolume
                and self.creation_date_time == other.creation_date_time
                and self.snapshot_type == other.snapshot_type
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
                logging.error(return_val.stderr)
                return False
            else:
                return True

    def btrfs_take_snapshot(self, dest, ro):
        """Don't want snapshots of snapshots."""
        logging.error(f"No snapshots of snapshots plox. {self.name}"
                      f"is a snapshot. This is an error"
                      )
        return None

    def btrfs_snapshot_diff_check(self, new):
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
