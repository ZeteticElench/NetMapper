"""SNMP-based data collector for Bridge MIB (RFC 1493/RFC 4188).

This module implements SNMP queries to collect MAC address forwarding tables
from network switches using the Bridge MIB, as described in RFC 1493.
"""

import logging
from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass
from pysnmp.hlapi import (
    getCmd,
    nextCmd,
    SnmpEngine,
    CommunityData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
)
from pysnmp.proto.rfc1902 import OctetString

logger = logging.getLogger(__name__)


# SNMP OID Constants for Bridge MIB (RFC 1493)
OID_DOT1D_BASE_PORT_TABLE = "1.3.6.1.2.1.17.1.4"  # dot1dBasePortTable
OID_DOT1D_BASE_PORT_IF_INDEX = "1.3.6.1.2.1.17.1.4.1.2"  # dot1dBasePortIfIndex
OID_DOT1D_TP_FDB_TABLE = "1.3.6.1.2.1.17.4.3"  # dot1dTpFdbTable
OID_DOT1D_TP_FDB_ADDRESS = "1.3.6.1.2.1.17.4.3.1.1"  # dot1dTpFdbAddress
OID_DOT1D_TP_FDB_PORT = "1.3.6.1.2.1.17.4.3.1.2"  # dot1dTpFdbPort
OID_DOT1D_TP_FDB_STATUS = "1.3.6.1.2.1.17.4.3.1.3"  # dot1dTpFdbStatus

# System MIB for device identification
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"  # sysName
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"  # sysDescr


@dataclass
class BridgePort:
    """Bridge port information."""
    port_number: int
    if_index: int


@dataclass
class MacEntry:
    """MAC address forwarding table entry."""
    mac_address: str
    port_number: int
    status: int  # 1=other, 2=invalid, 3=learned, 4=self, 5=mgmt


@dataclass
class BridgeMibData:
    """Complete Bridge MIB data for a switch."""
    device_ip: str
    sys_name: str
    sys_descr: str
    port_mapping: Dict[int, int]  # bridge_port -> if_index
    mac_table: List[MacEntry]
    reachable_macs: Dict[int, Set[str]]  # port_number -> set of MACs


class SNMPBridgeCollector:
    """Collect Bridge MIB data via SNMP."""

    def __init__(
        self,
        community: str = "public",
        timeout: int = 5,
        retries: int = 3,
    ) -> None:
        """
        Initialize SNMP collector.

        Args:
            community: SNMP community string.
            timeout: SNMP timeout in seconds.
            retries: Number of retries for failed queries.
        """
        self.community = community
        self.timeout = timeout
        self.retries = retries
        self.engine = SnmpEngine()

    def collect_bridge_mib(
        self,
        device_ip: str,
        vlan_ids: Optional[List[int]] = None,
    ) -> Optional[BridgeMibData]:
        """
        Collect Bridge MIB data from a device.

        Args:
            device_ip: IP address of the device.
            vlan_ids: Optional list of VLAN IDs to query (Cisco specific).

        Returns:
            BridgeMibData if successful, None otherwise.
        """
        logger.info(f"Collecting Bridge MIB data from {device_ip}")

        try:
            # Get system information
            sys_name = self._get_sys_name(device_ip)
            sys_descr = self._get_sys_descr(device_ip)

            logger.debug(f"Device {device_ip}: {sys_name}")

            # Get port mapping (bridge port to ifIndex)
            port_mapping = self._get_port_mapping(device_ip)

            if not port_mapping:
                logger.warning(f"No port mapping found for {device_ip}")
                return None

            # Get MAC address forwarding table
            mac_table: List[MacEntry] = []

            if vlan_ids:
                # Cisco-specific: query each VLAN separately
                for vlan_id in vlan_ids:
                    vlan_macs = self._get_mac_table(device_ip, vlan_id)
                    mac_table.extend(vlan_macs)
            else:
                # Standard query
                mac_table = self._get_mac_table(device_ip)

            if not mac_table:
                logger.warning(f"No MAC entries found for {device_ip}")

            # Build reachable MACs per port
            reachable_macs = self._build_reachable_macs(mac_table)

            bridge_data = BridgeMibData(
                device_ip=device_ip,
                sys_name=sys_name,
                sys_descr=sys_descr,
                port_mapping=port_mapping,
                mac_table=mac_table,
                reachable_macs=reachable_macs,
            )

            logger.info(
                f"Collected {len(mac_table)} MAC entries from {device_ip} "
                f"across {len(port_mapping)} ports"
            )

            return bridge_data

        except Exception as e:
            logger.error(f"Failed to collect Bridge MIB from {device_ip}: {e}")
            return None

    def _get_sys_name(self, device_ip: str) -> str:
        """Get system name via SNMP."""
        try:
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    self.engine,
                    CommunityData(self.community),
                    UdpTransportTarget((device_ip, 161), timeout=self.timeout, retries=self.retries),
                    ContextData(),
                    ObjectType(ObjectIdentity(OID_SYS_NAME)),
                )
            )

            if error_indication or error_status:
                return "unknown"

            return str(var_binds[0][1])

        except Exception as e:
            logger.debug(f"Failed to get sysName from {device_ip}: {e}")
            return "unknown"

    def _get_sys_descr(self, device_ip: str) -> str:
        """Get system description via SNMP."""
        try:
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    self.engine,
                    CommunityData(self.community),
                    UdpTransportTarget((device_ip, 161), timeout=self.timeout, retries=self.retries),
                    ContextData(),
                    ObjectType(ObjectIdentity(OID_SYS_DESCR)),
                )
            )

            if error_indication or error_status:
                return "unknown"

            return str(var_binds[0][1])

        except Exception as e:
            logger.debug(f"Failed to get sysDescr from {device_ip}: {e}")
            return "unknown"

    def _get_port_mapping(self, device_ip: str) -> Dict[int, int]:
        """
        Get bridge port to ifIndex mapping.

        Returns:
            Dictionary mapping bridge_port -> if_index
        """
        port_mapping: Dict[int, int] = {}

        try:
            for error_indication, error_status, error_index, var_binds in nextCmd(
                self.engine,
                CommunityData(self.community),
                UdpTransportTarget((device_ip, 161), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(OID_DOT1D_BASE_PORT_IF_INDEX)),
                lexicographicMode=False,
            ):
                if error_indication or error_status:
                    break

                for var_bind in var_binds:
                    oid, value = var_bind
                    # Extract bridge port number from OID
                    oid_str = str(oid)
                    bridge_port = int(oid_str.split('.')[-1])
                    if_index = int(value)
                    port_mapping[bridge_port] = if_index

        except Exception as e:
            logger.error(f"Error getting port mapping from {device_ip}: {e}")

        return port_mapping

    def _get_mac_table(
        self,
        device_ip: str,
        vlan_id: Optional[int] = None,
    ) -> List[MacEntry]:
        """
        Get MAC address forwarding table.

        Args:
            device_ip: Device IP address.
            vlan_id: Optional VLAN ID for Cisco devices (community@vlan).

        Returns:
            List of MAC table entries.
        """
        mac_table: List[MacEntry] = []

        # For Cisco devices with VLANs, append @vlan to community
        community = self.community
        if vlan_id is not None:
            community = f"{self.community}@{vlan_id}"

        try:
            for error_indication, error_status, error_index, var_binds in nextCmd(
                self.engine,
                CommunityData(community),
                UdpTransportTarget((device_ip, 161), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(OID_DOT1D_TP_FDB_PORT)),
                lexicographicMode=False,
            ):
                if error_indication or error_status:
                    break

                for var_bind in var_binds:
                    oid, value = var_bind
                    # Extract MAC address from OID
                    oid_str = str(oid)
                    oid_parts = oid_str.split('.')

                    # Last 6 octets are the MAC address
                    if len(oid_parts) >= 6:
                        mac_octets = oid_parts[-6:]
                        mac_address = ':'.join(f"{int(octet):02x}" for octet in mac_octets)
                        port_number = int(value)

                        # Get status for this MAC
                        status = 3  # Default to "learned"

                        mac_table.append(
                            MacEntry(
                                mac_address=mac_address,
                                port_number=port_number,
                                status=status,
                            )
                        )

        except Exception as e:
            logger.error(f"Error getting MAC table from {device_ip}: {e}")

        return mac_table

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
        device_ips: List[str],
        vlan_ids: Optional[List[int]] = None,
    ) -> Dict[str, BridgeMibData]:
        """
        Collect Bridge MIB data from multiple devices.

        Args:
            device_ips: List of device IP addresses.
            vlan_ids: Optional list of VLAN IDs (for Cisco devices).

        Returns:
            Dictionary mapping device_ip -> BridgeMibData.
        """
        results: Dict[str, BridgeMibData] = {}

        for device_ip in device_ips:
            bridge_data = self.collect_bridge_mib(device_ip, vlan_ids)
            if bridge_data:
                results[device_ip] = bridge_data

        return results
