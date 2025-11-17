"""Utility functions for NetMapper."""

import random
import string
from typing import Set


class CableIDGenerator:
    """Generate unique 4-character alphanumeric cable IDs."""

    def __init__(self) -> None:
        """Initialize the cable ID generator."""
        self._used_ids: Set[str] = set()
        self._chars = string.ascii_uppercase + string.digits

    def generate(self) -> str:
        """
        Generate a unique 4-character alphanumeric cable ID.

        Returns:
            A unique 4-character alphanumeric string.
        """
        while True:
            cable_id = ''.join(random.choices(self._chars, k=4))
            if cable_id not in self._used_ids:
                self._used_ids.add(cable_id)
                return cable_id

    def mark_used(self, cable_id: str) -> None:
        """
        Mark a cable ID as used (e.g., from existing database entries).

        Args:
            cable_id: The cable ID to mark as used.
        """
        self._used_ids.add(cable_id)


def normalize_hostname(hostname: str) -> str:
    """
    Normalize hostname by removing domain suffix and converting to lowercase.

    Args:
        hostname: The hostname to normalize.

    Returns:
        Normalized hostname.
    """
    # Remove FQDN suffix
    if '.' in hostname:
        hostname = hostname.split('.')[0]
    return hostname.lower()


def normalize_interface_name(interface: str) -> str:
    """
    Normalize interface name to a consistent format.

    Args:
        interface: The interface name to normalize.

    Returns:
        Normalized interface name.
    """
    # Common abbreviations
    replacements = {
        'Gi': 'GigabitEthernet',
        'Fa': 'FastEthernet',
        'Te': 'TenGigabitEthernet',
        'Eth': 'Ethernet',
        'Po': 'Port-channel',
        'Vl': 'Vlan',
    }

    for abbr, full in replacements.items():
        if interface.startswith(abbr):
            return interface.replace(abbr, full, 1)

    return interface
