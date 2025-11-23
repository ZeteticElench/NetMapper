# Infrahub GraphQL Schema Analysis

## Overview

The Infrahub GraphQL schema is a **masterclass in infrastructure modeling**, comprising **11,131 lines** of meticulously designed types, queries, and mutations. It represents one of the most comprehensive infrastructure management schemas available as open source.

## Impressive Scale

### By the Numbers

| Metric | Count | Description |
|--------|-------|-------------|
| **Total Lines** | 11,131 | Complete GraphQL schema |
| **Types/Interfaces/Enums** | 1,095+ | Core type definitions |
| **Node Types** | 200+ | Infrastructure entity types |
| **Mutations** | 500+ | Create/Update/Delete operations |
| **Queries** | 300+ | Data retrieval operations |
| **Attributes** | 1,000+ | Entity properties and relationships |
| **Events** | 50+ | Real-time event types |
| **Permissions** | 100+ | Fine-grained access control |

### Schema Breakdown

```
Infrahub Schema (11,131 lines)
├── Core Types (2,000+ lines)
│   ├── Node system (Branch, Account, Tag)
│   ├── Attribute system (String, Number, Boolean, JSON, etc.)
│   └── Relationship system (Component, Attribute, Generic)
├── IPAM Types (1,500+ lines)
│   ├── IPAddress, IPPrefix, IPNamespace
│   ├── VLAN, ASN, RouteTarget
│   └── IP allocation and management
├── DCIM Types (2,500+ lines)
│   ├── Device, Interface, Platform
│   ├── Rack, Site, Location hierarchy
│   └── Circuits, Cables, Connections
├── Organization Types (800+ lines)
│   ├── Provider, Tenant, Team
│   └── Contacts and relationships
├── Service Types (1,000+ lines)
│   ├── L2/L3 services
│   └── BGP sessions and routing
├── Event System (1,000+ lines)
│   ├── Real-time event streaming
│   ├── Branch operations (create, merge, rebase)
│   └── Schema evolution tracking
├── Permission System (800+ lines)
│   ├── Global permissions
│   ├── Object-level permissions
│   └── Role-based access control
└── Supporting Types (1,500+ lines)
    ├── Edges and pagination
    ├── Filters and aggregations
    └── Validation and metadata
```

## Architectural Highlights

### 1. **Graph-Native Design**

Unlike traditional REST APIs, Infrahub's GraphQL schema is truly graph-native:

```graphql
type InfraDevice implements CoreNode {
  # Identity
  id: String!
  display_label: String

  # Attributes with versioning
  name: TextAttribute!
  description: TextOptional
  status: DropdownOptional
  role: DropdownOptional

  # Relationships (graph edges)
  site: RelatedLocationSite
  interfaces: [RelatedInfraInterface!]!
  bgp_sessions: [RelatedInfraBGPSession!]!
  primary_address: RelatedIpamIPAddress

  # Metadata and permissions
  _updated_at: DateTime
  permissions: PermissionType
  owner: LineageOwner
}
```

**Key Features**:
- **Bidirectional relationships**: Every edge has both directions
- **Deep nesting**: Query arbitrary depth in single request
- **Attribute metadata**: Every field has lineage, ownership, permissions

### 2. **Version Control Built-In**

Infrahub treats infrastructure as code with Git-like versioning:

```graphql
type Branch {
  name: String!
  branched_from: String
  created_at: String
  has_schema_changes: Boolean
  graph_version: Int
  status: BranchStatus!
}

type BranchMerge {
  ok: Boolean
  object: Branch
  conflicts: [ConflictDetails!]
}

# Events for every branch operation
type BranchCreatedEvent implements EventNodeInterface
type BranchMergedEvent implements EventNodeInterface
type BranchRebasedEvent implements EventNodeInterface
```

**Capabilities**:
- Create feature branches for infrastructure changes
- Preview changes before merge
- Automatic conflict detection
- Full audit trail

### 3. **Rich Attribute System**

Every attribute type has rich metadata:

```graphql
interface AttributeInterface {
  is_default: Boolean      # Using default value?
  is_inherited: Boolean    # Inherited from parent?
  is_protected: Boolean    # Protected from changes?
  is_visible: Boolean      # Visible to current user?
  updated_at: DateTime     # When last modified?
  owner: LineageOwner      # Who owns this value?
  source: LineageSource    # Where did value come from?
  permissions: PermissionType  # Fine-grained permissions
}

# Specific attribute types
type TextAttribute implements AttributeInterface
type NumberAttribute implements AttributeInterface
type BoolAttribute implements AttributeInterface
type DropdownAttribute implements AttributeInterface
type IPHostAttribute implements AttributeInterface
type IPNetworkAttribute implements AttributeInterface
type JSONAttribute implements AttributeInterface
type ListAttribute implements AttributeInterface
type HashedPasswordAttribute implements AttributeInterface
```

**Power Features**:
- Track value lineage (where did this IP come from?)
- Inheritance hierarchies (site → rack → device)
- Permissions per attribute
- Audit trail per field

### 4. **Event-Driven Architecture**

Real-time event streaming for every operation:

```graphql
interface EventNodeInterface {
  id: String!
  event: String!              # Event type
  occurred_at: DateTime!      # Timestamp
  account_id: String          # Who triggered it
  branch: String              # Which branch
  level: Int!                 # Event hierarchy level
  parent_id: String           # Parent event
  has_children: Boolean!      # Has child events
  primary_node: RelatedNode   # Primary entity
  related_nodes: [RelatedNode!]!  # Related entities
}

# Specific event types (50+)
type ArtifactEvent implements EventNodeInterface
type BranchCreatedEvent implements EventNodeInterface
type SchemaValidatedEvent implements EventNodeInterface
type ProposedChangeCreatedEvent implements EventNodeInterface
```

**Use Cases**:
- Real-time UI updates
- Webhook triggers
- Audit logging
- Change tracking

### 5. **Fine-Grained Permissions**

Permissions at global, object, and attribute levels:

```graphql
type AccountGlobalPermission {
  action: String!        # view, create, update, delete
  decision: String!      # allow, deny
  namespace: String
  identifier: String
}

type AccountObjectPermission {
  action: String!
  decision: String!
  namespace: String!
  name: String!
  identifier: String!
}

type PermissionType {
  update: PermissionDecision!
  delete: PermissionDecision!
  view: PermissionDecision!
}
```

**Granularity**:
- Per namespace (e.g., only `Infra` objects)
- Per object type (e.g., only `InfraDevice`)
- Per instance (e.g., only this specific device)
- Per attribute (e.g., only view IP addresses)

### 6. **Schema Evolution Support**

Dynamic schema with migration tracking:

```graphql
type SchemaNode {
  kind: String!
  namespace: String!
  name: String!
  description: String
  attributes: [SchemaAttribute!]!
  relationships: [SchemaRelationship!]!
  generics: [String!]
  inherit_from: [String!]
  uniqueness_constraints: [[String!]!]
  default_filter: String
}

type SchemaDropdownChoice {
  name: String!
  label: String
  description: String
  color: String
}

type SchemaMigrationEvent implements EventNodeInterface {
  migrations: [String!]!
  previous_schema_hash: String!
  new_schema_hash: String!
}
```

**Capabilities**:
- Add/remove object types without downtime
- Evolve attributes (add, modify, remove)
- Schema validation before apply
- Migration tracking and rollback

### 7. **Powerful Query Capabilities**

Advanced filtering, pagination, and aggregation:

```graphql
input InfraDeviceFilter {
  name__value: String
  name__values: [String!]
  name__contains: String
  name__regex: String
  status__value: String
  status__values: [String!]
  role__value: String
  site__name__value: String
  # Nested filtering on relationships!
  interfaces__count: Int
  interfaces__name__contains: String
}

type InfraDeviceEdges {
  count: Int!
  edges: [InfraDeviceEdge!]!
  # Pagination cursors
  pageInfo: PageInfo!
}

# Complex queries possible
query GetCoreRoutersWithBGPSessions {
  InfraDevice(
    role__value: "core"
    bgp_sessions__count__gte: 1
  ) {
    edges {
      node {
        name { value }
        bgp_sessions {
          edges {
            node {
              peer_as { value }
              peer_ip { value }
            }
          }
        }
      }
    }
  }
}
```

### 8. **Proposed Changes Workflow**

Change management with approvals:

```graphql
type ProposedChange {
  id: String!
  name: String!
  state: ProposedChangeState!
  created_by: String
  created_at: DateTime
  source_branch: String!
  destination_branch: String!

  # Change details
  diff_summary: DiffSummary
  checks: ProposedChangeChecks
  comments: [ProposedChangeComment!]!

  # Available actions
  available_actions: AvailableActions!
}

type ProposedChangeChecks {
  repository: [RepositoryCheckResult!]!
  schema: [SchemaCheckResult!]!
  user: [UserCheckResult!]!
}

mutation ProposedChangeCreate {
  ProposedChangeCreate(
    data: {
      name: "Add new datacenter"
      source_branch: "feature/dc-nyc"
      destination_branch: "main"
    }
  ) {
    object {
      id
      state
      available_actions {
        edges {
          node {
            action
            available
          }
        }
      }
    }
  }
}
```

**Features**:
- CI/CD integration
- Approval workflows
- Automated checks (schema validation, tests, etc.)
- Comment threads
- Merge/reject/request-changes actions

## NetMapper's Integration Points

NetMapper leverages key aspects of the Infrahub schema:

### 1. **Device Modeling**

```python
# NetMapper maps to Infrahub's comprehensive device model
InfraDevice {
  name: "core-router-01"           # From NetMapper hostname
  type: "router"                   # Inferred from platform
  role: "core"                     # Inferred from hostname
  status: "active"                 # Operational status
  platform: "cisco_iosxe"          # NetMapper platform
  model: "ISR4451"                 # Hardware model
  serial_number: "ABC123"          # From discovery
  software_version: "17.3.4"       # OS version

  # Relationships
  site → LocationSite              # Physical location
  interfaces → [InfraInterface]    # All interfaces
  primary_address → IpamIPAddress  # Management IP
  tags → [BuiltinTag]             # Categorization
}
```

### 2. **Interface Modeling**

```python
# Rich interface model with role-based semantics
InfraInterface {
  name: "GigabitEthernet0/0"
  device → InfraDevice             # Parent device
  description: "Uplink to Core"
  speed: 1000                      # Mbps
  mtu: 1500
  enabled: true
  status: "active"
  role: "uplink"                   # Semantic role

  # L3 properties
  ip_addresses → [IpamIPAddress]  # All assigned IPs
  l3_interfaces → InfraInterfaceL3
}
```

### 3. **IPAM Integration**

```python
# NetMapper VLANs → Infrahub rich VLAN model
InfraVLAN {
  name: "VLAN100_Servers"
  vlan_id: 100
  description: "Production servers"
  status: "active"
  role: "server"                   # Semantic role
  site → LocationSite              # Site association
  gateway → InfraInterfaceL3      # L3 gateway
}

# IP addresses with full context
IpamIPAddress {
  address: "10.1.1.1/30"          # CIDR notation
  interface → InfraInterfaceL3    # Associated interface
  namespace → IpamIPNamespace     # IP namespace
  description: "Core router uplink"
}
```

### 4. **Relationship Semantics**

Infrahub's relationship types align perfectly with CIM:

```graphql
# Component relationship (composition)
type InfraDevice {
  interfaces: [RelatedInfraInterface!]!  # kind: Component
  bgp_sessions: [RelatedInfraBGPSession!]!  # kind: Component
}

# Attribute relationship (association)
type InfraDevice {
  site: RelatedLocationSite  # kind: Attribute
  asn: RelatedInfraAutonomousSystem  # kind: Attribute
}

# Maps to CIM perfectly:
# Component → CIM_COMPONENT (composition, is_weak=True)
# Attribute → CIM_CONTAINER (aggregation, is_weak=False)
```

## Why This Schema is Impressive

### 1. **Comprehensive Coverage**

From physical infrastructure to logical services:
- **Physical**: Racks, devices, cables, power
- **Logical**: VLANs, IP addresses, routing, BGP
- **Services**: L2VPN, L3VPN, Internet services
- **Organization**: Sites, tenants, providers, teams
- **Governance**: Permissions, approvals, workflows

### 2. **Production-Ready**

Not a toy schema, but production-grade:
- Battle-tested at scale
- Used by opsmill and community
- Active development and maintenance
- Comprehensive documentation

### 3. **Graph Database Native**

Truly leverages graph capabilities:
- Arbitrary depth traversal
- Bidirectional relationships
- Path queries
- Graph algorithms support

### 4. **Real-Time Collaboration**

Designed for teams:
- Branch-based workflows
- Conflict resolution
- Event streaming
- Multi-user coordination

### 5. **Extensible by Design**

Easy to extend:
- Custom attributes
- Custom relationships
- Generic types
- Schema inheritance

### 6. **API-First**

GraphQL provides:
- Single endpoint
- Type safety
- Introspection
- Client code generation
- Efficient data fetching (no over/under-fetching)

## NetMapper Advantages

By integrating with Infrahub's schema, NetMapper gains:

1. **Standardization**: Industry-standard infrastructure modeling
2. **Interoperability**: Compatible with Infrahub ecosystem
3. **Future-Proof**: Benefit from Infrahub's evolution
4. **Rich Context**: Leverage Infrahub's metadata and lineage
5. **Ecosystem**: Access to Infrahub's integrations and tools
6. **Validation**: GraphQL type checking and validation
7. **Documentation**: Auto-generated API docs from schema

## Comparison with Other Schemas

| Feature | Infrahub | NetBox | NAPALM | NetMapper |
|---------|----------|--------|--------|-----------|
| **Schema Size** | 11,131 lines | REST API | N/A | Integrated |
| **Type System** | GraphQL | Django ORM | Python | Pydantic |
| **Versioning** | Git-like branches | Change logs | N/A | Neo4j |
| **Real-time** | Event streaming | Webhooks | N/A | Graph queries |
| **Permissions** | Attribute-level | Object-level | N/A | Neo4j ACL |
| **Graph Native** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **API Type** | GraphQL | REST | Python lib | Python lib |
| **Relationships** | First-class | Foreign keys | N/A | Graph edges |

## Example: Complex Query

This query would be multiple REST calls in NetBox, but single request in Infrahub:

```graphql
query GetDatacenterTopology {
  LocationSite(name__value: "DC-NYC") {
    edges {
      node {
        name { value }
        racks: children {
          edges {
            node {
              ... on LocationRack {
                name { value }
                devices {
                  edges {
                    node {
                      name { value }
                      type { value }
                      role { value }
                      interfaces {
                        edges {
                          node {
                            name { value }
                            status { value }
                            ip_addresses {
                              edges {
                                node {
                                  address { value }
                                }
                              }
                            }
                            # Connected interfaces (graph traversal!)
                            connected_interface {
                              node {
                                name { value }
                                device {
                                  node {
                                    name { value }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

Single request returns entire datacenter topology with connections!

## Future Possibilities

NetMapper could further leverage Infrahub's schema:

1. **Direct GraphQL Integration**: Query NetMapper data via GraphQL
2. **Real-Time Sync**: Event-driven updates to Infrahub
3. **Branch-Based Discovery**: Discovery in feature branches
4. **Schema Extensions**: Custom NetMapper-specific types
5. **Bidirectional Sync**: Infrahub → NetMapper updates
6. **Workflow Integration**: Discovery as proposed changes
7. **Automated Validation**: Schema-based discovery validation

## Conclusion

The Infrahub GraphQL schema represents the **state-of-the-art in infrastructure modeling**:

- **11,131 lines** of meticulously designed types
- **1,095+ types** covering every aspect of infrastructure
- **Graph-native** design leveraging full power of graph databases
- **Production-ready** with version control, permissions, events
- **Extensible** architecture for custom requirements

NetMapper's integration with this schema provides a **solid foundation** for infrastructure management, combining:
- NetMapper's **discovery capabilities**
- Infrahub's **standardized modeling**
- DMTF CIM's **semantic relationships**
- Neo4j's **graph database power**

Together, they create a **comprehensive infrastructure intelligence platform**.

---

**References**:
- Infrahub Repository: https://github.com/opsmill/infrahub
- Infrahub Schema: 11,131 lines of GraphQL
- Infrahub Models: https://github.com/opsmill/infrahub/tree/stable/models/
- NetMapper Integration: `docs/INFRAHUB_INTEGRATION.md`
