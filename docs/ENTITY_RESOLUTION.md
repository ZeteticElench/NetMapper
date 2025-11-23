# Entity Resolution for Multi-Source Infrastructure Data

## The Problem

When merging infrastructure data from multiple sources into a unified graph database, **the same physical or logical entity appears with different identifiers, attributes, and metadata across systems**. This creates critical challenges:

### Real-World Scenario

A single production server might appear as:

**Active Directory**:
```yaml
cn: SRV-WEB-01
dNSHostName: srv-web-01.corp.local
operatingSystem: Windows Server 2019
distinguishedName: CN=SRV-WEB-01,OU=Servers,DC=corp,DC=local
```

**AWS EC2**:
```yaml
InstanceId: i-1234567890abcdef0
Tags:
  - Name: srv-web-01
PrivateIpAddress: 10.0.1.5
MacAddress: 0a:12:34:56:78:90
InstanceType: t3.medium
```

**VMware vCenter**:
```yaml
name: srv-web-01
uuid: 420a1234-5678-90ab-cdef-1234567890ab
guestHostName: srv-web-01.corp.local
guestIpAddress: 10.0.1.5
macAddress: 00:50:56:12:34:56
```

**Asset Management System**:
```yaml
asset_tag: IT-12345
name: Web Server 01
serial_number: ABC123456
manufacturer: Dell
model: PowerEdge R640
location: DC-NYC-Rack-01-U42
```

**Antivirus Console**:
```yaml
hostname: srv-web-01
ip_address: 10.0.1.5
last_scan: 2024-11-20
av_version: 10.5.3
threats_detected: 0
```

**Backup Software**:
```yaml
client_name: SRV-WEB-01.CORP.LOCAL
ip: 10.0.1.5
last_backup: 2024-11-22
backup_size_gb: 250
```

### The Challenge

Without entity resolution, you get:
- **6 separate nodes** in Neo4j for the same server
- **Fragmented data**: Each system has partial view
- **No unified truth**: Can't answer "what's the backup status of this AWS instance?"
- **Duplicate counts**: Inventory reports show 6 servers instead of 1
- **Broken relationships**: Cannot trace connections across data sources

## NetMapper's Solution

NetMapper's entity resolution framework solves this through:

1. **Weighted Identifier Matching**: Different identifiers have different reliability
2. **Confidence Scoring**: Quantifies match certainty
3. **Conflict Resolution**: Handles contradictory data from sources
4. **Data Lineage**: Tracks provenance of every attribute
5. **Canonical Entities**: Creates unified "golden record" per entity

## Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Active    │  │     AWS     │  │   VMware    │  │    Asset    │
│  Directory  │  │     EC2     │  │   vCenter   │  │  Management │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │                │
       └────────────────┴────────────────┴────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Source Adapters     │
                  │  (Normalization)     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Entity Identifiers  │
                  │  - Hostname          │
                  │  - IP Address        │
                  │  - MAC Address       │
                  │  - Serial Number     │
                  │  - UUIDs             │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  EntityResolver      │
                  │  - Match Finding     │
                  │  - Confidence Score  │
                  │  - Merge Logic       │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Canonical Entity    │
                  │  (Golden Record)     │
                  │  - All Identifiers   │
                  │  - Merged Attributes │
                  │  - Full Lineage      │
                  │  - Conflicts Flagged │
                  └──────────────────────┘
```

## Identifier Matching System

### Identifier Weights

Different identifiers have different reliability for matching:

| Identifier Type | Weight | Rationale |
|----------------|--------|-----------|
| **serial_number** | 1.0 | Hardware serial numbers are globally unique and permanent |
| **asset_tag** | 1.0 | Inventory tags are unique within organization |
| **vmware_uuid** | 1.0 | Hypervisor UUIDs are permanent per VM |
| **aws_instance_id** | 1.0 | Cloud instance IDs are permanent |
| **mac_address** | 0.9 | Usually permanent but can be spoofed or virtual |
| **hostname** | 0.8 | Can be changed but usually stable |
| **ip_address** | 0.7 | Can be reassigned (DHCP) but often stable |
| **fqdn** | 0.85 | More stable than simple hostname |

### Matching Algorithm

```python
def calculate_match_score(entity1_identifiers, entity2_identifiers):
    """
    Calculate weighted match score between two entities.

    Returns:
        score: 0.0 to 1.0 (0 = no match, 1.0 = definite match)
    """

    total_weight = 0.0
    matched_weight = 0.0

    for id1 in entity1_identifiers:
        for id2 in entity2_identifiers:
            if id1.type == id2.type:
                weight = IDENTIFIER_WEIGHTS.get(id1.type, 0.5)
                total_weight += weight

                # Exact match
                if id1.value.lower() == id2.value.lower():
                    matched_weight += weight

                # Fuzzy match for hostnames
                elif id1.type in ["hostname", "fqdn"]:
                    similarity = fuzzy_match(id1.value, id2.value)
                    matched_weight += weight * similarity

    return matched_weight / total_weight if total_weight > 0 else 0.0
```

### Confidence Levels

| Confidence | Score Range | Meaning |
|-----------|-------------|---------|
| **EXACT** | 1.0 | Perfect match (e.g., matching serial numbers) |
| **HIGH** | 0.8 - 0.99 | Very likely same entity (multiple strong identifiers) |
| **MEDIUM** | 0.6 - 0.79 | Probable match (hostname + IP match) |
| **LOW** | 0.4 - 0.59 | Possible match (only IP address match) |
| **UNCERTAIN** | < 0.4 | Insufficient evidence (requires manual review) |

## Conflict Resolution

When merging entities, attributes from different sources may conflict.

### Resolution Strategies

#### 1. PREFER_SOURCE

Prefer data from specific sources based on reliability:

```python
# Example: Trust asset management for hardware details
SOURCE_PRIORITY = {
    "serial_number": [DataSource.ASSET_MANAGEMENT, DataSource.VMWARE],
    "ip_address": [DataSource.NETMAPPER, DataSource.AWS, DataSource.ACTIVE_DIRECTORY],
    "os_version": [DataSource.ACTIVE_DIRECTORY, DataSource.VMWARE, DataSource.AWS],
}
```

**Use Case**: Hardware details are most accurate in asset management system.

#### 2. MOST_RECENT

Use the most recently updated value:

```python
# Example: IP addresses change frequently
attributes["ip_address"] = max(
    ip_values,
    key=lambda x: x.timestamp
)
```

**Use Case**: Network configuration that changes over time.

#### 3. MOST_COMPLETE

Use the most detailed/complete value:

```python
# Example: Use longest description
attributes["description"] = max(
    descriptions,
    key=lambda x: len(x.value) if x.value else 0
)
```

**Use Case**: Descriptive fields where more detail is better.

#### 4. MANUAL_REVIEW

Flag conflicts for human review:

```python
if len(conflicting_values) > 1:
    canonical.conflicts.append(
        AttributeConflict(
            attribute="os_version",
            values=conflicting_values,
            recommendation="Please verify OS version"
        )
    )
```

**Use Case**: Critical attributes where accuracy is essential.

#### 5. AGGREGATE

Combine all values:

```python
# Example: Collect all tags from all sources
all_tags = set()
for source in sources:
    all_tags.update(source.get("tags", []))
attributes["tags"] = list(all_tags)
```

**Use Case**: Tags, labels, or categories from multiple sources.

#### 6. VOTING

Use most common value across sources:

```python
# Example: Status reported by multiple systems
from collections import Counter
status_votes = Counter([s["status"] for s in sources])
attributes["status"] = status_votes.most_common(1)[0][0]
```

**Use Case**: Status fields where majority is likely correct.

## Data Lineage and Provenance

Every attribute in a canonical entity tracks its origin:

```python
class EntityAttribute(BaseModel):
    """Attribute with full provenance tracking."""

    value: Any
    source: DataSource
    timestamp: datetime
    confidence: float

    # Provenance metadata
    source_id: str           # Original source record ID
    extracted_by: str        # Adapter that extracted it
    extraction_time: datetime

    # Quality metadata
    is_validated: bool
    validation_method: Optional[str]
```

### Example: Lineage for Hostname

```yaml
canonical_entity:
  canonical_id: "server-xyz-canonical"

  attributes:
    hostname:
      - value: "SRV-WEB-01"
        source: ACTIVE_DIRECTORY
        timestamp: 2024-11-20T10:00:00Z
        confidence: 0.95
        source_id: "CN=SRV-WEB-01,OU=Servers,DC=corp,DC=local"

      - value: "srv-web-01"
        source: AWS
        timestamp: 2024-11-22T15:30:00Z
        confidence: 0.90
        source_id: "i-1234567890abcdef0"

      - value: "srv-web-01.corp.local"
        source: VMWARE
        timestamp: 2024-11-21T08:00:00Z
        confidence: 0.95
        source_id: "420a1234-5678-90ab-cdef-1234567890ab"
```

This allows answering questions like:
- "Where did this IP address come from?"
- "When was this value last updated?"
- "Which sources agree on this attribute?"
- "What's the most recent data for this field?"

## Source Adapters

### Available Adapters

NetMapper includes adapters for common enterprise systems:

1. **ActiveDirectoryAdapter**: LDAP computer objects
2. **AWSAdapter**: EC2 instances
3. **AzureAdapter**: Azure VMs (planned)
4. **VMwareAdapter**: vCenter virtual machines
5. **AssetManagementAdapter**: Inventory systems (ServiceNow, Snipe-IT)
6. **AntivirusAdapter**: AV consoles (planned)
7. **MDMAdapter**: Mobile Device Management (planned)
8. **BackupAdapter**: Backup software (planned)

### Adapter Interface

All adapters implement:

```python
class SourceAdapter:
    """Base class for data source adapters."""

    source_type: DataSource

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Extract entities from data source."""
        raise NotImplementedError

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw source data into standard entity format.

        Returns:
            {
                "source": DataSource,
                "id": str,
                "identifiers": List[EntityIdentifier],
                "attributes": Dict[str, Any],
                "timestamp": datetime
            }
        """
        raise NotImplementedError
```

### Creating Custom Adapters

Example adapter for custom CMDB:

```python
from netmapper.entity_sources import SourceAdapter
from netmapper.entity_resolution import EntityIdentifier, DataSource

class CustomCMDBAdapter(SourceAdapter):
    """Extract assets from custom CMDB."""

    source_type = DataSource.CUSTOM

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key

    def extract_entities(self) -> List[Dict[str, Any]]:
        """Query CMDB API and extract assets."""
        import requests

        response = requests.get(
            f"{self.api_url}/assets",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        entities = []
        for asset in response.json():
            entity = self.normalize_entity(asset)
            entities.append(entity)

        return entities

    def normalize_entity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CMDB asset to standard format."""
        identifiers = []

        # Extract identifiers from CMDB fields
        if "hostname" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="hostname",
                    value=raw_data["hostname"],
                    source=self.source_type,
                    confidence=0.9
                )
            )

        if "serial" in raw_data:
            identifiers.append(
                EntityIdentifier(
                    type="serial_number",
                    value=raw_data["serial"],
                    source=self.source_type,
                    confidence=1.0
                )
            )

        return {
            "source": self.source_type,
            "id": raw_data["asset_id"],
            "identifiers": [i.dict() for i in identifiers],
            "attributes": {
                "manufacturer": raw_data.get("manufacturer"),
                "model": raw_data.get("model"),
                "location": raw_data.get("location"),
            },
            "timestamp": datetime.utcnow()
        }
```

## Usage Examples

### Example 1: Basic Multi-Source Resolution

```python
from netmapper.entity_resolution import EntityResolver, ConflictResolution
from netmapper.entity_sources import (
    ActiveDirectoryAdapter,
    AWSAdapter,
    VMwareAdapter
)

# Initialize resolver
resolver = EntityResolver(
    "bolt://localhost:7687",
    "neo4j",
    "password"
)

# Collect entities from all sources
all_entities = []

# Active Directory
ad_adapter = ActiveDirectoryAdapter("ldap://dc.corp.local", "bind_dn", "password")
all_entities.extend(ad_adapter.extract_entities())

# AWS
aws_adapter = AWSAdapter("us-east-1", "access_key", "secret_key")
all_entities.extend(aws_adapter.extract_entities())

# VMware
vmware_adapter = VMwareAdapter("vcenter.corp.local", "admin", "password")
all_entities.extend(vmware_adapter.extract_entities())

# Merge into canonical entity
canonical = resolver.merge_entities(
    all_entities,
    conflict_resolution=ConflictResolution.MOST_RECENT
)

# Store in Neo4j
resolver.store_canonical_entity(canonical)

print(f"Created canonical entity: {canonical.canonical_id}")
print(f"Merged {len(all_entities)} source entities")
print(f"Total identifiers: {len(canonical.identifiers)}")
print(f"Conflicts requiring review: {len(canonical.conflicts)}")

resolver.close()
```

### Example 2: Finding Matches for New Entity

```python
# New entity from backup software
new_entity_identifiers = [
    EntityIdentifier(
        type="hostname",
        value="srv-web-01.corp.local",
        source=DataSource.CUSTOM,
        confidence=0.9
    ),
    EntityIdentifier(
        type="ip_address",
        value="10.0.1.5",
        source=DataSource.CUSTOM,
        confidence=0.8
    )
]

# Find matches in existing canonical entities
matches = resolver.find_matches(new_entity_identifiers)

for match in matches:
    print(f"Found match: {match.canonical_id}")
    print(f"  Confidence: {match.confidence}")
    print(f"  Matched identifiers: {match.matched_identifiers}")
```

### Example 3: Querying Lineage

```python
# Get canonical entity
canonical = resolver.get_canonical_entity("server-xyz-canonical")

# Show lineage for specific attribute
if "ip_address" in canonical.attributes:
    print("IP Address lineage:")
    for attr in canonical.attributes["ip_address"]:
        print(f"  {attr.value}")
        print(f"    Source: {attr.source}")
        print(f"    Updated: {attr.timestamp}")
        print(f"    Confidence: {attr.confidence}")
```

### Example 4: Conflict Review

```python
# Get all canonical entities with conflicts
entities_with_conflicts = resolver.get_entities_with_conflicts()

for entity in entities_with_conflicts:
    print(f"\nEntity: {entity.canonical_id}")

    for conflict in entity.conflicts:
        print(f"  Conflict in: {conflict.attribute}")
        print(f"  Values:")
        for value in conflict.values:
            print(f"    - {value.value} (from {value.source} at {value.timestamp})")
        print(f"  Recommendation: {conflict.recommendation}")
```

## Neo4j Storage Model

### Canonical Entity Node

```cypher
CREATE (e:CanonicalEntity {
  canonical_id: "server-xyz-canonical",
  entity_type: "computer",
  created_at: datetime("2024-11-23T10:00:00Z"),
  updated_at: datetime("2024-11-23T10:00:00Z"),
  confidence: 0.95,
  has_conflicts: false
})
```

### Source Entity Relationship

```cypher
MATCH (canonical:CanonicalEntity {canonical_id: "server-xyz-canonical"})
MATCH (source:NetworkDevice {hostname: "srv-web-01.corp.local"})
CREATE (canonical)-[:MERGED_FROM {
  source_type: "NETMAPPER",
  timestamp: datetime("2024-11-23T10:00:00Z"),
  confidence: 0.95
}]->(source)
```

### Identifier Index

```cypher
CREATE (id:EntityIdentifier {
  type: "hostname",
  value: "srv-web-01.corp.local",
  canonical_id: "server-xyz-canonical"
})

CREATE INDEX entity_identifier_index FOR (n:EntityIdentifier) ON (n.type, n.value)
```

### Querying Merged Entities

```cypher
// Find canonical entity by any identifier
MATCH (id:EntityIdentifier {type: "ip_address", value: "10.0.1.5"})
MATCH (canonical:CanonicalEntity {canonical_id: id.canonical_id})
MATCH (canonical)-[:MERGED_FROM]->(sources)
RETURN canonical, sources

// Find all sources for a canonical entity
MATCH (canonical:CanonicalEntity {canonical_id: "server-xyz-canonical"})
MATCH (canonical)-[r:MERGED_FROM]->(sources)
RETURN sources.hostname, r.source_type, r.timestamp
```

## Best Practices

### 1. Start with High-Confidence Identifiers

Begin matching with unique identifiers:
- Serial numbers
- Asset tags
- Cloud instance IDs
- Hypervisor UUIDs

### 2. Use Conservative Thresholds

Set minimum confidence thresholds:
```python
MIN_AUTO_MERGE_CONFIDENCE = 0.8  # Only auto-merge high confidence
MIN_SUGGEST_MATCH = 0.6          # Suggest below 0.8
REQUIRE_MANUAL_REVIEW = 0.4      # Manual review below 0.6
```

### 3. Prefer Source Priority for Critical Attributes

```python
# Trust authoritative sources
ATTRIBUTE_SOURCES = {
    "serial_number": DataSource.ASSET_MANAGEMENT,
    "warranty_expires": DataSource.ASSET_MANAGEMENT,
    "ip_address": DataSource.NETMAPPER,  # Network discovery is authoritative
    "os_version": DataSource.ACTIVE_DIRECTORY,
}
```

### 4. Track Match History

Store match decisions for audit trail:
```python
canonical.match_history.append({
    "timestamp": datetime.utcnow(),
    "action": "merged",
    "source_entity_id": "i-1234567890abcdef0",
    "confidence": 0.95,
    "matched_by": ["hostname", "ip_address", "mac_address"],
    "operator": "auto" / "manual:admin@corp.local"
})
```

### 5. Regular Re-Resolution

Re-run entity resolution periodically:
- After bulk imports from new sources
- When identifier data changes significantly
- To catch previously low-confidence matches that now have more data

### 6. Human-in-the-Loop for Edge Cases

Always flag for manual review:
- Confidence < 0.6
- Conflicting critical attributes (different serial numbers)
- Merging >5 source entities
- First-time matches from new data sources

## Performance Considerations

### Indexing Strategy

```python
# Create indexes on identifier types
CREATE INDEX entity_id_hostname FOR (n:EntityIdentifier) ON (n.type, n.value) WHERE n.type = "hostname"
CREATE INDEX entity_id_ip FOR (n:EntityIdentifier) ON (n.type, n.value) WHERE n.type = "ip_address"
CREATE INDEX entity_id_mac FOR (n:EntityIdentifier) ON (n.type, n.value) WHERE n.type = "mac_address"
CREATE INDEX entity_id_serial FOR (n:EntityIdentifier) ON (n.type, n.value) WHERE n.type = "serial_number"
```

### Batch Processing

Process entities in batches:
```python
BATCH_SIZE = 100

for i in range(0, len(all_entities), BATCH_SIZE):
    batch = all_entities[i:i+BATCH_SIZE]
    for entity in batch:
        matches = resolver.find_matches(entity["identifiers"])
        # Process matches...
```

### Caching

Cache frequently accessed canonical entities:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_canonical_entity(canonical_id: str):
    return resolver.get_canonical_entity(canonical_id)
```

## Troubleshooting

### Issue: Too Many False Positives

**Symptoms**: Unrelated entities being merged

**Solutions**:
1. Increase minimum confidence threshold
2. Add more unique identifiers to matching
3. Exclude low-weight identifiers (like IP addresses in DHCP environments)
4. Use stricter fuzzy matching thresholds

### Issue: Missing Matches

**Symptoms**: Same entity appearing as multiple canonical entities

**Solutions**:
1. Lower confidence threshold temporarily
2. Check identifier normalization (case sensitivity, whitespace)
3. Add fuzzy matching for more identifier types
4. Review source adapter identifier extraction logic

### Issue: Conflicting Attributes

**Symptoms**: Many conflicts requiring manual review

**Solutions**:
1. Implement source priority for specific attributes
2. Use MOST_RECENT strategy for frequently-changing data
3. Increase trust in authoritative sources
4. Validate source data quality before import

### Issue: Performance Degradation

**Symptoms**: Slow match finding with large datasets

**Solutions**:
1. Verify Neo4j indexes are created
2. Use batch processing
3. Implement caching for canonical entities
4. Consider partitioning by entity type
5. Use Bloom filters for quick rejection of non-matches

## Integration with NetMapper

### Workflow Integration

```
NetMapper Discovery
       ↓
  Neo4j Storage
       ↓
Entity Resolution
       ↓
Canonical Entities
       ↓
   ┌───┴───┐
   ↓       ↓
Infrahub  GUI
 Export  Display
```

### GUI Integration (Future)

Planned GUI features:
- Visual entity matching review interface
- Side-by-side comparison of source entities
- Conflict resolution workflow
- Match confidence visualization
- Lineage timeline view

### API Integration

```python
# RESTful API endpoint (planned)
GET /api/canonical-entities/{id}
GET /api/canonical-entities/{id}/lineage/{attribute}
GET /api/canonical-entities/conflicts
POST /api/canonical-entities/{id}/resolve-conflict
```

## Future Enhancements

- [ ] Machine learning-based match scoring
- [ ] Automatic identifier weight tuning based on historical accuracy
- [ ] Graph-based entity clustering (community detection)
- [ ] Real-time conflict notification
- [ ] Blockchain-based provenance tracking
- [ ] Integration with data quality frameworks
- [ ] Automated data validation rules
- [ ] GUI for match review and conflict resolution

## References

### Academic Research

- **Entity Resolution**: P. Christen, "Data Matching", Springer, 2012
- **Record Linkage**: I. P. Fellegi and A. B. Sunter, "A Theory for Record Linkage", JASA, 1969
- **Fuzzy Matching**: Cohen, W. W., et al. "A Comparison of String Metrics for Matching Names and Records"

### Related Tools

- **Dedupe.io**: Machine learning-based deduplication
- **RecordLinkage (Python)**: Record linkage toolkit
- **Apache Nifi**: Data flow with entity resolution processors

### NetMapper Documentation

- `netmapper/entity_resolution.py` - Core resolution engine
- `netmapper/entity_sources.py` - Source adapters
- `docs/CIM_INTEGRATION.md` - CIM relationship types
- `docs/INFRAHUB_INTEGRATION.md` - Infrahub export integration

---

**License**: Same as NetMapper core project
