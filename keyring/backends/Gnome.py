import os

try:
    from gi.repository import GnomeKeyring
except ImportError:
    pass

from keyring.backend import KeyringBackend
from keyring.errors import PasswordSetError, PasswordDeleteError
from keyring.util import properties

class Keyring(KeyringBackend):
    """Gnome Keyring"""

    # Name of the keyring to store the passwords in.
    # Use None for the default keyring.
    KEYRING_NAME = None

    requisite_vars = [
        'GNOME_KEYRING_CONTROL',
        'DISPLAY',
        'DBUS_SESSION_BUS_ADDRESS',
    ]

    @properties.ClassProperty
    @classmethod
    def priority(cls):
        if 'gnomekeyring' not in globals():
            raise RuntimeError("gnomekeyring module required")
        return int(cls.has_requisite_vars())

    @classmethod
    def has_requisite_vars(cls):
        """
        Return True if the requisite environment vars are present in the
        environment.
        """
        return set(cls.requisite_vars).issubset(os.environ)

    def get_password(self, service, username):
        """Get password of the username for the service
        """
        service = self._safe_string(service)
        username = self._safe_string(username)
        attrs = GnomeKeyring.Attribute.list_new()
        GnomeKeyring.Attribute.list_append_string(attrs, 'user', username)
        GnomeKeyring.Attribute.list_append_string(attrs, 'domain', service)
        result, items = GnomeKeyring.find_items_sync(
            GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if result == GnomeKeyring.Result.IO_ERROR:
            return None
        if result == GnomeKeyring.Result.NO_MATCH:
            return None
        if result == GnomeKeyring.Result.CANCELLED:
            # The user pressed "Cancel" when prompted to unlock their keyring.
            return None

        assert len(items) == 1, 'no more than one entry should ever match'
        secret = items[0].secret
        return secret if isinstance(secret, unicode) else secret.decode('utf-8')

    def set_password(self, service, username, password):
        """Set password for the username of the service
        """
        service = self._safe_string(service)
        username = self._safe_string(username)
        password = self._safe_string(password)
        attrs = GnomeKeyring.Attribute.list_new()
        GnomeKeyring.Attribute.list_append_string(attrs, 'user', username)
        GnomeKeyring.Attribute.list_append_string(attrs, 'domain', service)
        result = GnomeKeyring.item_create_sync(
            self.KEYRING_NAME, GnomeKeyring.ItemType.NETWORK_PASSWORD,
            "Password for '%s' on '%s'" % (username, service),
            attrs, password, True)[0]
        if result == GnomeKeyring.Result.CANCELLED:
            # The user pressed "Cancel" when prompted to unlock their keyring.
            raise PasswordSetError("Cancelled by user")

    def delete_password(self, service, username):
        """Delete the password for the username of the service.
        """
        attrs = GnomeKeyring.Attribute.list_new()
        GnomeKeyring.Attribute.list_append_string(attrs, 'user', username)
        GnomeKeyring.Attribute.list_append_string(attrs, 'domain', service)
        result, items = GnomeKeyring.find_items_sync(
            GnomeKeyring.ItemType.NETWORK_PASSWORD, attrs)
        if result == GnomeKeyring.Result.NO_MATCH:
            raise PasswordDeleteError("Password not found")
        for current in items:
            result = GnomeKeyring.item_delete_sync(current.keyring,
                                                   current.item_id)
            if result == GnomeKeyring.Result.CANCELLED:
                raise PasswordDeleteError("Cancelled by user")

    def _safe_string(self, source, encoding='utf-8'):
        """Convert unicode to string as gnomekeyring barfs on unicode"""
        if not isinstance(source, str):
            return source.encode(encoding)
        return str(source)
