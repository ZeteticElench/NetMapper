"""Hybrid network discovery combining PyATS and Bejerano SNMP topology discovery.

This module integrates:
1. PyATS-based CDP/LLDP/STP discovery (high-level)
2. Bejerano topology discovery using MAC tables (via SNMP or PyATS)
"""

import logging
from typing import Dict, List, Optional, Set

from .models import DiscoveryConfig, DiscoveryResult, DeviceCredentials
from .discovery import NetworkDiscovery
from .snmp_collector import SNMPBridgeCollector, BridgeMibData
from .pyats_mac_collector import PyATSMacCollector
from .bejerano_algorithm import BejeranoTopologyDiscovery, PhysicalTopology
from .neo4j_manager import Neo4jManager


logger = logging.getLogger(__name__)


class HybridNetworkDiscovery:
    """
    Hybrid discovery combining PyATS and Bejerano algorithms.

    This provides a complete topology view:
    - PyATS: CDP/LLDP neighbors, STP, VLANs, interfaces
    - Bejerano: Layer 2 physical topology from MAC tables (SNMP or PyATS)
    """

    def __init__(
        self,
        config: DiscoveryConfig,
        snmp_community: str = "public",
        enable_bejerano: bool = True,
        mac_collection_method: str = "snmp",  # "snmp" or "pyats"
    ) -> None:
        """
        Initialize hybrid discovery.

        Args:
            config: Discovery configuration.
            snmp_community: SNMP community string for Bejerano algorithm.
            enable_bejerano: Enable Bejerano topology discovery.
            mac_collection_method: Method to collect MAC tables ("snmp" or "pyats").
        """
        self.config = config
        self.snmp_community = snmp_community
        self.enable_bejerano = enable_bejerano
        self.mac_collection_method = mac_collection_method

        # Initialize PyATS-based discovery
        self.pyats_discovery = NetworkDiscovery(config)

        # Initialize MAC table collectors
        self.snmp_collector = SNMPBridgeCollector(community=snmp_community)
        self.pyats_mac_collector = PyATSMacCollector(
            timeout=config.connection_timeout,
            command_timeout=config.command_timeout,
        )
        self.bejerano = BejeranoTopologyDiscovery()

        # Results
        self.discovered_devices: Set[str] = set()
        self.bejerano_topology: Optional[PhysicalTopology] = None

    def run(self) -> None:
        """
        Run hybrid discovery process.

        Steps:
        1. Run PyATS-based discovery (CDP/LLDP/STP/VLAN)
        2. Collect device IPs from PyATS results
        3. Run Bejerano SNMP-based topology discovery
        4. Store combined results in Neo4j
        """
        logger.info("Starting hybrid network discovery")

        # Phase 1: PyATS Discovery
        logger.info("Phase 1: Running PyATS-based discovery (CDP/LLDP/STP)")
        try:
            self.pyats_discovery.run()
            self.discovered_devices = self.pyats_discovery.visited
            logger.info(f"PyATS discovery completed: {len(self.discovered_devices)} devices")
        except Exception as e:
            logger.error(f"PyATS discovery failed: {e}")
            return

        # Phase 2: Bejerano SNMP Discovery
        if self.enable_bejerano and self.discovered_devices:
            logger.info("Phase 2: Running Bejerano SNMP-based topology discovery")
            try:
                self._run_bejerano_discovery()
            except Exception as e:
                logger.error(f"Bejerano discovery failed: {e}")

        # Print summary
        self._print_summary()

    def _run_bejerano_discovery(self) -> None:
        """
        Run Bejerano algorithm on discovered devices.

        Collects MAC address tables via SNMP or PyATS and infers physical topology.
        """
        logger.info(f"MAC collection method: {self.mac_collection_method}")

        # Collect MAC address tables
        bridge_data_map: Dict[str, BridgeMibData] = {}

        if self.mac_collection_method == "snmp":
            bridge_data_map = self._collect_mac_via_snmp()
        elif self.mac_collection_method == "pyats":
            bridge_data_map = self._collect_mac_via_pyats()
        else:
            logger.error(f"Invalid MAC collection method: {self.mac_collection_method}")
            return

        if not bridge_data_map:
            logger.warning("No MAC table data collected, skipping Bejerano algorithm")
            return

        # Run Bejerano topology discovery
        logger.info(f"Running Bejerano algorithm on {len(bridge_data_map)} devices")
        self.bejerano_topology = self.bejerano.discover_topology(bridge_data_map)

        # Store results in Neo4j
        logger.info("Storing Bejerano topology in Neo4j")
        self._store_bejerano_topology()

        # Print topology summary
        if self.bejerano_topology:
            summary = self.bejerano.export_topology_summary(self.bejerano_topology)
            logger.info(f"\n{summary}")

    def _collect_mac_via_snmp(self) -> Dict[str, BridgeMibData]:
        """
        Collect MAC address tables via SNMP Bridge MIB.

        Returns:
            Dictionary mapping device_ip -> BridgeMibData.
        """
        # Get device IPs from discovered devices
        device_ips: List[str] = []

        # Extract IPs from Neo4j
        neo4j = self.pyats_discovery.neo4j
        with neo4j.driver.session() as session:
            result = session.run(
                "MATCH (d:NetworkDevice) WHERE d.hostname IN $hostnames "
                "RETURN d.hostname AS hostname, d.mgmt_ip AS ip",
                hostnames=list(self.discovered_devices),
            )

            for record in result:
                ip = record["ip"]
                if ip and ip != "unknown":
                    device_ips.append(ip)

        if not device_ips:
            logger.warning("No device IPs available for SNMP collection")
            return {}

        logger.info(f"Collecting Bridge MIB data from {len(device_ips)} devices via SNMP")

        # Collect VLAN IDs (for Cisco devices)
        vlan_ids = self._get_vlan_ids()

        # Collect Bridge MIB data
        bridge_data_map: Dict[str, BridgeMibData] = {}

        for device_ip in device_ips:
            try:
                bridge_data = self.snmp_collector.collect_bridge_mib(
                    device_ip,
                    vlan_ids=vlan_ids if vlan_ids else None,
                )

                if bridge_data:
                    bridge_data_map[device_ip] = bridge_data
                    logger.debug(f"Collected Bridge MIB from {device_ip} via SNMP")
                else:
                    logger.warning(f"No Bridge MIB data from {device_ip}")

            except Exception as e:
                logger.warning(f"Failed to collect Bridge MIB from {device_ip}: {e}")

        return bridge_data_map

    def _collect_mac_via_pyats(self) -> Dict[str, BridgeMibData]:
        """
        Collect MAC address tables via PyATS CLI parsing.

        Returns:
            Dictionary mapping device_ip -> BridgeMibData.
        """
        # Get device credentials from cache
        credentials_list: List[DeviceCredentials] = []

        for hostname in self.discovered_devices:
            if hostname in self.pyats_discovery.credential_cache:
                credentials_list.append(self.pyats_discovery.credential_cache[hostname])

        if not credentials_list:
            logger.warning("No device credentials available for PyATS MAC collection")
            return {}

        logger.info(f"Collecting MAC tables from {len(credentials_list)} devices via PyATS")

        # Collect MAC tables via PyATS
        bridge_data_map = self.pyats_mac_collector.collect_multiple_devices(credentials_list)

        logger.info(f"Collected MAC tables from {len(bridge_data_map)} devices via PyATS")

        return bridge_data_map

    def _get_vlan_ids(self) -> List[int]:
        """
        Get list of VLAN IDs from discovered devices.

        Returns:
            List of unique VLAN IDs.
        """
        vlan_ids: Set[int] = set()
        neo4j = self.pyats_discovery.neo4j

        with neo4j.driver.session() as session:
            result = session.run("MATCH (v:VLAN) RETURN DISTINCT v.vlan_id AS vlan_id")

            for record in result:
                vlan_id = record["vlan_id"]
                if vlan_id:
                    vlan_ids.add(vlan_id)

        return sorted(vlan_ids)

    def _store_bejerano_topology(self) -> None:
        """Store Bejerano topology results in Neo4j."""
        if not self.bejerano_topology:
            return

        neo4j = self.pyats_discovery.neo4j

        with neo4j.driver.session() as session:
            # Store physical links discovered by Bejerano
            for link in self.bejerano_topology.links:
                # Map device IPs to hostnames
                hostname_a = self._ip_to_hostname(link.device_a)
                hostname_b = self._ip_to_hostname(link.device_b)

                if not hostname_a or not hostname_b:
                    continue

                # Create SNMP_PHYSICAL_LINK relationship
                query = """
                MATCH (d1:NetworkDevice {hostname: $hostname_a})
                MATCH (d2:NetworkDevice {hostname: $hostname_b})
                MERGE (d1)-[r:SNMP_PHYSICAL_LINK]->(d2)
                SET r.port_a = $port_a,
                    r.port_b = $port_b,
                    r.link_type = $link_type,
                    r.discovery_method = 'bejerano'
                """

                session.run(
                    query,
                    hostname_a=hostname_a,
                    port_a=link.port_a,
                    hostname_b=hostname_b,
                    port_b=link.port_b,
                    link_type=link.link_type,
                )

            # Mark uncooperative elements
            for uncooperative_id in self.bejerano_topology.uncooperative_devices:
                query = """
                CREATE (u:UncooperativeElement {
                    element_id: $element_id,
                    discovered_by: 'bejerano',
                    element_type: 'hub_or_unmanaged_switch'
                })
                """
                session.run(query, element_id=uncooperative_id)

        logger.info(
            f"Stored {len(self.bejerano_topology.links)} Bejerano physical links "
            f"and {len(self.bejerano_topology.uncooperative_devices)} uncooperative elements"
        )

    def _ip_to_hostname(self, ip: str) -> Optional[str]:
        """
        Map device IP to hostname using Neo4j.

        Args:
            ip: Device IP address.

        Returns:
            Hostname or None if not found.
        """
        neo4j = self.pyats_discovery.neo4j

        with neo4j.driver.session() as session:
            result = session.run(
                "MATCH (d:NetworkDevice {mgmt_ip: $ip}) RETURN d.hostname AS hostname LIMIT 1",
                ip=ip,
            )

            record = result.single()
            return record["hostname"] if record else None

    def _print_summary(self) -> None:
        """Print discovery summary."""
        logger.info("=" * 60)
        logger.info("Hybrid Discovery Summary")
        logger.info("=" * 60)
        logger.info(f"PyATS devices discovered: {self.pyats_discovery.devices_discovered}")
        logger.info(f"PyATS devices failed: {self.pyats_discovery.devices_failed}")

        if self.bejerano_topology:
            logger.info(
                f"Bejerano physical links: {len(self.bejerano_topology.links)}"
            )
            logger.info(
                f"Bejerano uncooperative elements: "
                f"{len(self.bejerano_topology.uncooperative_devices)}"
            )
        else:
            logger.info("Bejerano discovery: Not performed")

        logger.info("=" * 60)

    def close(self) -> None:
        """Close connections and cleanup."""
        self.pyats_discovery.close()
        logger.info("Hybrid discovery connections closed")
