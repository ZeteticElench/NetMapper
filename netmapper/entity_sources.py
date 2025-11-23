"""
Data source adapters for entity resolution.

Provides connectors to common enterprise systems to extract entity data:
- Active Directory
- AWS/Azure
- VMware vCenter
- Asset Management Systems
- Antivirus Software
- Mobile Device Management (MDM)
- Backup Software
- CMDB

Each adapter normalizes data into a standard format for entity resolution.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .entity_resolution import (
    EntityIdentifier,
    EntityAttribute,
    DataSource,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Base Source Adapter
# ============================================================================


class SourceAdapter:
    """Base class for data source adapters."""

    source_type: DataSource = DataSource.CUSTOM

    def extract_entities(self) -> List[Dict[str, Any]]:
        """
        Extract entities from data source.

        Returns:
            List of entity dictionaries with identifiers and attributes.
        """
        raise NotImplementedError

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw source data into standard entity format.

        Args:
            raw_data: Raw data from source.

        Returns:
            Normalized entity dict with:
            - source: DataSource
            - identifiers: List[EntityIdentifier]
            - attributes: Dict[str, Any]
            - timestamp: datetime
        """
        raise NotImplementedError


# ============================================================================
# Active Directory Adapter
# ============================================================================


class ActiveDirectoryAdapter(SourceAdapter):
    """
    Extract computer entities from Active Directory.

    Uses LDAP to query AD for computer objects and extract identifying attributes.
    """

    source_type = DataSource.ACTIVE_DIRECTORY

    def __init__(self, ldap_server: str, bind_dn: str, bind_password: str):
        """
        Initialize AD adapter.

        Args:
            ldap_server: LDAP server address.
            bind_dn: Bind DN for authentication.
            bind_password: Bind password.
        """
        self.ldap_server = ldap_server
        self.bind_dn = bind_dn
        self.bind_password = bind_password

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract computer objects from AD."""
        # This would use ldap3 or similar library
        # Simplified example:
        entities = []

        # Example AD computer attributes
        ad_computers = [
            {
                "cn": "SRV-WEB-01",
                "dNSHostName": "srv-web-01.corp.local",
                "operatingSystem": "Windows Server 2019",
                "operatingSystemVersion": "10.0 (17763)",
                "whenCreated": "20230101120000.0Z",
                "distinguishedName": "CN=SRV-WEB-01,OU=Servers,DC=corp,DC=local",
                "description": "Production web server",
            }
        ]

        for computer in ad_computers:
            entity = self.normalize_entity(computer)
            entities.append(entity)

        return entities

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AD computer object to entity format."""
        identifiers = []

        # Hostname from CN
        if "cn" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="hostname",
                    value=raw_data["cn"],
                    source=self.source_type,
                    confidence=0.95,
                )
            )

        # FQDN from dNSHostName
        if "dNSHostName" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="fqdn",
                    value=raw_data["dNSHostName"],
                    source=self.source_type,
                    confidence=1.0,
                )
            )

        # Attributes
        attributes = {
            "os_name": raw_data.get("operatingSystem"),
            "os_version": raw_data.get("operatingSystemVersion"),
            "ad_dn": raw_data.get("distinguishedName"),
            "description": raw_data.get("description"),
        }

        return {
            "source": self.source_type,
            "id": raw_data.get("cn"),
            "identifiers": [i.dict() for i in identifiers],
            "attributes": attributes,
            "timestamp": datetime.utcnow(),
        }


# ============================================================================
# AWS Adapter
# ============================================================================


class AWSAdapter(SourceAdapter):
    """
    Extract EC2 instance entities from AWS.

    Uses boto3 to query EC2 instances and extract metadata.
    """

    source_type = DataSource.AWS

    def __init__(self, region: str, access_key: str, secret_key: str):
        """
        Initialize AWS adapter.

        Args:
            region: AWS region.
            access_key: AWS access key.
            secret_key: AWS secret key.
        """
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract EC2 instances from AWS."""
        # This would use boto3
        # Simplified example:
        entities = []

        # Example EC2 instance
        instances = [
            {
                "InstanceId": "i-1234567890abcdef0",
                "PrivateIpAddress": "10.0.1.5",
                "PrivateDnsName": "ip-10-0-1-5.ec2.internal",
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "Tags": [
                    {"Key": "Name", "Value": "srv-web-01"},
                    {"Key": "Environment", "Value": "production"},
                ],
                "NetworkInterfaces": [
                    {
                        "MacAddress": "0a:12:34:56:78:90",
                        "PrivateIpAddress": "10.0.1.5",
                    }
                ],
            }
        ]

        for instance in instances:
            entity = self.normalize_entity(instance)
            entities.append(entity)

        return entities

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize EC2 instance to entity format."""
        identifiers = []

        # AWS instance ID
        if "InstanceId" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="aws_instance_id",
                    value=raw_data["InstanceId"],
                    source=self.source_type,
                    confidence=1.0,
                )
            )

        # Private IP
        if "PrivateIpAddress" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="ip_address",
                    value=raw_data["PrivateIpAddress"],
                    source=self.source_type,
                    confidence=0.8,
                )
            )

        # MAC address
        if "NetworkInterfaces" in raw_data:
            for ni in raw_data["NetworkInterfaces"]:
                if "MacAddress" in ni:
                    identifiers.append(
                        EntityIdentifier(
                            type="mac_address",
                            value=ni["MacAddress"],
                            source=self.source_type,
                            confidence=0.9,
                        )
                    )

        # Hostname from tags
        hostname = None
        if "Tags" in raw_data:
            for tag in raw_data["Tags"]:
                if tag.get("Key") == "Name":
                    hostname = tag.get("Value")
                    identifiers.append(
                        EntityIdentifier(
                            type="hostname",
                            value=hostname,
                            source=self.source_type,
                            confidence=0.9,
                        )
                    )
                    break

        # Attributes
        attributes = {
            "instance_type": raw_data.get("InstanceType"),
            "state": raw_data.get("State", {}).get("Name"),
            "region": self.region,
            "cloud_provider": "aws",
        }

        # Add tags as attributes
        if "Tags" in raw_data:
            for tag in raw_data["Tags"]:
                key = f"tag_{tag['Key'].lower()}"
                attributes[key] = tag["Value"]

        return {
            "source": self.source_type,
            "id": raw_data.get("InstanceId"),
            "identifiers": [i.dict() for i in identifiers],
            "attributes": attributes,
            "timestamp": datetime.utcnow(),
        }


# ============================================================================
# VMware vCenter Adapter
# ============================================================================


class VMwareAdapter(SourceAdapter):
    """
    Extract VM entities from VMware vCenter.

    Uses pyVmomi to query vCenter for virtual machines.
    """

    source_type = DataSource.VMWARE

    def __init__(self, vcenter_host: str, username: str, password: str):
        """
        Initialize vCenter adapter.

        Args:
            vcenter_host: vCenter server hostname.
            username: vCenter username.
            password: vCenter password.
        """
        self.vcenter_host = vcenter_host
        self.username = username
        self.password = password

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract VMs from vCenter."""
        # This would use pyVmomi
        # Simplified example:
        entities = []

        # Example VM
        vms = [
            {
                "name": "srv-web-01",
                "uuid": "420a1234-5678-90ab-cdef-1234567890ab",
                "guestHostName": "srv-web-01.corp.local",
                "guestIpAddress": "10.0.1.5",
                "powerState": "poweredOn",
                "guestFullName": "Microsoft Windows Server 2019 (64-bit)",
                "numCpu": 4,
                "memorySizeMB": 8192,
                "hardware": {
                    "device": [
                        {
                            "macAddress": "00:50:56:12:34:56",
                        }
                    ]
                },
            }
        ]

        for vm in vms:
            entity = self.normalize_entity(vm)
            entities.append(entity)

        return entities

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize vCenter VM to entity format."""
        identifiers = []

        # VMware UUID
        if "uuid" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="vmware_uuid",
                    value=raw_data["uuid"],
                    source=self.source_type,
                    confidence=1.0,
                )
            )

        # Hostname
        if "guestHostName" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="fqdn",
                    value=raw_data["guestHostName"],
                    source=self.source_type,
                    confidence=0.95,
                )
            )

        # IP address
        if "guestIpAddress" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="ip_address",
                    value=raw_data["guestIpAddress"],
                    source=self.source_type,
                    confidence=0.8,
                )
            )

        # MAC address
        if "hardware" in raw_data:
            for device in raw_data["hardware"].get("device", []):
                if "macAddress" in device:
                    identifiers.append(
                        EntityIdentifier(
                            type="mac_address",
                            value=device["macAddress"],
                            source=self.source_type,
                            confidence=0.95,
                        )
                    )

        # Attributes
        attributes = {
            "vm_name": raw_data.get("name"),
            "power_state": raw_data.get("powerState"),
            "guest_os": raw_data.get("guestFullName"),
            "num_cpu": raw_data.get("numCpu"),
            "memory_mb": raw_data.get("memorySizeMB"),
            "hypervisor": "vmware",
        }

        return {
            "source": self.source_type,
            "id": raw_data.get("uuid"),
            "identifiers": [i.dict() for i in identifiers],
            "attributes": attributes,
            "timestamp": datetime.utcnow(),
        }


# ============================================================================
# Asset Management Adapter
# ============================================================================


class AssetManagementAdapter(SourceAdapter):
    """
    Extract assets from inventory/asset management system.

    Example: ServiceNow CMDB, Snipe-IT, etc.
    """

    source_type = DataSource.ASSET_MANAGEMENT

    def __init__(self, api_url: str, api_key: str):
        """
        Initialize asset management adapter.

        Args:
            api_url: Asset management API URL.
            api_key: API authentication key.
        """
        self.api_url = api_url
        self.api_key = api_key

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract assets from system."""
        # This would use requests to call API
        # Simplified example:
        entities = []

        # Example asset
        assets = [
            {
                "asset_tag": "IT-12345",
                "name": "Web Server 01",
                "serial_number": "ABC123456",
                "manufacturer": "Dell",
                "model": "PowerEdge R640",
                "location": "DC-NYC-Rack-01-U42",
                "purchase_date": "2023-01-15",
                "warranty_expires": "2026-01-15",
                "assigned_to": "IT Operations",
            }
        ]

        for asset in assets:
            entity = self.normalize_entity(asset)
            entities.append(entity)

        return entities

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize asset to entity format."""
        identifiers = []

        # Asset tag
        if "asset_tag" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="asset_tag",
                    value=raw_data["asset_tag"],
                    source=self.source_type,
                    confidence=1.0,
                )
            )

        # Serial number
        if "serial_number" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="serial_number",
                    value=raw_data["serial_number"],
                    source=self.source_type,
                    confidence=1.0,
                )
            )

        # Hostname (fuzzy from name)
        if "name" in raw_data:
            # Try to extract hostname from name
            name = raw_data["name"].lower().replace(" ", "-")
            identifiers.append(
                EntityIdentifier(
                    type="hostname",
                    value=name,
                    source=self.source_type,
                    confidence=0.6,  # Low confidence, fuzzy match
                )
            )

        # Attributes
        attributes = {
            "manufacturer": raw_data.get("manufacturer"),
            "model": raw_data.get("model"),
            "location": raw_data.get("location"),
            "purchase_date": raw_data.get("purchase_date"),
            "warranty_expires": raw_data.get("warranty_expires"),
            "assigned_to": raw_data.get("assigned_to"),
        }

        return {
            "source": self.source_type,
            "id": raw_data.get("asset_tag"),
            "identifiers": [i.dict() for i in identifiers],
            "attributes": attributes,
            "timestamp": datetime.utcnow(),
        }


# ============================================================================
# Example: Complete Entity Resolution Workflow
# ============================================================================


def example_multi_source_resolution():
    """
    Example demonstrating complete entity resolution across multiple sources.

    Shows the same server appearing in:
    - NetMapper (discovered via CDP/LLDP)
    - Active Directory
    - AWS
    - VMware vCenter
    - Asset Management

    All get merged into a single canonical entity.
    """
    from .entity_resolution import EntityResolver, ConflictResolution

    # Initialize resolver
    resolver = EntityResolver("bolt://localhost:7687", "neo4j", "password")

    # Collect entities from all sources
    all_entities = []

    # 1. NetMapper discovered data
    netmapper_entity = {
        "source": DataSource.NETMAPPER,
        "id": "srv-web-01.corp.local",
        "identifiers": [
            {"type": "fqdn", "value": "srv-web-01.corp.local", "confidence": 1.0},
            {"type": "ip_address", "value": "10.0.1.5", "confidence": 1.0},
            {"type": "mac_address", "value": "00:50:56:12:34:56", "confidence": 1.0},
        ],
        "attributes": {
            "platform": "linux",
            "model": "Virtual Machine",
            "interfaces": 2,
        },
        "timestamp": datetime.utcnow(),
    }
    all_entities.append(netmapper_entity)

    # 2. Active Directory
    ad_adapter = ActiveDirectoryAdapter("ldap://dc.corp.local", "bind_dn", "password")
    ad_entities = ad_adapter.extract_entities()
    all_entities.extend(ad_entities)

    # 3. AWS
    aws_adapter = AWSAdapter("us-east-1", "access_key", "secret_key")
    aws_entities = aws_adapter.extract_entities()
    all_entities.extend(aws_entities)

    # 4. VMware
    vmware_adapter = VMwareAdapter("vcenter.corp.local", "admin", "password")
    vmware_entities = vmware_adapter.extract_entities()
    all_entities.extend(vmware_entities)

    # 5. Asset Management
    asset_adapter = AssetManagementAdapter("https://assets.corp.local/api", "api_key")
    asset_entities = asset_adapter.extract_entities()
    all_entities.extend(asset_entities)

    # Merge all entities
    canonical = resolver.merge_entities(
        all_entities,
        conflict_resolution=ConflictResolution.MOST_RECENT,
    )

    # Store canonical entity
    resolver.store_canonical_entity(canonical)

    print(f"Created canonical entity: {canonical.canonical_id}")
    print(f"Merged {len(all_entities)} source entities")
    print(f"Total identifiers: {len(canonical.identifiers)}")
    print(f"Unique attributes: {len(canonical.attributes)}")
    print(f"Conflicts: {len(canonical.conflicts)}")

    # Show lineage for a specific attribute
    if "hostname" in canonical.attributes:
        print("\nHostname lineage:")
        for attr in canonical.attributes["hostname"]:
            print(f"  {attr.value} from {attr.source} at {attr.timestamp}")

    resolver.close()


if __name__ == "__main__":
    example_multi_source_resolution()
