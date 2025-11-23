#!/usr/bin/env python3
"""
Example demonstrating DMTF CIM-based nesting relationships in NetMapper.

This script shows how to model hierarchical infrastructure using CIM relationship types:
- CIM_CONTAINER: Physical containment (movable items like servers in racks)
- CIM_COMPONENT: Composition (integral subcomponents like PSUs, line cards)
- CIM_MEMBER_OF_COLLECTION: Logical hierarchy (device groups, collections)

Based on DMTF CIM Schema v2.55.0
"""

import logging
import json
from netmapper.neo4j_manager import Neo4jManager
from netmapper.models import (
    CIMNestingRelationship,
    CIMRelationshipType,
    RemovalConditions,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_datacenter_hierarchy(manager: Neo4jManager) -> None:
    """
    Create a sample datacenter hierarchy using CIM relationships.

    Topology:
    - Datacenter DC1
      - Rack R01 (CONTAINER)
        - Server SRV-01 (CONTAINER, removable when off)
          - PSU-1 (COMPONENT, integral part)
          - PSU-2 (COMPONENT, integral part)
          - NIC-1 (COMPONENT, hot-swappable)
        - Server SRV-02 (CONTAINER, removable when off)
        - Switch SW-01 (CONTAINER, removable when off)
          - LineCard-1 (COMPONENT, slot 1)
          - LineCard-2 (COMPONENT, slot 2)
      - Rack R02 (CONTAINER)
    - Device Group "Core-Switches" (MEMBER_OF_COLLECTION)
      - SW-01
      - SW-02
    """
    logger.info("Creating datacenter hierarchy with CIM relationships...")

    # 1. CONTAINER Relationships - Physical containment (movable items)

    # Datacenter contains Racks
    racks = [
        CIMNestingRelationship(
            parent_id="datacenter-dc1",
            child_id="rack-r01",
            relationship_type=CIMRelationshipType.CONTAINER,
            location_within_container="Row A, Position 1",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=False,  # Rack can exist independently
            properties={"rack_height_u": 42}
        ),
        CIMNestingRelationship(
            parent_id="datacenter-dc1",
            child_id="rack-r02",
            relationship_type=CIMRelationshipType.CONTAINER,
            location_within_container="Row A, Position 2",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=False,
            properties={"rack_height_u": 42}
        ),
    ]

    for rack_rel in racks:
        manager.create_cim_nesting_relationship(rack_rel)

    # Rack contains Servers and Switches
    rack_contents = [
        CIMNestingRelationship(
            parent_id="rack-r01",
            child_id="server-srv01",
            relationship_type=CIMRelationshipType.CONTAINER,
            location_within_container="U42-U44",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=False,
            properties={"device_type": "server", "power_watts": 750}
        ),
        CIMNestingRelationship(
            parent_id="rack-r01",
            child_id="server-srv02",
            relationship_type=CIMRelationshipType.CONTAINER,
            location_within_container="U39-U41",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=False,
            properties={"device_type": "server", "power_watts": 750}
        ),
        CIMNestingRelationship(
            parent_id="rack-r01",
            child_id="switch-sw01",
            relationship_type=CIMRelationshipType.CONTAINER,
            location_within_container="U1-U2",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=False,
            properties={"device_type": "switch", "model": "Cisco Nexus 9300"}
        ),
    ]

    for content_rel in rack_contents:
        manager.create_cim_nesting_relationship(content_rel)

    # 2. COMPONENT Relationships - Composition (integral subcomponents)

    # Server components (integral parts, rarely moved)
    server_components = [
        # SRV-01 components
        CIMNestingRelationship(
            parent_id="server-srv01",
            child_id="psu-srv01-1",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="PSU Bay 1",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=True,  # PSU cannot exist without server (composition)
            properties={"component_type": "power_supply", "wattage": 750}
        ),
        CIMNestingRelationship(
            parent_id="server-srv01",
            child_id="psu-srv01-2",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="PSU Bay 2",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=True,
            properties={"component_type": "power_supply", "wattage": 750}
        ),
        CIMNestingRelationship(
            parent_id="server-srv01",
            child_id="nic-srv01-1",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="PCIe Slot 1",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_ON_OR_OFF,
            is_weak=True,
            properties={"component_type": "network_card", "speed": "10G"}
        ),
    ]

    # Switch components (line cards)
    switch_components = [
        CIMNestingRelationship(
            parent_id="switch-sw01",
            child_id="linecard-sw01-1",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="Slot 1",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=True,
            properties={"component_type": "line_card", "ports": 48}
        ),
        CIMNestingRelationship(
            parent_id="switch-sw01",
            child_id="linecard-sw01-2",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="Slot 2",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=True,
            properties={"component_type": "line_card", "ports": 48}
        ),
        CIMNestingRelationship(
            parent_id="switch-sw01",
            child_id="supervisor-sw01",
            relationship_type=CIMRelationshipType.COMPONENT,
            location_within_container="Supervisor Slot",
            removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
            is_weak=True,
            properties={"component_type": "supervisor", "cpu_cores": 4}
        ),
    ]

    for component_rel in server_components + switch_components:
        manager.create_cim_nesting_relationship(component_rel)

    # 3. MEMBER_OF_COLLECTION - Logical hierarchy

    # Create device collections (logical grouping)
    collections = [
        CIMNestingRelationship(
            parent_id="collection-core-switches",
            child_id="switch-sw01",
            relationship_type=CIMRelationshipType.MEMBER_OF_COLLECTION,
            is_weak=False,  # Member can exist independently
            properties={
                "collection_name": "Core Switches",
                "role": "core",
                "redundancy_group": "1"
            }
        ),
        CIMNestingRelationship(
            parent_id="collection-core-switches",
            child_id="switch-sw02",
            relationship_type=CIMRelationshipType.MEMBER_OF_COLLECTION,
            is_weak=False,
            properties={
                "collection_name": "Core Switches",
                "role": "core",
                "redundancy_group": "1"
            }
        ),
        CIMNestingRelationship(
            parent_id="collection-compute-nodes",
            child_id="server-srv01",
            relationship_type=CIMRelationshipType.MEMBER_OF_COLLECTION,
            is_weak=False,
            properties={
                "collection_name": "Compute Nodes",
                "cluster": "k8s-prod"
            }
        ),
        CIMNestingRelationship(
            parent_id="collection-compute-nodes",
            child_id="server-srv02",
            relationship_type=CIMRelationshipType.MEMBER_OF_COLLECTION,
            is_weak=False,
            properties={
                "collection_name": "Compute Nodes",
                "cluster": "k8s-prod"
            }
        ),
    ]

    for collection_rel in collections:
        manager.create_cim_nesting_relationship(collection_rel)

    logger.info("Datacenter hierarchy created successfully!")


def query_hierarchy_examples(manager: Neo4jManager) -> None:
    """Demonstrate querying CIM hierarchies."""
    logger.info("\n=== Querying CIM Hierarchies ===\n")

    # Example 1: Get all children of a rack
    logger.info("1. Get all devices in Rack R01:")
    rack_contents = manager.get_cim_children("rack-r01")
    for item in rack_contents:
        logger.info(f"  - {item['id']}: {item['relationship']}")

    # Example 2: Get only CONTAINER relationships (movable items)
    logger.info("\n2. Get only movable items in Rack R01:")
    movable_items = manager.get_cim_children(
        "rack-r01",
        CIMRelationshipType.CONTAINER
    )
    for item in movable_items:
        logger.info(
            f"  - {item['id']} at {item['relationship'].get('location_within_container')}"
        )

    # Example 3: Get integral components of a server
    logger.info("\n3. Get integral components of Server SRV-01:")
    components = manager.get_cim_children(
        "server-srv01",
        CIMRelationshipType.COMPONENT
    )
    for component in components:
        is_weak = component['relationship'].get('is_weak', False)
        comp_type = component['relationship'].get('component_type', 'unknown')
        logger.info(
            f"  - {component['id']} ({comp_type}) - "
            f"Integral part: {is_weak}"
        )

    # Example 4: Get complete hierarchy
    logger.info("\n4. Get complete hierarchy from Datacenter DC1:")
    hierarchy = manager.get_cim_hierarchy("datacenter-dc1", max_depth=5)
    logger.info(json.dumps(hierarchy, indent=2, default=str))

    # Example 5: Get members of a logical collection
    logger.info("\n5. Get members of Core Switches collection:")
    members = manager.get_cim_children(
        "collection-core-switches",
        CIMRelationshipType.MEMBER_OF_COLLECTION
    )
    for member in members:
        role = member['relationship'].get('role', 'N/A')
        logger.info(f"  - {member['id']} (role: {role})")


def main():
    """Main function to demonstrate CIM nesting relationships."""
    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "password"

    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    manager = Neo4jManager(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

    try:
        # Create sample hierarchy
        create_datacenter_hierarchy(manager)

        # Query examples
        query_hierarchy_examples(manager)

        logger.info("\n=== CIM Nesting Example Complete ===")
        logger.info("\nYou can now visualize the hierarchy in Neo4j Browser:")
        logger.info("  MATCH (n)-[r]->(m) WHERE r.relationship_type IS NOT NULL RETURN n,r,m")
        logger.info("\nOr query specific relationship types:")
        logger.info("  MATCH (n)-[r:CIM_CONTAINER]->(m) RETURN n,r,m  // Physical containment")
        logger.info("  MATCH (n)-[r:CIM_COMPONENT]->(m) RETURN n,r,m  // Integral components")
        logger.info("  MATCH (n)-[r:CIM_MEMBER_OF_COLLECTION]->(m) RETURN n,r,m  // Logical groups")

    finally:
        manager.close()
        logger.info("Connection closed.")


if __name__ == "__main__":
    main()
