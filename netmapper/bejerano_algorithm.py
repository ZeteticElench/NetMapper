"""Implementation of the Bejerano et al. 2003 Physical Topology Discovery Algorithm.

Reference: Y. Bejerano, Y. Breitbart, M. Garofalakis, R. Rastogi,
"Physical Topology Discovery for Large Multi-Subnet Networks,"
IEEE INFOCOM 2003, pp. 342-352.

This algorithm discovers Layer 2 physical topology using MAC address forwarding
tables from SNMP Bridge MIB, including detection of uncooperative elements
(hubs, unmanaged switches) that don't respond to SNMP.
"""

import logging
from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .snmp_collector import BridgeMibData


logger = logging.getLogger(__name__)


@dataclass
class TopologyNode:
    """Node in the topology tree."""
    node_id: str  # Device identifier (IP or MAC)
    device_ip: Optional[str] = None
    is_cooperative: bool = True  # False for uncooperative elements (hubs)
    is_junction: bool = False  # Degree >= 3
    degree: int = 0
    parent: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    port_to_child: Dict[str, int] = field(default_factory=dict)  # child_id -> port_num
    reachable_macs: Set[str] = field(default_factory=set)  # MACs reachable via this node


@dataclass
class SkeletonTree:
    """Skeleton tree structure for subnet topology."""
    root_id: str
    nodes: Dict[str, TopologyNode]  # node_id -> TopologyNode
    anchor_nodes: Set[str]  # Junction nodes that connect to other skeleton trees


@dataclass
class PhysicalLink:
    """Physical link between two devices."""
    device_a: str
    port_a: int
    device_b: str
    port_b: int
    link_type: str = "switch-switch"  # or "switch-hub", "hub-switch"


@dataclass
class PhysicalTopology:
    """Complete physical topology result."""
    nodes: Dict[str, TopologyNode]
    links: List[PhysicalLink]
    cooperative_devices: Set[str]  # Devices that respond to SNMP
    uncooperative_devices: Set[str]  # Inferred hubs/unmanaged switches


class BejeranoTopologyDiscovery:
    """Bejerano algorithm for physical topology discovery."""

    def __init__(self) -> None:
        """Initialize the topology discovery algorithm."""
        self.bridge_data_map: Dict[str, BridgeMibData] = {}
        self.switch_macs: Dict[str, str] = {}  # device_ip -> MAC address
        self.mac_to_device: Dict[str, str] = {}  # MAC -> device_ip

    def discover_topology(
        self,
        bridge_data_map: Dict[str, BridgeMibData],
    ) -> PhysicalTopology:
        """
        Discover physical topology using Bejerano algorithm.

        Args:
            bridge_data_map: Dictionary mapping device_ip -> BridgeMibData.

        Returns:
            PhysicalTopology containing discovered topology.
        """
        logger.info(f"Starting Bejerano topology discovery for {len(bridge_data_map)} devices")

        self.bridge_data_map = bridge_data_map

        # Step 1: Extract switch MAC addresses from their own MAC tables
        self._extract_switch_macs()

        # Step 2: Build preliminary topology using AFT data
        connecting_trees = self._build_connecting_trees()

        # Step 3: Identify switch-to-switch connections
        links = self._identify_switch_connections()

        # Step 4: Detect uncooperative elements
        uncooperative = self._detect_uncooperative_elements(links)

        # Step 5: Build final topology nodes
        nodes = self._build_topology_nodes(links)

        topology = PhysicalTopology(
            nodes=nodes,
            links=links,
            cooperative_devices=set(bridge_data_map.keys()),
            uncooperative_devices=uncooperative,
        )

        logger.info(
            f"Topology discovery complete: {len(nodes)} nodes, {len(links)} links, "
            f"{len(uncooperative)} uncooperative elements"
        )

        return topology

    def _extract_switch_macs(self) -> None:
        """
        Extract each switch's own MAC address from its MAC table.

        Switches typically have their own MAC in the forwarding table with status=4 (self).
        """
        for device_ip, bridge_data in self.bridge_data_map.items():
            # Look for MAC entries with status=4 (self) or status=5 (mgmt)
            for entry in bridge_data.mac_table:
                if entry.status in [4, 5]:
                    self.switch_macs[device_ip] = entry.mac_address
                    self.mac_to_device[entry.mac_address] = device_ip
                    logger.debug(f"Switch {device_ip} MAC: {entry.mac_address}")
                    break

            # If not found, use first MAC in table as approximation
            if device_ip not in self.switch_macs and bridge_data.mac_table:
                # Use the MAC with the lowest port number
                sorted_entries = sorted(bridge_data.mac_table, key=lambda e: e.port_number)
                if sorted_entries:
                    self.switch_macs[device_ip] = sorted_entries[0].mac_address
                    self.mac_to_device[sorted_entries[0].mac_address] = device_ip

    def _build_connecting_trees(self) -> Dict[str, SkeletonTree]:
        """
        Build connecting trees for each device based on AFT data.

        Returns:
            Dictionary of skeleton trees, one per device.
        """
        trees: Dict[str, SkeletonTree] = {}

        for device_ip, bridge_data in self.bridge_data_map.items():
            root_node = TopologyNode(
                node_id=device_ip,
                device_ip=device_ip,
                is_cooperative=True,
                reachable_macs=set(m.mac_address for m in bridge_data.mac_table),
            )

            nodes = {device_ip: root_node}

            tree = SkeletonTree(
                root_id=device_ip,
                nodes=nodes,
                anchor_nodes=set(),
            )

            trees[device_ip] = tree

        return trees

    def _identify_switch_connections(self) -> List[PhysicalLink]:
        """
        Identify switch-to-switch connections by analyzing MAC tables.

        Core algorithm: If switch A sees switch B's MAC on port P,
        then port P is likely connected to switch B.

        Returns:
            List of identified physical links.
        """
        links: List[PhysicalLink] = []
        connected_pairs: Set[Tuple[str, str]] = set()

        for device_ip, bridge_data in self.bridge_data_map.items():
            # For each port, check if it contains another switch's MAC
            for port_num, mac_set in bridge_data.reachable_macs.items():
                # Find other switches' MACs in this port's MAC set
                for other_device_ip, other_mac in self.switch_macs.items():
                    if other_device_ip == device_ip:
                        continue

                    if other_mac in mac_set:
                        # Found a connection: device_ip's port_num -> other_device_ip
                        # Avoid duplicate links
                        pair = tuple(sorted([device_ip, other_device_ip]))
                        if pair not in connected_pairs:
                            # Find the corresponding port on other device
                            other_port = self._find_reverse_port(
                                other_device_ip, device_ip, port_num
                            )

                            link = PhysicalLink(
                                device_a=device_ip,
                                port_a=port_num,
                                device_b=other_device_ip,
                                port_b=other_port if other_port else 0,
                                link_type="switch-switch",
                            )

                            links.append(link)
                            connected_pairs.add(pair)

                            logger.debug(
                                f"Link: {device_ip}:{port_num} <-> {other_device_ip}:{other_port}"
                            )

        return links

    def _find_reverse_port(
        self,
        device_ip: str,
        neighbor_ip: str,
        neighbor_port: int,
    ) -> Optional[int]:
        """
        Find the port on device_ip that connects to neighbor_ip.

        Args:
            device_ip: Device to search.
            neighbor_ip: Neighbor device.
            neighbor_port: Port on neighbor.

        Returns:
            Port number on device_ip, or None if not found.
        """
        if device_ip not in self.bridge_data_map:
            return None

        bridge_data = self.bridge_data_map[device_ip]
        neighbor_mac = self.switch_macs.get(neighbor_ip)

        if not neighbor_mac:
            return None

        # Find port that sees the neighbor's MAC
        for port_num, mac_set in bridge_data.reachable_macs.items():
            if neighbor_mac in mac_set:
                return port_num

        return None

    def _detect_uncooperative_elements(
        self,
        links: List[PhysicalLink],
    ) -> Set[str]:
        """
        Detect uncooperative elements (hubs, unmanaged switches).

        An uncooperative element is inferred when:
        1. MACs seen on multiple ports suggest a shared medium
        2. Large sets of identical MACs on different switches' ports

        Args:
            links: Discovered switch-to-switch links.

        Returns:
            Set of inferred uncooperative element identifiers.
        """
        uncooperative: Set[str] = set()

        # For each switch, look for ports with suspiciously large MAC sets
        # that might indicate a hub or unmanaged switch
        for device_ip, bridge_data in self.bridge_data_map.items():
            port_mac_counts = {
                port: len(macs)
                for port, macs in bridge_data.reachable_macs.items()
            }

            # If a port sees many more MACs than others, might be a hub
            if port_mac_counts:
                avg_count = sum(port_mac_counts.values()) / len(port_mac_counts)

                for port, count in port_mac_counts.items():
                    # Heuristic: port with >3x average MAC count might have a hub
                    if count > avg_count * 3 and count > 10:
                        # Check if this port connects to a known switch
                        is_known_switch = any(
                            (link.device_a == device_ip and link.port_a == port)
                            or (link.device_b == device_ip and link.port_b == port)
                            for link in links
                        )

                        if not is_known_switch:
                            hub_id = f"hub_{device_ip}_{port}"
                            uncooperative.add(hub_id)
                            logger.info(
                                f"Detected potential uncooperative element: {hub_id} "
                                f"({count} MACs on {device_ip}:{port})"
                            )

        return uncooperative

    def _build_topology_nodes(
        self,
        links: List[PhysicalLink],
    ) -> Dict[str, TopologyNode]:
        """
        Build topology nodes from discovered links.

        Args:
            links: Discovered physical links.

        Returns:
            Dictionary of topology nodes.
        """
        nodes: Dict[str, TopologyNode] = {}

        # Create nodes for all cooperative devices
        for device_ip in self.bridge_data_map.keys():
            if device_ip not in nodes:
                nodes[device_ip] = TopologyNode(
                    node_id=device_ip,
                    device_ip=device_ip,
                    is_cooperative=True,
                )

        # Add connections from links
        for link in links:
            if link.device_a in nodes:
                nodes[link.device_a].children.add(link.device_b)
                nodes[link.device_a].port_to_child[link.device_b] = link.port_a
                nodes[link.device_a].degree += 1

            if link.device_b in nodes:
                nodes[link.device_b].children.add(link.device_a)
                nodes[link.device_b].port_to_child[link.device_a] = link.port_b
                nodes[link.device_b].degree += 1

        # Mark junction nodes (degree >= 3)
        for node in nodes.values():
            if node.degree >= 3:
                node.is_junction = True

        return nodes

    def export_topology_summary(self, topology: PhysicalTopology) -> str:
        """
        Export topology as a human-readable summary.

        Args:
            topology: Physical topology.

        Returns:
            String representation of topology.
        """
        lines = ["=" * 60]
        lines.append("Physical Topology Discovery (Bejerano Algorithm)")
        lines.append("=" * 60)
        lines.append(f"Cooperative devices: {len(topology.cooperative_devices)}")
        lines.append(f"Uncooperative elements: {len(topology.uncooperative_devices)}")
        lines.append(f"Physical links: {len(topology.links)}")
        lines.append("")

        lines.append("Network Nodes:")
        lines.append("-" * 60)
        for node_id, node in sorted(topology.nodes.items()):
            node_type = "Junction" if node.is_junction else "Switch"
            lines.append(
                f"  {node_id}: {node_type} (degree={node.degree}, "
                f"neighbors={len(node.children)})"
            )

        lines.append("")
        lines.append("Physical Links:")
        lines.append("-" * 60)
        for link in topology.links:
            lines.append(
                f"  {link.device_a}:{link.port_a} <-> "
                f"{link.device_b}:{link.port_b} [{link.link_type}]"
            )

        if topology.uncooperative_devices:
            lines.append("")
            lines.append("Uncooperative Elements (Inferred):")
            lines.append("-" * 60)
            for elem in sorted(topology.uncooperative_devices):
                lines.append(f"  {elem}")

        lines.append("=" * 60)

        return "\n".join(lines)
