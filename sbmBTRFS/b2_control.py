"""Setup and interface to b2 upload service."""

from b2sdk.account_info.sqlite_account_info import SqliteAccountInfo
from b2sdk.api import B2Api


class B2CloudInterface():
    """Interface for Backblaze B2 APIself.

    Allows for uploading and downloading files to buckets and
    listing bucket contents.
    """

    def __init__(self, arg):
        """Initialize B2 connection and credentials."""
        info = SqliteAccountInfo()  # creds and tokens in ~/.b2_account_info
        b2_api = B2Api(info)
        self.arg = arg
