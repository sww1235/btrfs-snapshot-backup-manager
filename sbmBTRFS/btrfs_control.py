"""Python interface to btrfs-progs commands."""

# TODO: remove in production version
TESTING = True


class Subvolume:
    """Represents a btrfs subvolume."""

    def __init__(self, path, name):
        """Initialize Subvolume class at path.

        This is used to create subvolume objects only, and may not represent a
        physical on-disk subvolume.
        This will be tested at creation time using the self.exists() method.
        """
        self.path = path
        self.name = name
        self.physical = self.exists()

    def exists(self):
        """Check if subvolume object corresponds to an actual subvolume.

        Uses btrfs subvolume show command to detect if a subvolume exists
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

    @classmethod
    def create(cls, path):
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
        subvolume_name = os.path.basename(os.path.normpath(path))
        return cls(path, subvolume_name)

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

    def btrfs_take_snapshot(self, dest, ro):
        """Take a snapshot of a btrfs subvolume.

        Uses btrfs-progs snapshot command to take a snapshot of the src
        subvolume
        Keyword arguments:
        dest -- path to destination snapshot as string. This includes the name
        of the snapshot itself.
        See the documentation of btrfs subvolume for further details.
        ro -- whether to take a read only snapshot
        """
        if self.exists:
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
                return Snapshot()
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
        else:
            logging.error(f"subvolume {self.name} does not exist on disk.")

    def btrfs_send_snapshot_diff(self, new=None):
        """Output diff between two subvolumes (snapshots) to a file.

        Keyword arguments:
        new -- path to newer subvolume (snapshots) as string. (optional)
        """
        tmp_path = os.path.join("/", "tmp")
        if new:
            filename = (os.path.basename(self.path)
                        + "::"
                        + os.path.basename(new))
            filepath = os.path.join(tmp_path, filename)
            if testing:
                print(f"btrfs send -p {old} -f {filepath} {new}")
            else:
                subprocess.run(["btrfs", "send", "-p", old, "-f", filename, new],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            logging.info(f"Sending difference between {old} and "
                         f"{new} to {filepath}"
                         )
        else:
            filename = "init" + "::" + os.path.basename(old)
            filepath = os.path.join(tmp_path, filename)
            if testing:
                print(f"btrfs send -f {filepath} {old}")
            else:
                subprocess.run(["btrfs", "send", "-f", filepath, old],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
                logging.info(return_val.stdout)
                logging.error(return_val.stderr)
            logging.info(f"Sending {old} to {filepath}")

        return filepath


class Snapshot(Subvolume):
    """Represents a btrfs snapshot, which is a special case of subvolume."""

    def __init__(self, name, snapshot_type, creation_date_time, subvolume,
                 read_only):
        """Initialize Snapshot class."""
        self.name = name
        self.snapshot_type = snapshot_type
        self.creation_date_time = creation_date_time
        self.read_only = read_only
        self.subvolume = subvolume
        super().__init__(self)  # add instance variables from superclass
