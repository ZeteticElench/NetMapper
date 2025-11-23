"""
Entity Resolution Framework for NetMapper.

Solves the critical problem of merging data from multiple sources (Active Directory,
inventory systems, AV software, MDM, AWS, vCenter, backup systems, etc.) where the
same physical or logical entity appears with different identifiers.

Example Problem:
    Same server appears as:
    - AD: "SRV-WEB-01.corp.local"
    - Inventory: "Web Server 01" (Serial: ABC123)
    - AWS: "i-1234567890abcdef0" (Private IP: 10.0.1.5)
    - vCenter: "srv-web-01" (UUID: 420a1234-5678-90ab-cdef-1234567890ab)
    - Backup: "SRV-WEB-01" (MAC: 00:50:56:12:34:56)
    - NetMapper: "srv-web-01.corp.local" (IP: 10.0.1.5)

Solution:
    Entity resolution creates a canonical entity that merges all data sources,
    tracking provenance and handling conflicts.
"""

import logging
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from difflib import SequenceMatcher

from pydantic import BaseModel, Field
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


# ============================================================================
# Entity Resolution Models
# ============================================================================


class DataSource(str, Enum):
    """Known data sources that can contribute entity data."""
    NETMAPPER = "netmapper"
    ACTIVE_DIRECTORY = "active_directory"
    INVENTORY_SYSTEM = "inventory_system"
    ANTIVIRUS = "antivirus"
    MDM = "mobile_device_management"
    AWS = "aws"
    AZURE = "azure"
    VMWARE = "vmware"
    BACKUP_SOFTWARE = "backup_software"
    MONITORING = "monitoring"
    CMDB = "cmdb"
    ASSET_MANAGEMENT = "asset_management"
    CUSTOM = "custom"


class MatchConfidence(str, Enum):
    """Confidence level for entity matches."""
    EXACT = "exact"           # 100% certain (same unique identifier)
    HIGH = "high"             # 90-99% (multiple strong matches)
    MEDIUM = "medium"         # 70-89% (some matches, needs review)
    LOW = "low"               # 50-69% (weak matches, likely false)
    UNCERTAIN = "uncertain"   # <50% (probably not a match)


class ConflictResolution(str, Enum):
    """Strategy for resolving conflicting attribute values."""
    PREFER_SOURCE = "prefer_source"           # Prefer specific source
    MOST_RECENT = "most_recent"               # Use most recently updated
    MOST_COMPLETE = "most_complete"           # Use most detailed value
    MANUAL_REVIEW = "manual_review"           # Require human decision
    AGGREGATE = "aggregate"                   # Combine all values
    VOTING = "voting"                         # Majority wins


class EntityIdentifier(BaseModel):
    """
    Identifier that can be used to match entities across sources.

    Examples:
    - hostname: "srv-web-01.corp.local"
    - ip_address: "10.0.1.5"
    - mac_address: "00:50:56:12:34:56"
    - serial_number: "ABC123456"
    - asset_tag: "IT-12345"
    - aws_instance_id: "i-1234567890abcdef0"
    - vmware_uuid: "420a1234-5678-90ab-cdef-1234567890ab"
    """
    type: str = Field(..., description="Identifier type (hostname, ip, mac, serial, etc.)")
    value: str = Field(..., description="Identifier value")
    source: DataSource = Field(..., description="Data source that provided this identifier")
    confidence: float = Field(1.0, description="Confidence in identifier accuracy (0.0-1.0)")
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class EntityAttribute(BaseModel):
    """
    Single attribute value from a data source with provenance.

    Tracks where data came from and when, enabling conflict resolution.
    """
    name: str = Field(..., description="Attribute name (e.g., 'os_version', 'location')")
    value: Any = Field(..., description="Attribute value")
    source: DataSource = Field(..., description="Data source")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(1.0, description="Confidence in value accuracy (0.0-1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityMatch(BaseModel):
    """
    Potential match between entities from different sources.

    Tracks matching criteria and confidence score.
    """
    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")
    confidence: MatchConfidence = Field(..., description="Match confidence")
    score: float = Field(..., description="Numeric match score (0.0-1.0)")

    # Matching evidence
    matched_identifiers: List[str] = Field(
        default_factory=list,
        description="Identifiers that matched (hostname, ip, mac, etc.)"
    )
    matched_attributes: List[str] = Field(
        default_factory=list,
        description="Attributes that matched (model, serial, etc.)"
    )

    # Decision tracking
    reviewed: bool = Field(False, description="Has been manually reviewed")
    confirmed: Optional[bool] = Field(None, description="Match confirmed by human")
    reviewed_by: Optional[str] = Field(None, description="User who reviewed")
    reviewed_at: Optional[datetime] = Field(None, description="Review timestamp")


class CanonicalEntity(BaseModel):
    """
    Canonical entity created by merging multiple data sources.

    Represents the "single source of truth" for an entity, with full
    provenance tracking for every attribute.
    """
    canonical_id: str = Field(..., description="Unique canonical entity ID")
    entity_type: str = Field(..., description="Entity type (device, user, application, etc.)")

    # All identifiers from all sources
    identifiers: List[EntityIdentifier] = Field(default_factory=list)

    # Merged attributes with provenance
    attributes: Dict[str, List[EntityAttribute]] = Field(
        default_factory=dict,
        description="Attribute name -> list of values from different sources"
    )

    # Source entity references
    source_entities: Dict[DataSource, str] = Field(
        default_factory=dict,
        description="Source -> entity ID in that source"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(1.0, description="Overall entity confidence")

    # Conflict tracking
    conflicts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Unresolved attribute conflicts"
    )


# ============================================================================
# Entity Resolution Engine
# ============================================================================


class EntityResolver:
    """
    Entity resolution engine for merging multi-source data.

    Performs fuzzy matching across identifiers, merges attributes with
    conflict resolution, and maintains data lineage.
    """

    # Identifier weights for matching
    IDENTIFIER_WEIGHTS = {
        "serial_number": 1.0,      # Exact match = definite match
        "asset_tag": 1.0,
        "uuid": 1.0,
        "aws_instance_id": 1.0,
        "vmware_uuid": 1.0,
        "mac_address": 0.9,        # Strong but can change
        "ip_address": 0.7,         # Medium (DHCP can reassign)
        "hostname": 0.8,           # Strong but can be renamed
        "fqdn": 0.8,
        "email": 0.9,
        "username": 0.8,
    }

    # Minimum score thresholds
    EXACT_THRESHOLD = 1.0
    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7
    LOW_THRESHOLD = 0.5

    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        """
        Initialize entity resolver.

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

    def find_matches(
        self,
        entity_identifiers: List[EntityIdentifier],
        candidate_pool: Optional[List[str]] = None,
    ) -> List[EntityMatch]:
        """
        Find potential matches for an entity based on identifiers.

        Args:
            entity_identifiers: List of identifiers for the entity.
            candidate_pool: Optional list of canonical entity IDs to search.
                           If None, searches all entities.

        Returns:
            List of potential matches sorted by confidence.

        Example:
            >>> identifiers = [
            ...     EntityIdentifier(type="hostname", value="srv-web-01", source=DataSource.NETMAPPER),
            ...     EntityIdentifier(type="ip_address", value="10.0.1.5", source=DataSource.NETMAPPER),
            ...     EntityIdentifier(type="mac_address", value="00:50:56:12:34:56", source=DataSource.NETMAPPER),
            ... ]
            >>> matches = resolver.find_matches(identifiers)
            >>> for match in matches:
            ...     print(f"{match.entity2_id}: {match.confidence} ({match.score:.2f})")
        """
        matches = []

        # Query Neo4j for entities with matching identifiers
        query = """
        MATCH (e:CanonicalEntity)
        WHERE e.canonical_id IN $candidates OR $candidates IS NULL
        WITH e
        UNWIND e.identifiers AS identifier
        WHERE identifier.value IN $identifier_values
        RETURN DISTINCT
            e.canonical_id as entity_id,
            collect(identifier) as matched_identifiers,
            e as entity
        """

        identifier_values = [ident.value for ident in entity_identifiers]

        with self.driver.session() as session:
            result = session.run(
                query,
                identifier_values=identifier_values,
                candidates=candidate_pool,
            )

            for record in result:
                entity_id = record["entity_id"]
                matched = record["matched_identifiers"]

                # Calculate match score
                score = self._calculate_match_score(
                    entity_identifiers,
                    matched,
                )

                # Determine confidence level
                if score >= self.EXACT_THRESHOLD:
                    confidence = MatchConfidence.EXACT
                elif score >= self.HIGH_THRESHOLD:
                    confidence = MatchConfidence.HIGH
                elif score >= self.MEDIUM_THRESHOLD:
                    confidence = MatchConfidence.MEDIUM
                elif score >= self.LOW_THRESHOLD:
                    confidence = MatchConfidence.LOW
                else:
                    confidence = MatchConfidence.UNCERTAIN

                match = EntityMatch(
                    entity1_id="new_entity",  # Placeholder
                    entity2_id=entity_id,
                    confidence=confidence,
                    score=score,
                    matched_identifiers=[m["type"] for m in matched],
                )
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _calculate_match_score(
        self,
        identifiers1: List[EntityIdentifier],
        identifiers2: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate match score between two sets of identifiers.

        Uses weighted scoring based on identifier type and quality.

        Args:
            identifiers1: First set of identifiers.
            identifiers2: Second set of identifiers (as dicts from Neo4j).

        Returns:
            Match score (0.0-1.0).
        """
        # Build lookup maps
        ident1_map = {(i.type, i.value.lower()): i for i in identifiers1}
        ident2_map = {(i["type"], i["value"].lower()): i for i in identifiers2}

        total_weight = 0.0
        matched_weight = 0.0

        # Check exact matches
        for (type1, value1), ident1 in ident1_map.items():
            weight = self.IDENTIFIER_WEIGHTS.get(type1, 0.5)
            total_weight += weight

            if (type1, value1) in ident2_map:
                # Exact match
                matched_weight += weight * ident1.confidence
            else:
                # Check fuzzy match for hostnames
                if type1 in ["hostname", "fqdn"]:
                    for (type2, value2), ident2 in ident2_map.items():
                        if type2 == type1:
                            similarity = self._string_similarity(value1, value2)
                            if similarity > 0.8:
                                matched_weight += weight * similarity * ident1.confidence
                                break

        if total_weight == 0:
            return 0.0

        return min(matched_weight / total_weight, 1.0)

    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def merge_entities(
        self,
        entities: List[Dict[str, Any]],
        conflict_resolution: ConflictResolution = ConflictResolution.MOST_RECENT,
    ) -> CanonicalEntity:
        """
        Merge multiple source entities into a canonical entity.

        Args:
            entities: List of entity data from different sources.
            conflict_resolution: Strategy for resolving conflicts.

        Returns:
            Canonical entity with merged data.

        Example:
            >>> entities = [
            ...     {
            ...         "source": DataSource.NETMAPPER,
            ...         "identifiers": [...],
            ...         "attributes": {"hostname": "srv-web-01", "ip": "10.0.1.5"}
            ...     },
            ...     {
            ...         "source": DataSource.AWS,
            ...         "identifiers": [...],
            ...         "attributes": {"instance_id": "i-123", "ip": "10.0.1.5", "region": "us-east-1"}
            ...     },
            ... ]
            >>> canonical = resolver.merge_entities(entities)
        """
        import uuid

        canonical_id = f"canonical-{uuid.uuid4()}"

        canonical = CanonicalEntity(
            canonical_id=canonical_id,
            entity_type="device",  # Could be inferred or specified
        )

        # Merge identifiers
        all_identifiers = []
        for entity in entities:
            source = entity.get("source", DataSource.CUSTOM)
            for ident in entity.get("identifiers", []):
                all_identifiers.append(
                    EntityIdentifier(
                        type=ident["type"],
                        value=ident["value"],
                        source=source,
                        confidence=ident.get("confidence", 1.0),
                    )
                )
        canonical.identifiers = all_identifiers

        # Merge attributes
        for entity in entities:
            source = entity.get("source", DataSource.CUSTOM)
            timestamp = entity.get("timestamp", datetime.utcnow())

            for attr_name, attr_value in entity.get("attributes", {}).items():
                if attr_name not in canonical.attributes:
                    canonical.attributes[attr_name] = []

                canonical.attributes[attr_name].append(
                    EntityAttribute(
                        name=attr_name,
                        value=attr_value,
                        source=source,
                        timestamp=timestamp,
                    )
                )

        # Resolve conflicts
        canonical = self._resolve_conflicts(canonical, conflict_resolution)

        # Track source entities
        for entity in entities:
            source = entity.get("source")
            entity_id = entity.get("id")
            if source and entity_id:
                canonical.source_entities[source] = entity_id

        return canonical

    def _resolve_conflicts(
        self,
        canonical: CanonicalEntity,
        strategy: ConflictResolution,
    ) -> CanonicalEntity:
        """
        Resolve attribute conflicts using specified strategy.

        Args:
            canonical: Canonical entity with potential conflicts.
            strategy: Conflict resolution strategy.

        Returns:
            Canonical entity with resolved conflicts.
        """
        for attr_name, attr_values in canonical.attributes.items():
            if len(attr_values) <= 1:
                continue  # No conflict

            # Get unique values
            unique_values = list(set(av.value for av in attr_values))
            if len(unique_values) == 1:
                continue  # All sources agree

            # Conflict exists
            if strategy == ConflictResolution.MOST_RECENT:
                # Keep most recent value
                attr_values.sort(key=lambda av: av.timestamp, reverse=True)
                canonical.attributes[attr_name] = [attr_values[0]]

            elif strategy == ConflictResolution.MOST_COMPLETE:
                # Keep most detailed value
                attr_values.sort(key=lambda av: len(str(av.value)), reverse=True)
                canonical.attributes[attr_name] = [attr_values[0]]

            elif strategy == ConflictResolution.AGGREGATE:
                # Keep all values
                pass  # Already have all

            elif strategy == ConflictResolution.MANUAL_REVIEW:
                # Flag for review
                canonical.conflicts.append({
                    "attribute": attr_name,
                    "values": [
                        {
                            "value": av.value,
                            "source": av.source,
                            "timestamp": av.timestamp.isoformat(),
                        }
                        for av in attr_values
                    ],
                })

        return canonical

    def store_canonical_entity(self, entity: CanonicalEntity):
        """
        Store canonical entity in Neo4j.

        Args:
            entity: Canonical entity to store.
        """
        query = """
        MERGE (e:CanonicalEntity {canonical_id: $canonical_id})
        SET e.entity_type = $entity_type,
            e.identifiers = $identifiers,
            e.attributes = $attributes,
            e.source_entities = $source_entities,
            e.created_at = datetime($created_at),
            e.updated_at = datetime($updated_at),
            e.confidence = $confidence,
            e.conflicts = $conflicts
        RETURN e
        """

        with self.driver.session() as session:
            session.run(
                query,
                canonical_id=entity.canonical_id,
                entity_type=entity.entity_type,
                identifiers=[i.dict() for i in entity.identifiers],
                attributes={
                    k: [av.dict() for av in v]
                    for k, v in entity.attributes.items()
                },
                source_entities=entity.source_entities,
                created_at=entity.created_at.isoformat(),
                updated_at=entity.updated_at.isoformat(),
                confidence=entity.confidence,
                conflicts=entity.conflicts,
            )

        logger.info(f"Stored canonical entity: {entity.canonical_id}")
