#!/usr/bin/env python3
"""
Example: Export NetMapper topology to Infrahub-compatible format.

This script demonstrates how to convert NetMapper discovery data to Infrahub
models and export them to YAML/JSON for import into Infrahub.

Usage:
    python examples/infrahub_export_example.py
"""

import logging
from netmapper.infrahub_adapter import InfrahubAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Convert NetMapper topology to Infrahub models and export."""

    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USERNAME = "neo4j"
    NEO4J_PASSWORD = "password"

    # Output files
    YAML_OUTPUT = "netmapper_infrahub_topology.yml"
    JSON_OUTPUT = "netmapper_infrahub_topology.json"

    logger.info("=== NetMapper to Infrahub Exporter ===\n")

    # Create adapter
    adapter = InfrahubAdapter(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

    try:
        # Convert topology
        logger.info("Converting NetMapper topology to Infrahub models...")
        topology = adapter.convert_topology()

        # Print summary
        print("\n=== Conversion Summary ===")
        print(f"Devices:      {len(topology.devices)}")
        print(f"Interfaces:   {len(topology.interfaces)}")
        print(f"VLANs:        {len(topology.vlans)}")
        print(f"IP Addresses: {len(topology.ip_addresses)}")
        print(f"Sites:        {len(topology.sites)}")
        print(f"Timestamp:    {topology.discovery_timestamp}")

        # Sample device details
        if topology.devices:
            print("\n=== Sample Device (Infrahub Model) ===")
            device = topology.devices[0]
            print(f"Name:     {device.name}")
            print(f"Type:     {device.type}")
            print(f"Role:     {device.role}")
            print(f"Status:   {device.status}")
            print(f"Platform: {device.platform}")
            print(f"Model:    {device.model}")
            print(f"Site:     {device.site}")

        # Sample interface details
        if topology.interfaces:
            print("\n=== Sample Interface (Infrahub Model) ===")
            interface = topology.interfaces[0]
            print(f"Name:        {interface.name}")
            print(f"Device:      {interface.device}")
            print(f"Status:      {interface.status}")
            print(f"Role:        {interface.role}")
            print(f"Enabled:     {interface.enabled}")
            print(f"IP Addresses: {interface.ip_addresses}")

        # Export to YAML
        logger.info(f"\nExporting to YAML: {YAML_OUTPUT}")
        adapter.export_to_yaml(topology, YAML_OUTPUT)

        # Export to JSON
        logger.info(f"Exporting to JSON: {JSON_OUTPUT}")
        adapter.export_to_json(topology, JSON_OUTPUT)

        print(f"\n=== Export Complete ===")
        print(f"YAML: {YAML_OUTPUT}")
        print(f"JSON: {JSON_OUTPUT}")
        print("\nThese files can be imported into Infrahub or used for integration.")

        # Show example Infrahub import command
        print("\n=== Next Steps ===")
        print("To import into Infrahub:")
        print("1. Review the generated YAML/JSON files")
        print("2. Use Infrahub's import utilities or API")
        print("3. Map any additional custom attributes as needed")
        print("\nExample Infrahub GraphQL mutation:")
        print("""
mutation CreateDevice {
  InfraDeviceCreate(
    data: {
      name: { value: "device-hostname" }
      type: { value: "router" }
      status: { value: "active" }
      role: { value: "core" }
    }
  ) {
    object {
      id
      name { value }
    }
  }
}
        """)

    finally:
        adapter.close()
        logger.info("Connection closed.")


if __name__ == "__main__":
    main()
