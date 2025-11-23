"""
Infrahub model integration for NetMapper.

Provides adapters and converters to map NetMapper discovery data to Infrahub
data models, enabling standardized infrastructure representation compatible
with Infrahub's schema.

Based on Infrahub stable branch models:
https://github.com/opsmill/infrahub/tree/stable/models/
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Infrahub Base Enums (from models/base/dcim.yml and ipam.yml)
# ============================================================================


class InfraDeviceStatus(str, Enum):
    """Device operational status."""
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    MAINTENANCE = "maintenance"
    DRAINED = "drained"


class InfraDeviceRole(str, Enum):
    """Device role in network."""
    CORE = "core"
    EDGE = "edge"
    CPE = "cpe"
    FIREWALL = "firewall"
    SPINE = "spine"
    LEAF = "leaf"


class InfraInterfaceStatus(str, Enum):
    """Interface operational status."""
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    MAINTENANCE = "maintenance"
    DRAINED = "drained"


class InfraInterfaceRole(str, Enum):
    """Interface role in network."""
    BACKBONE = "backbone"
    UPSTREAM = "upstream"
    PEERING = "peering"
    PEER = "peer"
    SERVER = "server"
    LOOPBACK = "loopback"
    MANAGEMENT = "management"
    UPLINK = "uplink"
    LEAF = "leaf"
    SPARE = "spare"


class VLANStatus(str, Enum):
    """VLAN operational status."""
    ACTIVE = "active"
    PROVISIONING = "provisioning"
    MAINTENANCE = "maintenance"
    DRAINED = "drained"


class VLANRole(str, Enum):
    """VLAN role."""
    SERVER = "server"
    MANAGEMENT = "management"
    USER = "user"


# ============================================================================
# Infrahub Models (aligned with models/base/dcim.yml)
# ============================================================================


class InfrahubDevice(BaseModel):
    """
    Infrahub InfraDevice model.

    Maps to: models/base/dcim.yml -> InfraDevice
    Namespace: Infra
    """
    name: str = Field(..., description="Unique device name")
    description: Optional[str] = Field(None, description="Device description")
    type: str = Field(..., description="Device type (router, switch, firewall, etc.)")
    status: Optional[InfraDeviceStatus] = Field(
        InfraDeviceStatus.ACTIVE,
        description="Operational status"
    )
    role: Optional[InfraDeviceRole] = Field(None, description="Network role")

    # Relationships (stored as references)
    site: Optional[str] = Field(None, description="Reference to LocationSite")
    primary_address: Optional[str] = Field(None, description="Primary IP address")
    asn: Optional[int] = Field(None, description="Autonomous System Number")

    # Additional attributes from NetMapper
    platform: Optional[str] = Field(None, description="Platform/OS type")
    model: Optional[str] = Field(None, description="Hardware model")
    serial_number: Optional[str] = Field(None, description="Serial number")
    software_version: Optional[str] = Field(None, description="Software version")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags")


class InfrahubInterface(BaseModel):
    """
    Infrahub InfraInterface model (Generic).

    Maps to: models/base/dcim.yml -> InfraInterface (Generic)
    Namespace: Infra
    """
    name: str = Field(..., description="Interface name")
    description: Optional[str] = Field(None, description="Interface description")
    speed: Optional[int] = Field(None, description="Interface speed in Mbps")
    mtu: int = Field(1500, description="Maximum Transmission Unit")
    enabled: bool = Field(True, description="Interface enabled")
    status: Optional[InfraInterfaceStatus] = Field(
        InfraInterfaceStatus.ACTIVE,
        description="Operational status"
    )
    role: Optional[InfraInterfaceRole] = Field(None, description="Interface role")

    # Relationship
    device: str = Field(..., description="Reference to InfraDevice")

    # L3 Interface properties (for InfraInterfaceL3)
    ip_addresses: List[str] = Field(default_factory=list, description="Assigned IP addresses")


class InfrahubVLAN(BaseModel):
    """
    Infrahub InfraVLAN model.

    Maps to: models/base/ipam.yml -> InfraVLAN
    Namespace: Infra
    """
    name: str = Field(..., description="VLAN name (unique)")
    description: Optional[str] = Field(None, description="VLAN description")
    vlan_id: int = Field(..., description="VLAN ID (1-4094)")
    status: VLANStatus = Field(
        VLANStatus.PROVISIONING,
        description="Operational status"
    )
    role: VLANRole = Field(VLANRole.SERVER, description="VLAN role")

    # Relationships
    site: Optional[str] = Field(None, description="Reference to LocationSite")
    gateway: Optional[str] = Field(None, description="Reference to InfraInterfaceL3 (L3 gateway)")


class InfrahubIPAddress(BaseModel):
    """
    Infrahub IpamIPAddress model.

    Maps to: models/base/ipam.yml -> IpamIPAddress
    Namespace: Ipam
    """
    address: str = Field(..., description="IP address with prefix (e.g., 192.168.1.1/24)")

    # Relationship
    interface: Optional[str] = Field(None, description="Reference to InfraInterfaceL3")


class InfrahubCircuit(BaseModel):
    """
    Infrahub InfraCircuit model.

    Maps to: models/base/dcim.yml -> InfraCircuit
    Namespace: Infra
    """
    circuit_id: str = Field(..., description="Unique circuit identifier")
    description: Optional[str] = Field(None, description="Circuit description")
    vendor_id: Optional[str] = Field(None, description="Vendor circuit ID")
    status: Optional[InfraDeviceStatus] = Field(
        InfraDeviceStatus.ACTIVE,
        description="Circuit status"
    )
    role: Optional[InfraInterfaceRole] = Field(None, description="Circuit role")

    # Relationships
    provider: Optional[str] = Field(None, description="Reference to OrganizationProvider")
    tenant: Optional[str] = Field(None, description="Reference to OrganizationTenant")


# ============================================================================
# Infrahub Location Models (from models/base/location.yml)
# ============================================================================


class InfrahubSite(BaseModel):
    """
    Infrahub LocationSite model.

    Maps to: models/base/location.yml -> LocationSite
    Namespace: Location
    """
    name: str = Field(..., description="Site name (unique)")
    description: Optional[str] = Field(None, description="Site description")
    city: Optional[str] = Field(None, description="City")
    address: Optional[str] = Field(None, description="Physical address")
    contact: Optional[str] = Field(None, description="Contact information")

    # Hierarchical relationship
    parent: Optional[str] = Field(None, description="Reference to LocationCountry")


class InfrahubRack(BaseModel):
    """
    Infrahub LocationRack model (if extended).

    Maps to: models/base/location.yml -> LocationRack (or custom extension)
    Namespace: Location
    """
    name: str = Field(..., description="Rack name (unique)")
    description: Optional[str] = Field(None, description="Rack description")
    height_u: int = Field(42, description="Rack height in U")

    # Hierarchical relationship
    parent: Optional[str] = Field(None, description="Reference to LocationSite")
    site: Optional[str] = Field(None, description="Reference to LocationSite")


# ============================================================================
# NetMapper to Infrahub Conversion Models
# ============================================================================


class InfrahubTopology(BaseModel):
    """
    Complete Infrahub topology representation.

    Contains all discovered infrastructure mapped to Infrahub models.
    """
    devices: List[InfrahubDevice] = Field(default_factory=list)
    interfaces: List[InfrahubInterface] = Field(default_factory=list)
    vlans: List[InfrahubVLAN] = Field(default_factory=list)
    ip_addresses: List[InfrahubIPAddress] = Field(default_factory=list)
    sites: List[InfrahubSite] = Field(default_factory=list)
    circuits: List[InfrahubCircuit] = Field(default_factory=list)

    # Metadata
    discovery_timestamp: Optional[str] = Field(None, description="Discovery timestamp")
    netmapper_version: str = Field("1.0.0", description="NetMapper version")
