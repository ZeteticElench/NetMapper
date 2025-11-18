"""PyATS-based MAC address table collector.

This module collects MAC address forwarding tables using PyATS CLI parsing
as an alternative to SNMP Bridge MIB queries.
"""

import logging
from typing import Dict, List, Optional, Set
from pyats.topology import Device as PyATSDevice
from pyats.topology import Testbed
from genie.libs.parser.utils.common import ParserNotFound

from .models import DeviceCredentials
from .snmp_collector import MacEntry, BridgeMibData


logger = logging.getLogger(__name__)


class PyATSMacCollector:
    """Collect MAC address tables using PyATS."""

    def __init__(self, timeout: int = 30, command_timeout: int = 30) -> None:
        """
        Initialize PyATS MAC collector.

        Args:
            timeout: Connection timeout in seconds.
            command_timeout: Command execution timeout in seconds.
        """
        self.timeout = timeout
        self.command_timeout = command_timeout

    def _create_device(self, creds: DeviceCredentials) -> PyATSDevice:
        """
        Create a PyATS device from credentials.

        Args:
            creds: Device credentials.

        Returns:
            PyATS Device object.
        """
        testbed = Testbed('dynamic_testbed')
        device = PyATSDevice(
            name=creds.hostname,
            os=creds.os,
            credentials={
                'default': {
                    'username': creds.username,
                    'password': creds.password,
                },
                'enable': {
                    'password': creds.enable_password or creds.password,
                }
            },
            connections={
                'cli': {
                    'protocol': creds.protocol,
                    'ip': creds.ip,
                    'port': creds.port,
                }
            },
            testbed=testbed,
        )
        return device

    def collect_mac_table(self, creds: DeviceCredentials) -> Optional[BridgeMibData]:
        """
        Collect MAC address table from device using PyATS.

        Args:
            creds: Device credentials.

        Returns:
            BridgeMibData if successful, None otherwise.
        """
        logger.info(f"Collecting MAC table from {creds.hostname} ({creds.ip}) via PyATS")

        device = self._create_device(creds)

        try:
            device.connect(
                learn_hostname=True,
                init_exec_commands=[],
                init_config_commands=[],
                log_stdout=False,
                connection_timeout=self.timeout,
            )

            # Get device information
            sys_name = creds.hostname
            sys_descr = self._get_device_description(device)

            # Collect MAC address table
            mac_table = self._parse_mac_table(device)

            if not mac_table:
                logger.warning(f"No MAC entries found for {creds.hostname}")
                return None

            # Build port mapping (interface name -> synthetic port number)
            port_mapping = self._build_port_mapping(mac_table)

            # Build reachable MACs per port
            reachable_macs = self._build_reachable_macs(mac_table)

            bridge_data = BridgeMibData(
                device_ip=creds.ip,
                sys_name=sys_name,
                sys_descr=sys_descr,
                port_mapping=port_mapping,
                mac_table=mac_table,
                reachable_macs=reachable_macs,
            )

            logger.info(
                f"Collected {len(mac_table)} MAC entries from {creds.hostname} "
                f"via PyATS"
            )

            return bridge_data

        except Exception as e:
            logger.error(f"Failed to collect MAC table from {creds.hostname}: {e}")
            return None

        finally:
            if device.is_connected():
                device.disconnect()

    def _get_device_description(self, device: PyATSDevice) -> str:
        """Get device description."""
        try:
            output = device.parse('show version')
            version_info = output.get('version', {})
            platform = version_info.get('platform', 'unknown')
            version = version_info.get('version', 'unknown')
            return f"{platform} running {version}"
        except Exception:
            return "unknown"

    def _parse_mac_table(self, device: PyATSDevice) -> List[MacEntry]:
        """
        Parse MAC address table from device.

        Args:
            device: PyATS device.

        Returns:
            List of MAC entries.
        """
        mac_table: List[MacEntry] = []

        try:
            # Try "show mac address-table" (most Cisco platforms)
            output = device.parse('show mac address-table')
            mac_table = self._extract_mac_entries(output)

        except ParserNotFound:
            try:
                # Try alternative command
                output = device.parse('show mac-address-table')
                mac_table = self._extract_mac_entries(output)
            except Exception as e:
                logger.warning(f"Failed to parse MAC table: {e}")

        except Exception as e:
            logger.warning(f"Failed to parse MAC table: {e}")

        return mac_table

    def _extract_mac_entries(self, output: Dict) -> List[MacEntry]:
        """
        Extract MAC entries from parsed output.

        Args:
            output: Parsed command output.

        Returns:
            List of MAC entries.
        """
        mac_table: List[MacEntry] = []

        # Handle different output formats
        if 'mac_table' in output:
            # Cisco IOS/IOS-XE format
            mac_table_data = output['mac_table']

            if 'vlans' in mac_table_data:
                # Format: mac_table -> vlans -> vlan_id -> mac_addresses
                for vlan_id, vlan_data in mac_table_data['vlans'].items():
                    mac_addresses = vlan_data.get('mac_addresses', {})

                    for mac_addr, mac_info in mac_addresses.items():
                        interfaces = mac_info.get('interfaces', {})

                        for interface, intf_info in interfaces.items():
                            entry_type = intf_info.get('entry_type', 'dynamic')

                            # Map entry type to Bridge MIB status
                            status = 3  # learned
                            if entry_type in ['static', 'system']:
                                status = 4  # self

                            # Use a synthetic port number based on interface name
                            port_number = self._interface_to_port_number(interface)

                            mac_table.append(
                                MacEntry(
                                    mac_address=mac_addr,
                                    port_number=port_number,
                                    status=status,
                                )
                            )

        return mac_table

    @staticmethod
    def _interface_to_port_number(interface: str) -> int:
        """
        Convert interface name to synthetic port number.

        Args:
            interface: Interface name (e.g., "GigabitEthernet1/0/1").

        Returns:
            Synthetic port number.
        """
        # Extract numeric part from interface name
        # E.g., "GigabitEthernet1/0/1" -> "101", "Eth2/3" -> "23"
        import re
        numbers = re.findall(r'\d+', interface)

        if numbers:
            # Concatenate all numbers to create unique port number
            port_str = ''.join(numbers)
            try:
                return int(port_str)
            except ValueError:
                pass

        # Fallback: hash interface name
        return abs(hash(interface)) % 10000

    def _build_port_mapping(self, mac_table: List[MacEntry]) -> Dict[int, int]:
        """
        Build port mapping (port_number -> if_index).

        Since PyATS uses interface names, we create synthetic port numbers.

        Args:
            mac_table: List of MAC entries.

        Returns:
            Dictionary mapping port_number -> if_index (same as port_number).
        """
        port_mapping: Dict[int, int] = {}

        for entry in mac_table:
            # For PyATS, we use the same number for both port and ifIndex
            port_mapping[entry.port_number] = entry.port_number

        return port_mapping

    @staticmethod
    def _build_reachable_macs(mac_table: List[MacEntry]) -> Dict[int, Set[str]]:
        """
        Build a mapping of port -> set of reachable MAC addresses.

        Args:
            mac_table: List of MAC table entries.

        Returns:
            Dictionary mapping port_number -> set of MAC addresses.
        """
        reachable: Dict[int, Set[str]] = {}

        for entry in mac_table:
            if entry.port_number not in reachable:
                reachable[entry.port_number] = set()
            reachable[entry.port_number].add(entry.mac_address)

        return reachable

    def collect_multiple_devices(
        self,
        credentials_list: List[DeviceCredentials],
    ) -> Dict[str, BridgeMibData]:
        """
        Collect MAC tables from multiple devices.

        Args:
            credentials_list: List of device credentials.

        Returns:
            Dictionary mapping device_ip -> BridgeMibData.
        """
        results: Dict[str, BridgeMibData] = {}

        for creds in credentials_list:
            bridge_data = self.collect_mac_table(creds)
            if bridge_data:
                results[creds.ip] = bridge_data

        return results
