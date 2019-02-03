"""Python interface to btrfs-progs commands."""

# TODO: remove in production version
TESTING = True


class Subvolume:
    """Represents a btrfs subvolume."""

    def __init__(self, path):
        """Initialize Subvolume class at path.

        This is used to create subvolume objects only, and may not represent a
        physical on-disk subvolume.
        """
        self.path = path

    def exists(self):
        """Check if subvolume object corresponds to an actual subvolume.

        Uses btrfs subvolume show command to detect if a subvolume exists
        Keyword arguments:
        path -- path to subvolume as string
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

    @staticmethod
    def create(path):
        """Create a btrfs subvolume at path.

        Uses btrfs-progs subvolume command to create a new subvolume
        Keyword arguments:
        path -- path to subvolume as string
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

    def delete(self):
        """Delete a btrfs subvolume at path.

        Uses btrfs-progs subvolume command to delete a subvolume. Cannot
        recursively delete subvolumes.
        Keyword arguments:
        path -- path to subvolume as string
        """
        if TESTING:
            print(f"btrfs subvolume delete {path}")
        else:
            subprocess.run(["btrfs", "subvolume", "delete", path],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
            logging.info(return_val.stdout)
            logging.error(return_val.stderr)
        logging.info(f"Deleting subvolume at {path}")

    def btrfs_take_snapshot(self, src, dest, ro):
        """Take a snapshot of a btrfs subvolume.

        Uses btrfs-progs snapshot command to take a snapshot of the src
        subvolume
        Keyword arguments:
        src -- path to source subvolume as string
        dest -- path to destination snapshot as string. This includes the name
        of the snapshot itself.
        See the documentation of btrfs subvolume for further details.
        ro -- whether to take a read only snapshot
        """
        if ro:
            if TESTING:
                print(f"btrfs subvolume snapshot -r {src} {dest}")
            else:
                return_val = subprocess.run(
                    ["btrfs", "subvolume", "snapshot", "-r", src, dest],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            logging.info(f"Taking new read only snapshot of {src} at {dest}")
        else:
            if TESTING:
                print(f"btrfs subvolume snapshot {src} {dest}")
            else:
                return_val = subprocess.run(
                    ["btrfs", "subvolume", "snapshot", src, dest],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
            logging.info(f"Taking new snapshot of {src} at {dest}")
        if not TESTING:
            # log stdout and stderr from btrfs commands
            logging.info(return_val.stdout)
            logging.error(return_val.stderr)


class Snapshot(Subvolume):
    """Represents a btrfs snapshot, which is a special case of subvolume."""

    def __init__(self, name, snapshot_type, creation_date_time):
        """Initialize Snapshot class."""
        self.name = name
        self.snapshot_type = snapshot_type
        self.creation_date_time = creation_date_time
        super().__init__(self)  # add instance variables from superclass
