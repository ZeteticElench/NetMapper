"""Strongly typed data models for network topology discovery."""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class PortStatus(str, Enum):
    """Port status enumeration."""
    UP = "up"
    DOWN = "down"
    ADMIN_DOWN = "admin-down"
    UNKNOWN = "unknown"


class CableType(str, Enum):
    """Cable type enumeration."""
    COPPER = "copper"
    FIBER = "fiber"
    UNKNOWN = "unknown"


class CIMRelationshipType(str, Enum):
    """
    DMTF CIM relationship types for nesting hierarchies.

    Based on CIM Schema v2.55.0:
    - CONTAINER: Physical containment (CIM_Container, CIM_PackagedComponent)
    - COMPONENT: Composition relationship (CIM_ConcreteComponent with Composition)
    - MEMBER_OF_COLLECTION: Logical hierarchy (CIM_MemberOfCollection)
    """
    CONTAINER = "CIM_CONTAINER"
    COMPONENT = "CIM_COMPONENT"
    MEMBER_OF_COLLECTION = "CIM_MEMBER_OF_COLLECTION"


class RemovalConditions(str, Enum):
    """
    CIM RemovalConditions for physical components.

    Indicates whether a component can be removed and under what conditions.
    Maps to CIM_PhysicalComponent.RemovalConditions.
    """
    UNKNOWN = "Unknown"
    NOT_APPLICABLE = "Not Applicable"
    REMOVABLE_WHEN_OFF = "Removable when off"
    REMOVABLE_WHEN_ON_OR_OFF = "Removable when on or off"


class Port(BaseModel):
    """Physical port model."""
    name: str
    status: PortStatus
    speed: Optional[str] = None
    duplex: Optional[str] = None
    description: Optional[str] = None
    vlan: Optional[int] = None


class Cable(BaseModel):
    """Cable connecting two ports."""
    id: str = Field(..., description="4-character alphanumeric cable ID")
    type: CableType = CableType.UNKNOWN
    length: Optional[str] = None


class Interface(BaseModel):
    """Logical interface model."""
    name: str
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    status: PortStatus
    vlan: Optional[int] = None
    description: Optional[str] = None


class NetworkDevice(BaseModel):
    """Network device model."""
    hostname: str
    mgmt_ip: str
    platform: str
    model: Optional[str] = None
    serial_number: Optional[str] = None
    software_version: Optional[str] = None
    ports: List[Port] = Field(default_factory=list)
    interfaces: List[Interface] = Field(default_factory=list)


class CDPNeighbor(BaseModel):
    """CDP neighbor information."""
    local_interface: str
    neighbor_device: str
    neighbor_interface: str
    neighbor_ip: Optional[str] = None
    platform: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class LLDPNeighbor(BaseModel):
    """LLDP neighbor information."""
    local_interface: str
    neighbor_device: str
    neighbor_interface: str
    neighbor_ip: Optional[str] = None
    platform: Optional[str] = None
    system_description: Optional[str] = None


class VLANInfo(BaseModel):
    """VLAN information."""
    vlan_id: int
    name: str
    status: str
    ports: List[str] = Field(default_factory=list)


class STPInterface(BaseModel):
    """STP interface information."""
    interface: str
    role: str  # Root, Designated, Alternate, Backup
    state: str  # Forwarding, Blocking, Listening, Learning
    cost: Optional[int] = None
    priority: Optional[int] = None
    port_id: Optional[str] = None


class STPInstance(BaseModel):
    """STP instance for a VLAN."""
    vlan_id: int
    bridge_priority: int
    bridge_address: str
    root_bridge_priority: int
    root_bridge_address: str
    root_port: Optional[str] = None
    root_path_cost: Optional[int] = None
    interfaces: List[STPInterface] = Field(default_factory=list)
    is_root: bool = False


class DeviceCredentials(BaseModel):
    """Device credentials for PyATS connection."""
    hostname: str
    ip: str
    username: str
    password: str
    enable_password: Optional[str] = None
    protocol: str = "ssh"
    port: int = 22
    os: str = "ios"  # ios, iosxe, nxos, iosxr, etc.


class DiscoveryConfig(BaseModel):
    """Discovery configuration."""
    start_device: DeviceCredentials
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    max_depth: Optional[int] = None
    discover_cdp: bool = True
    discover_lldp: bool = True
    discover_stp: bool = True
    discover_vlans: bool = True
    connection_timeout: int = 30
    command_timeout: int = 30
    # Parallel discovery settings
    parallel_discovery: bool = True
    max_workers: int = 10
    queue_max_size: int = 100
    # Adaptive worker tuning
    enable_adaptive_tuning: bool = True
    min_workers: int = 5
    adaptive_max_workers: int = 100
    # Batched Neo4j writes
    enable_neo4j_batching: bool = True
    # Bejerano Layer 2 topology discovery
    enable_bejerano: bool = True
    snmp_community: str = "public"
    mac_collection_method: str = "snmp"  # "snmp" or "pyats"


class DiscoveryResult(BaseModel):
    """Result of device discovery."""
    device: NetworkDevice
    cdp_neighbors: List[CDPNeighbor] = Field(default_factory=list)
    lldp_neighbors: List[LLDPNeighbor] = Field(default_factory=list)
    vlans: List[VLANInfo] = Field(default_factory=list)
    stp_instances: List[STPInstance] = Field(default_factory=list)


class CIMNestingRelationship(BaseModel):
    """
    CIM-based nesting relationship between nodes.

    Implements DMTF CIM containment, composition, and membership relationships
    to model hierarchical structures in network infrastructure.

    Examples:
    - Rack CONTAINS Server (movable, removal_conditions=REMOVABLE_WHEN_OFF)
    - Server COMPONENT PowerSupply (integral part, is_weak=True)
    - DeviceGroup MEMBER_OF_COLLECTION Switch1 (logical grouping)
    """
    parent_id: str = Field(..., description="Parent node identifier (hostname, ID, etc.)")
    child_id: str = Field(..., description="Child node identifier")
    relationship_type: CIMRelationshipType = Field(
        ...,
        description="Type of CIM relationship"
    )

    # CIM_Container properties
    location_within_container: Optional[str] = Field(
        None,
        description="Position of child within parent (e.g., 'Slot 2', 'Bay 3')"
    )

    # CIM_PhysicalComponent properties
    removal_conditions: Optional[RemovalConditions] = Field(
        None,
        description="Conditions under which child can be removed from parent"
    )

    # Composition semantics
    is_weak: bool = Field(
        False,
        description="If True, child cannot exist without parent (Composition). "
                   "If False, child can exist independently (Aggregation)."
    )

    # Additional metadata
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional CIM properties or custom metadata"
    )
