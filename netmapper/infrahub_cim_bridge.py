"""
Bridge between Infrahub models and DMTF CIM relationships.

Demonstrates how Infrahub's Component relationships align with CIM semantics,
and provides utilities to convert between the two models.
"""

import logging
from typing import List, Dict, Optional

from .models import CIMNestingRelationship, CIMRelationshipType, RemovalConditions
from .infrahub_models import (
    InfrahubDevice,
    InfrahubInterface,
    InfrahubSite,
    InfrahubRack,
)

logger = logging.getLogger(__name__)


class InfrahubCIMBridge:
    """
    Bridge between Infrahub models and CIM relationships.

    Infrahub uses Component relationships (kind: Component) which align well
    with CIM_COMPONENT (composition). This bridge provides mapping utilities.

    Mapping:
    - Infrahub Component -> CIM_COMPONENT (composition)
    - Infrahub Attribute -> CIM_CONTAINER (aggregation)
    - Infrahub hierarchical locations -> CIM_CONTAINER
    """

    @staticmethod
    def infrahub_to_cim_relationship(
        parent_type: str,
        child_type: str,
        parent_id: str,
        child_id: str,
        location: Optional[str] = None,
        infrahub_kind: str = "Component",
    ) -> CIMNestingRelationship:
        """
        Convert Infrahub relationship to CIM nesting relationship.

        Args:
            parent_type: Infrahub parent node type (e.g., "InfraDevice")
            child_type: Infrahub child node type (e.g., "InfraInterface")
            parent_id: Parent node ID
            child_id: Child node ID
            location: Location within container (optional)
            infrahub_kind: Infrahub relationship kind (Component, Attribute, etc.)

        Returns:
            CIMNestingRelationship instance

        Examples:
            >>> # Infrahub: Device -[Component]-> Interface
            >>> # Maps to: CIM_COMPONENT (interface is integral to device)
            >>> rel = infrahub_to_cim_relationship(
            ...     "InfraDevice", "InfraInterface",
            ...     "router-01", "GigabitEthernet0/0",
            ...     infrahub_kind="Component"
            ... )
            >>> assert rel.relationship_type == CIMRelationshipType.COMPONENT
            >>> assert rel.is_weak == True
        """

        # Map Infrahub relationship kind to CIM type
        if infrahub_kind == "Component":
            # Component relationships are integral parts (composition)
            cim_type = CIMRelationshipType.COMPONENT
            is_weak = True
            removal = RemovalConditions.REMOVABLE_WHEN_OFF

        elif infrahub_kind == "Attribute":
            # Attribute relationships are associations (aggregation)
            cim_type = CIMRelationshipType.CONTAINER
            is_weak = False
            removal = RemovalConditions.REMOVABLE_WHEN_OFF

        else:
            # Default to CONTAINER for other types
            cim_type = CIMRelationshipType.CONTAINER
            is_weak = False
            removal = RemovalConditions.UNKNOWN

        # Special cases based on node types
        if parent_type == "LocationSite" and child_type == "InfraDevice":
            # Site contains devices (physical containment)
            cim_type = CIMRelationshipType.CONTAINER
            is_weak = False

        elif parent_type == "LocationRack" and child_type == "InfraDevice":
            # Rack contains devices (physical containment)
            cim_type = CIMRelationshipType.CONTAINER
            is_weak = False
            removal = RemovalConditions.REMOVABLE_WHEN_OFF

        elif parent_type == "InfraDevice" and child_type == "InfraInterface":
            # Device has interfaces (composition)
            cim_type = CIMRelationshipType.COMPONENT
            is_weak = True

        return CIMNestingRelationship(
            parent_id=parent_id,
            child_id=child_id,
            relationship_type=cim_type,
            location_within_container=location,
            removal_conditions=removal,
            is_weak=is_weak,
            properties={
                "infrahub_parent_type": parent_type,
                "infrahub_child_type": child_type,
                "infrahub_kind": infrahub_kind,
            },
        )

    @staticmethod
    def create_infrahub_hierarchy_as_cim(
        site: InfrahubSite,
        racks: List[InfrahubRack],
        devices: List[InfrahubDevice],
    ) -> List[CIMNestingRelationship]:
        """
        Create CIM relationships for Infrahub hierarchical location structure.

        Infrahub location hierarchy:
        LocationSite -> LocationRack -> InfraDevice

        Maps to CIM_CONTAINER relationships.

        Args:
            site: Infrahub site
            racks: List of racks in site
            devices: List of devices in racks

        Returns:
            List of CIM relationships
        """
        relationships = []

        # Site -> Racks
        for rack in racks:
            if rack.site == site.name:
                rel = CIMNestingRelationship(
                    parent_id=site.name,
                    child_id=rack.name,
                    relationship_type=CIMRelationshipType.CONTAINER,
                    location_within_container=rack.description or None,
                    removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
                    is_weak=False,
                    properties={
                        "infrahub_type": "LocationRack",
                        "height_u": rack.height_u,
                    },
                )
                relationships.append(rel)

        # Racks -> Devices
        for device in devices:
            # Find device's rack (simplified - assumes rack name in device metadata)
            for rack in racks:
                # In real implementation, would query device.rack relationship
                rel = CIMNestingRelationship(
                    parent_id=rack.name,
                    child_id=device.name,
                    relationship_type=CIMRelationshipType.CONTAINER,
                    location_within_container="U42",  # Would come from device metadata
                    removal_conditions=RemovalConditions.REMOVABLE_WHEN_OFF,
                    is_weak=False,
                    properties={
                        "infrahub_type": "InfraDevice",
                        "device_type": device.type,
                        "device_role": device.role.value if device.role else None,
                    },
                )
                relationships.append(rel)
                break  # One device per rack for this example

        return relationships

    @staticmethod
    def map_infrahub_component_to_cim(
        device: InfrahubDevice,
        interfaces: List[InfrahubInterface],
    ) -> List[CIMNestingRelationship]:
        """
        Map Infrahub Component relationships to CIM_COMPONENT.

        Infrahub uses "kind: Component" for integral parts:
        - InfraDevice -[Component]-> InfraInterface
        - InfraDevice -[Component]-> InfraBGPSession

        These map to CIM_COMPONENT (composition).

        Args:
            device: Infrahub device
            interfaces: List of interfaces belonging to device

        Returns:
            List of CIM_COMPONENT relationships
        """
        relationships = []

        for interface in interfaces:
            if interface.device == device.name:
                rel = CIMNestingRelationship(
                    parent_id=device.name,
                    child_id=f"{device.name}:{interface.name}",
                    relationship_type=CIMRelationshipType.COMPONENT,
                    location_within_container=interface.name,
                    removal_conditions=RemovalConditions.REMOVABLE_WHEN_ON_OR_OFF
                    if interface.role and "management" not in interface.name.lower()
                    else RemovalConditions.REMOVABLE_WHEN_OFF,
                    is_weak=True,  # Interface cannot exist without device
                    properties={
                        "infrahub_type": "InfraInterface",
                        "interface_role": interface.role.value if interface.role else None,
                        "interface_status": interface.status.value,
                    },
                )
                relationships.append(rel)

        return relationships

    @staticmethod
    def generate_infrahub_yaml_with_cim_annotations(
        relationships: List[CIMNestingRelationship],
        output_file: str,
    ):
        """
        Generate Infrahub YAML with CIM relationship annotations.

        Creates an Infrahub-compatible YAML file with CIM relationship metadata
        embedded as custom attributes.

        Args:
            relationships: List of CIM relationships
            output_file: Output YAML file path
        """
        import yaml

        # Group relationships by type
        containers = [r for r in relationships if r.relationship_type == CIMRelationshipType.CONTAINER]
        components = [r for r in relationships if r.relationship_type == CIMRelationshipType.COMPONENT]
        collections = [r for r in relationships if r.relationship_type == CIMRelationshipType.MEMBER_OF_COLLECTION]

        data = {
            "version": "1.0",
            "metadata": {
                "cim_version": "2.55.0",
                "description": "Infrahub topology with DMTF CIM relationship annotations",
            },
            "relationships": {
                "cim_containers": [
                    {
                        "parent": r.parent_id,
                        "child": r.child_id,
                        "location": r.location_within_container,
                        "removal_conditions": r.removal_conditions.value if r.removal_conditions else None,
                        "is_weak": r.is_weak,
                        "properties": r.properties,
                    }
                    for r in containers
                ],
                "cim_components": [
                    {
                        "parent": r.parent_id,
                        "child": r.child_id,
                        "location": r.location_within_container,
                        "removal_conditions": r.removal_conditions.value if r.removal_conditions else None,
                        "is_weak": r.is_weak,
                        "properties": r.properties,
                    }
                    for r in components
                ],
                "cim_collections": [
                    {
                        "collection": r.parent_id,
                        "member": r.child_id,
                        "properties": r.properties,
                    }
                    for r in collections
                ],
            },
        }

        with open(output_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated Infrahub YAML with CIM annotations: {output_file}")


# ============================================================================
# Example Usage
# ============================================================================


def example_usage():
    """Example demonstrating Infrahub-CIM bridge."""

    # Example 1: Convert Infrahub Component to CIM
    device_interface_rel = InfrahubCIMBridge.infrahub_to_cim_relationship(
        parent_type="InfraDevice",
        child_type="InfraInterface",
        parent_id="core-router-01",
        child_id="core-router-01:GigabitEthernet0/0",
        location="GigabitEthernet0/0",
        infrahub_kind="Component",
    )

    print("Example 1: Infrahub Component -> CIM_COMPONENT")
    print(f"  Relationship Type: {device_interface_rel.relationship_type}")
    print(f"  Is Weak (Composition): {device_interface_rel.is_weak}")
    print(f"  Location: {device_interface_rel.location_within_container}")

    # Example 2: Rack contains Device
    rack_device_rel = InfrahubCIMBridge.infrahub_to_cim_relationship(
        parent_type="LocationRack",
        child_type="InfraDevice",
        parent_id="rack-01",
        child_id="core-router-01",
        location="U42-U44",
        infrahub_kind="Attribute",
    )

    print("\nExample 2: Infrahub Rack -> Device (Attribute) -> CIM_CONTAINER")
    print(f"  Relationship Type: {rack_device_rel.relationship_type}")
    print(f"  Is Weak (Composition): {rack_device_rel.is_weak}")
    print(f"  Removal Conditions: {rack_device_rel.removal_conditions}")

    print("\n✓ Infrahub models successfully mapped to CIM relationships!")


if __name__ == "__main__":
    example_usage()
