"""Neo4j database manager for network topology."""

import logging
from typing import List, Optional, Set, Dict, Tuple
from neo4j import GraphDatabase, Driver, ManagedTransaction

from .models import (
    NetworkDevice,
    Port,
    Cable,
    Interface,
    CDPNeighbor,
    LLDPNeighbor,
    VLANInfo,
    STPInstance,
    STPInterface,
    DiscoveryResult,
)
from .utils import CableIDGenerator


logger = logging.getLogger(__name__)


class Neo4jManager:
    """Manage Neo4j database operations for network topology."""

    def __init__(self, uri: str, username: str, password: str) -> None:
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI.
            username: Neo4j username.
            password: Neo4j password.
        """
        self.driver: Driver = GraphDatabase.driver(uri, auth=(username, password))
        self.cable_id_gen = CableIDGenerator()
        self._initialize_constraints()
        self._load_existing_cable_ids()

    def close(self) -> None:
        """Close Neo4j connection."""
        self.driver.close()

    def _initialize_constraints(self) -> None:
        """Create uniqueness constraints and indexes."""
        logger.info("Initializing Neo4j constraints and indexes")

        constraints = [
            "CREATE CONSTRAINT device_hostname IF NOT EXISTS FOR (d:NetworkDevice) REQUIRE d.hostname IS UNIQUE",
            "CREATE CONSTRAINT port_id IF NOT EXISTS FOR (p:Port) REQUIRE (p.device_hostname, p.name) IS UNIQUE",
            "CREATE CONSTRAINT interface_id IF NOT EXISTS FOR (i:Interface) REQUIRE (i.device_hostname, i.name) IS UNIQUE",
            "CREATE CONSTRAINT cable_id IF NOT EXISTS FOR (c:Cable) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX port_device IF NOT EXISTS FOR (p:Port) ON (p.device_hostname)",
            "CREATE INDEX interface_device IF NOT EXISTS FOR (i:Interface) ON (i.device_hostname)",
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.debug(f"Constraint/index already exists or error: {e}")

    def _load_existing_cable_ids(self) -> None:
        """Load existing cable IDs from database to avoid duplicates."""
        logger.info("Loading existing cable IDs from Neo4j")

        query = "MATCH (c:Cable) RETURN c.id as id"

        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                self.cable_id_gen.mark_used(record["id"])

    def store_discovery_result(self, result: DiscoveryResult) -> None:
        """
        Store complete discovery result in Neo4j.

        Args:
            result: Discovery result to store.
        """
        logger.info(f"Storing discovery result for {result.device.hostname}")

        with self.driver.session() as session:
            # Store device
            session.execute_write(self._create_network_device, result.device)

            # Store ports
            session.execute_write(self._create_ports, result.device.hostname, result.device.ports)

            # Store interfaces
            session.execute_write(
                self._create_interfaces, result.device.hostname, result.device.interfaces
            )

            # Store CDP neighbors and create cable connections
            session.execute_write(
                self._create_cdp_neighbors, result.device.hostname, result.cdp_neighbors
            )

            # Store LLDP neighbors
            session.execute_write(
                self._create_lldp_neighbors, result.device.hostname, result.lldp_neighbors
            )

            # Store VLAN information
            session.execute_write(self._create_vlans, result.device.hostname, result.vlans)

            # Store STP instances
            session.execute_write(
                self._create_stp_instances, result.device.hostname, result.stp_instances
            )

    @staticmethod
    def _create_network_device(tx: ManagedTransaction, device: NetworkDevice) -> None:
        """Create or update NetworkDevice node."""
        query = """
        MERGE (d:NetworkDevice {hostname: $hostname})
        SET d.mgmt_ip = $mgmt_ip,
            d.platform = $platform,
            d.model = $model,
            d.serial_number = $serial_number,
            d.software_version = $software_version,
            d.updated_at = datetime()
        RETURN d
        """
        tx.run(
            query,
            hostname=device.hostname,
            mgmt_ip=device.mgmt_ip,
            platform=device.platform,
            model=device.model,
            serial_number=device.serial_number,
            software_version=device.software_version,
        )

    @staticmethod
    def _create_ports(tx: ManagedTransaction, hostname: str, ports: List[Port]) -> None:
        """Create or update Port nodes and HAS_PORT relationships."""
        for port in ports:
            query = """
            MATCH (d:NetworkDevice {hostname: $hostname})
            MERGE (p:Port {device_hostname: $hostname, name: $name})
            SET p.status = $status,
                p.speed = $speed,
                p.duplex = $duplex,
                p.description = $description,
                p.vlan = $vlan
            MERGE (d)-[:HAS_PORT]->(p)
            RETURN p
            """
            tx.run(
                query,
                hostname=hostname,
                name=port.name,
                status=port.status.value,
                speed=port.speed,
                duplex=port.duplex,
                description=port.description,
                vlan=port.vlan,
            )

    @staticmethod
    def _create_interfaces(
        tx: ManagedTransaction, hostname: str, interfaces: List[Interface]
    ) -> None:
        """Create or update Interface nodes and HAS relationships."""
        for interface in interfaces:
            query = """
            MATCH (d:NetworkDevice {hostname: $hostname})
            MERGE (i:Interface {device_hostname: $hostname, name: $name})
            SET i.ip_address = $ip_address,
                i.subnet_mask = $subnet_mask,
                i.status = $status,
                i.vlan = $vlan,
                i.description = $description
            MERGE (d)-[:HAS]->(i)
            RETURN i
            """
            tx.run(
                query,
                hostname=hostname,
                name=interface.name,
                ip_address=interface.ip_address,
                subnet_mask=interface.subnet_mask,
                status=interface.status.value,
                vlan=interface.vlan,
                description=interface.description,
            )

    def _create_cdp_neighbors(
        self, tx: ManagedTransaction, hostname: str, neighbors: List[CDPNeighbor]
    ) -> None:
        """Create CDP neighbor relationships and cables."""
        for neighbor in neighbors:
            # Create neighbor device if it doesn't exist
            create_neighbor_query = """
            MERGE (d:NetworkDevice {hostname: $neighbor_hostname})
            ON CREATE SET d.mgmt_ip = $neighbor_ip, d.platform = $platform
            """
            tx.run(
                create_neighbor_query,
                neighbor_hostname=neighbor.neighbor_device,
                neighbor_ip=neighbor.neighbor_ip or "unknown",
                platform=neighbor.platform or "unknown",
            )

            # Create CDP_NEIGHBOR relationship at interface level
            cdp_query = """
            MATCH (d1:NetworkDevice {hostname: $hostname})
            MATCH (d2:NetworkDevice {hostname: $neighbor_hostname})
            MERGE (i1:Interface {device_hostname: $hostname, name: $local_interface})
            MERGE (i2:Interface {device_hostname: $neighbor_hostname, name: $neighbor_interface})
            MERGE (d1)-[:HAS]->(i1)
            MERGE (d2)-[:HAS]->(i2)
            MERGE (i1)-[:CDP_NEIGHBOR]->(i2)
            """
            tx.run(
                cdp_query,
                hostname=hostname,
                neighbor_hostname=neighbor.neighbor_device,
                local_interface=neighbor.local_interface,
                neighbor_interface=neighbor.neighbor_interface,
            )

            # Create cable connection at port level
            cable_id = self._get_or_create_cable_id(
                tx, hostname, neighbor.local_interface, neighbor.neighbor_device, neighbor.neighbor_interface
            )

            cable_query = """
            MATCH (d1:NetworkDevice {hostname: $hostname})
            MATCH (d2:NetworkDevice {hostname: $neighbor_hostname})
            MERGE (p1:Port {device_hostname: $hostname, name: $local_interface})
            MERGE (p2:Port {device_hostname: $neighbor_hostname, name: $neighbor_interface})
            MERGE (d1)-[:HAS_PORT]->(p1)
            MERGE (d2)-[:HAS_PORT]->(p2)
            MERGE (c:Cable {id: $cable_id})
            ON CREATE SET c.type = 'unknown'
            MERGE (p1)-[:CABLE_END_A]->(c)
            MERGE (c)<-[:CABLE_END_B]-(p2)
            """
            tx.run(
                cable_query,
                hostname=hostname,
                neighbor_hostname=neighbor.neighbor_device,
                local_interface=neighbor.local_interface,
                neighbor_interface=neighbor.neighbor_interface,
                cable_id=cable_id,
            )

    def _get_or_create_cable_id(
        self,
        tx: ManagedTransaction,
        host1: str,
        port1: str,
        host2: str,
        port2: str,
    ) -> str:
        """
        Get existing cable ID or create a new one for a port pair.

        Args:
            tx: Neo4j transaction.
            host1: First device hostname.
            port1: First port name.
            host2: Second device hostname.
            port2: Second port name.

        Returns:
            Cable ID (4-char alphanumeric).
        """
        # Check if cable already exists (bidirectional)
        query = """
        MATCH (p1:Port {device_hostname: $host1, name: $port1})-[:CABLE_END_A]->(c:Cable)<-[:CABLE_END_B]-(p2:Port {device_hostname: $host2, name: $port2})
        RETURN c.id as cable_id
        UNION
        MATCH (p1:Port {device_hostname: $host1, name: $port1})-[:CABLE_END_B]->(c:Cable)<-[:CABLE_END_A]-(p2:Port {device_hostname: $host2, name: $port2})
        RETURN c.id as cable_id
        """
        result = tx.run(query, host1=host1, port1=port1, host2=host2, port2=port2)
        record = result.single()

        if record:
            return record["cable_id"]

        # Generate new cable ID
        return self.cable_id_gen.generate()

    @staticmethod
    def _create_lldp_neighbors(
        tx: ManagedTransaction, hostname: str, neighbors: List[LLDPNeighbor]
    ) -> None:
        """Create LLDP neighbor relationships."""
        for neighbor in neighbors:
            # Create neighbor device if it doesn't exist
            create_neighbor_query = """
            MERGE (d:NetworkDevice {hostname: $neighbor_hostname})
            ON CREATE SET d.mgmt_ip = $neighbor_ip, d.platform = 'unknown'
            """
            tx.run(
                create_neighbor_query,
                neighbor_hostname=neighbor.neighbor_device,
                neighbor_ip=neighbor.neighbor_ip or "unknown",
            )

            # Create LLDP_NEIGHBOR relationship
            lldp_query = """
            MATCH (d1:NetworkDevice {hostname: $hostname})
            MATCH (d2:NetworkDevice {hostname: $neighbor_hostname})
            MERGE (i1:Interface {device_hostname: $hostname, name: $local_interface})
            MERGE (i2:Interface {device_hostname: $neighbor_hostname, name: $neighbor_interface})
            MERGE (d1)-[:HAS]->(i1)
            MERGE (d2)-[:HAS]->(i2)
            MERGE (i1)-[:LLDP_NEIGHBOR]->(i2)
            """
            tx.run(
                lldp_query,
                hostname=hostname,
                neighbor_hostname=neighbor.neighbor_device,
                local_interface=neighbor.local_interface,
                neighbor_interface=neighbor.neighbor_interface,
            )

    @staticmethod
    def _create_vlans(tx: ManagedTransaction, hostname: str, vlans: List[VLANInfo]) -> None:
        """Create VLAN nodes and relationships."""
        for vlan in vlans:
            query = """
            MATCH (d:NetworkDevice {hostname: $hostname})
            MERGE (v:VLAN {device_hostname: $hostname, vlan_id: $vlan_id})
            SET v.name = $name,
                v.status = $status,
                v.ports = $ports
            MERGE (d)-[:HAS_VLAN]->(v)
            """
            tx.run(
                query,
                hostname=hostname,
                vlan_id=vlan.vlan_id,
                name=vlan.name,
                status=vlan.status,
                ports=vlan.ports,
            )

    @staticmethod
    def _create_stp_instances(
        tx: ManagedTransaction, hostname: str, stp_instances: List[STPInstance]
    ) -> None:
        """Create STP instance nodes and relationships."""
        for stp in stp_instances:
            # Create STP instance node
            query = """
            MATCH (d:NetworkDevice {hostname: $hostname})
            MERGE (s:STPInstance {device_hostname: $hostname, vlan_id: $vlan_id})
            SET s.bridge_priority = $bridge_priority,
                s.bridge_address = $bridge_address,
                s.root_bridge_priority = $root_bridge_priority,
                s.root_bridge_address = $root_bridge_address,
                s.root_port = $root_port,
                s.root_path_cost = $root_path_cost,
                s.is_root = $is_root
            MERGE (d)-[:HAS_STP]->(s)
            """
            tx.run(
                query,
                hostname=hostname,
                vlan_id=stp.vlan_id,
                bridge_priority=stp.bridge_priority,
                bridge_address=stp.bridge_address,
                root_bridge_priority=stp.root_bridge_priority,
                root_bridge_address=stp.root_bridge_address,
                root_port=stp.root_port,
                root_path_cost=stp.root_path_cost,
                is_root=stp.is_root,
            )

            # Create STP interface relationships
            for stp_intf in stp.interfaces:
                intf_query = """
                MATCH (s:STPInstance {device_hostname: $hostname, vlan_id: $vlan_id})
                MATCH (i:Interface {device_hostname: $hostname, name: $interface})
                MERGE (s)-[r:STP_INTERFACE]->(i)
                SET r.role = $role,
                    r.state = $state,
                    r.cost = $cost,
                    r.priority = $priority,
                    r.port_id = $port_id
                """
                tx.run(
                    intf_query,
                    hostname=hostname,
                    vlan_id=stp.vlan_id,
                    interface=stp_intf.interface,
                    role=stp_intf.role,
                    state=stp_intf.state,
                    cost=stp_intf.cost,
                    priority=stp_intf.priority,
                    port_id=stp_intf.port_id,
                )

    def get_visited_devices(self) -> Set[str]:
        """
        Get set of all device hostnames already in the database.

        Returns:
            Set of device hostnames.
        """
        query = "MATCH (d:NetworkDevice) RETURN d.hostname as hostname"

        with self.driver.session() as session:
            result = session.run(query)
            return {record["hostname"] for record in result}

    def device_exists(self, hostname: str) -> bool:
        """
        Check if a device exists in the database.

        Args:
            hostname: Device hostname to check.

        Returns:
            True if device exists, False otherwise.
        """
        query = "MATCH (d:NetworkDevice {hostname: $hostname}) RETURN d LIMIT 1"

        with self.driver.session() as session:
            result = session.run(query, hostname=hostname)
            return result.single() is not None
