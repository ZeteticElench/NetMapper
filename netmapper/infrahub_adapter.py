"""
Infrahub adapter for NetMapper.

Converts NetMapper discovery results to Infrahub-compatible data models,
enabling seamless integration with Infrahub's standardized infrastructure schema.
"""

import logging
from typing import List, Dict, Optional, Set
from datetime import datetime

from neo4j import GraphDatabase, Driver

from .models import (
    NetworkDevice,
    Interface,
    VLANInfo,
    PortStatus,
)
from .infrahub_models import (
    InfrahubDevice,
    InfrahubInterface,
    InfrahubVLAN,
    InfrahubIPAddress,
    InfrahubSite,
    InfrahubTopology,
    InfraDeviceStatus,
    InfraDeviceRole,
    InfraInterfaceStatus,
    InfraInterfaceRole,
    VLANStatus,
    VLANRole,
)

logger = logging.getLogger(__name__)


class InfrahubAdapter:
    """
    Adapter to convert NetMapper data to Infrahub models.

    Reads NetMapper discovery data from Neo4j and converts to Infrahub-compatible
    models for export or synchronization with Infrahub instances.
    """

    # Platform to device type mapping
    PLATFORM_TO_TYPE = {
        "cisco_ios": "router",
        "cisco_iosxe": "router",
        "cisco_nxos": "switch",
        "cisco_iosxr": "router",
        "cisco_asa": "firewall",
        "juniper_junos": "router",
        "arista_eos": "switch",
    }

    # Device role inference from hostname patterns
    ROLE_PATTERNS = {
        "core": InfraDeviceRole.CORE,
        "edge": InfraDeviceRole.EDGE,
        "spine": InfraDeviceRole.SPINE,
        "leaf": InfraDeviceRole.LEAF,
        "fw": InfraDeviceRole.FIREWALL,
        "firewall": InfraDeviceRole.FIREWALL,
    }

    # Interface role inference from name patterns
    INTERFACE_ROLE_PATTERNS = {
        "loopback": InfraInterfaceRole.LOOPBACK,
        "lo": InfraInterfaceRole.LOOPBACK,
        "management": InfraInterfaceRole.MANAGEMENT,
        "mgmt": InfraInterfaceRole.MANAGEMENT,
        "uplink": InfraInterfaceRole.UPLINK,
    }

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        """
        Initialize Infrahub adapter.

        Args:
            neo4j_uri: Neo4j connection URI.
            neo4j_username: Neo4j username.
            neo4j_password: Neo4j password.
        """
        self.driver: Driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_username, neo4j_password)
        )

    def close(self):
        """Close Neo4j connection."""
        self.driver.close()

    def convert_topology(self) -> InfrahubTopology:
        """
        Convert complete NetMapper topology to Infrahub models.

        Returns:
            InfrahubTopology containing all converted infrastructure data.
        """
        logger.info("Converting NetMapper topology to Infrahub models...")

        topology = InfrahubTopology(
            discovery_timestamp=datetime.utcnow().isoformat()
        )

        # Convert devices
        topology.devices = self._convert_devices()

        # Convert interfaces
        topology.interfaces = self._convert_interfaces()

        # Convert VLANs
        topology.vlans = self._convert_vlans()

        # Convert IP addresses
        topology.ip_addresses = self._convert_ip_addresses()

        # Infer sites from device locations
        topology.sites = self._infer_sites(topology.devices)

        logger.info(
            f"Conversion complete: {len(topology.devices)} devices, "
            f"{len(topology.interfaces)} interfaces, "
            f"{len(topology.vlans)} VLANs, "
            f"{len(topology.ip_addresses)} IP addresses"
        )

        return topology

    def _convert_devices(self) -> List[InfrahubDevice]:
        """Convert NetworkDevice nodes to InfrahubDevice models."""
        query = """
        MATCH (d:NetworkDevice)
        RETURN
            d.hostname as hostname,
            d.mgmt_ip as mgmt_ip,
            d.platform as platform,
            d.model as model,
            d.serial_number as serial_number,
            d.software_version as software_version
        """

        with self.driver.session() as session:
            result = session.run(query)
            devices = []

            for record in result:
                hostname = record["hostname"]
                platform = record.get("platform", "unknown")
                mgmt_ip = record.get("mgmt_ip")

                # Infer device type from platform
                device_type = self._infer_device_type(platform)

                # Infer device role from hostname
                role = self._infer_device_role(hostname)

                device = InfrahubDevice(
                    name=hostname,
                    type=device_type,
                    status=InfraDeviceStatus.ACTIVE,
                    role=role,
                    platform=platform,
                    model=record.get("model"),
                    serial_number=record.get("serial_number"),
                    software_version=record.get("software_version"),
                    primary_address=mgmt_ip,
                )

                devices.append(device)

            logger.info(f"Converted {len(devices)} devices to Infrahub models")
            return devices

    def _convert_interfaces(self) -> List[InfrahubInterface]:
        """Convert Interface nodes to InfrahubInterface models."""
        query = """
        MATCH (d:NetworkDevice)-[:HAS]->(i:Interface)
        RETURN
            d.hostname as device_hostname,
            i.name as interface_name,
            i.description as description,
            i.ip_address as ip_address,
            i.status as status
        """

        with self.driver.session() as session:
            result = session.run(query)
            interfaces = []

            for record in result:
                device_hostname = record["device_hostname"]
                interface_name = record["interface_name"]
                ip_address = record.get("ip_address")

                # Infer status
                status_str = record.get("status", "up")
                status = (
                    InfraInterfaceStatus.ACTIVE
                    if status_str == "up"
                    else InfraInterfaceStatus.DRAINED
                )

                # Infer interface role
                role = self._infer_interface_role(interface_name)

                # Build IP addresses list
                ip_addresses = [ip_address] if ip_address else []

                interface = InfrahubInterface(
                    name=interface_name,
                    description=record.get("description"),
                    enabled=(status == InfraInterfaceStatus.ACTIVE),
                    status=status,
                    role=role,
                    device=device_hostname,
                    ip_addresses=ip_addresses,
                )

                interfaces.append(interface)

            logger.info(f"Converted {len(interfaces)} interfaces to Infrahub models")
            return interfaces

    def _convert_vlans(self) -> List[InfrahubVLAN]:
        """Convert VLAN nodes to InfrahubVLAN models."""
        query = """
        MATCH (d:NetworkDevice)-[:HAS_VLAN]->(v:VLAN)
        RETURN DISTINCT
            v.vlan_id as vlan_id,
            v.name as name,
            v.status as status
        """

        with self.driver.session() as session:
            result = session.run(query)
            vlans = []
            seen_vlans: Set[int] = set()

            for record in result:
                vlan_id = record["vlan_id"]

                # Skip duplicates
                if vlan_id in seen_vlans:
                    continue
                seen_vlans.add(vlan_id)

                vlan_name = record.get("name", f"VLAN{vlan_id}")
                status_str = record.get("status", "active")

                # Map status
                status = (
                    VLANStatus.ACTIVE
                    if status_str == "active"
                    else VLANStatus.PROVISIONING
                )

                vlan = InfrahubVLAN(
                    name=vlan_name,
                    vlan_id=vlan_id,
                    status=status,
                    role=VLANRole.SERVER,  # Default role
                )

                vlans.append(vlan)

            logger.info(f"Converted {len(vlans)} VLANs to Infrahub models")
            return vlans

    def _convert_ip_addresses(self) -> List[InfrahubIPAddress]:
        """Convert IP addresses to InfrahubIPAddress models."""
        query = """
        MATCH (i:Interface)
        WHERE i.ip_address IS NOT NULL
        RETURN
            i.ip_address as ip_address,
            i.subnet_mask as subnet_mask,
            i.device_hostname + ':' + i.name as interface_ref
        """

        with self.driver.session() as session:
            result = session.run(query)
            ip_addresses = []

            for record in result:
                ip_address = record.get("ip_address")
                subnet_mask = record.get("subnet_mask", "255.255.255.0")
                interface_ref = record.get("interface_ref")

                if not ip_address:
                    continue

                # Convert subnet mask to CIDR prefix
                prefix_len = self._subnet_mask_to_cidr(subnet_mask)
                address_with_prefix = f"{ip_address}/{prefix_len}"

                ip_addr = InfrahubIPAddress(
                    address=address_with_prefix,
                    interface=interface_ref,
                )

                ip_addresses.append(ip_addr)

            logger.info(f"Converted {len(ip_addresses)} IP addresses to Infrahub models")
            return ip_addresses

    def _infer_sites(self, devices: List[InfrahubDevice]) -> List[InfrahubSite]:
        """
        Infer sites from device locations.

        In future, this could read from CIM CONTAINER relationships or
        custom site attributes.
        """
        # For now, create a default site
        sites = [
            InfrahubSite(
                name="DefaultSite",
                description="Default site for discovered devices",
            )
        ]

        # Update devices to reference the default site
        for device in devices:
            device.site = "DefaultSite"

        return sites

    def _infer_device_type(self, platform: str) -> str:
        """Infer Infrahub device type from NetMapper platform."""
        platform_lower = platform.lower()

        for pattern, device_type in self.PLATFORM_TO_TYPE.items():
            if pattern in platform_lower:
                return device_type

        # Default fallback
        if "switch" in platform_lower:
            return "switch"
        elif "router" in platform_lower:
            return "router"
        elif "firewall" in platform_lower or "asa" in platform_lower:
            return "firewall"
        else:
            return "device"

    def _infer_device_role(self, hostname: str) -> Optional[InfraDeviceRole]:
        """Infer Infrahub device role from hostname patterns."""
        hostname_lower = hostname.lower()

        for pattern, role in self.ROLE_PATTERNS.items():
            if pattern in hostname_lower:
                return role

        return None

    def _infer_interface_role(self, interface_name: str) -> Optional[InfraInterfaceRole]:
        """Infer Infrahub interface role from interface name."""
        interface_lower = interface_name.lower()

        for pattern, role in self.INTERFACE_ROLE_PATTERNS.items():
            if pattern in interface_lower:
                return role

        return None

    @staticmethod
    def _subnet_mask_to_cidr(subnet_mask: str) -> int:
        """Convert subnet mask to CIDR prefix length."""
        try:
            octets = subnet_mask.split(".")
            binary = "".join([bin(int(octet))[2:].zfill(8) for octet in octets])
            return binary.count("1")
        except Exception:
            return 24  # Default /24

    def export_to_yaml(self, topology: InfrahubTopology, output_file: str):
        """
        Export Infrahub topology to YAML file.

        Args:
            topology: InfrahubTopology to export.
            output_file: Output YAML file path.
        """
        import yaml

        data = {
            "metadata": {
                "discovery_timestamp": topology.discovery_timestamp,
                "netmapper_version": topology.netmapper_version,
            },
            "devices": [device.dict() for device in topology.devices],
            "interfaces": [iface.dict() for iface in topology.interfaces],
            "vlans": [vlan.dict() for vlan in topology.vlans],
            "ip_addresses": [ip.dict() for ip in topology.ip_addresses],
            "sites": [site.dict() for site in topology.sites],
        }

        with open(output_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Exported Infrahub topology to {output_file}")

    def export_to_json(self, topology: InfrahubTopology, output_file: str):
        """
        Export Infrahub topology to JSON file.

        Args:
            topology: InfrahubTopology to export.
            output_file: Output JSON file path.
        """
        import json

        data = topology.dict()

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported Infrahub topology to {output_file}")
