"""Network discovery orchestrator using queue-based traversal."""

import logging
from typing import Set, Dict, Optional, Deque
from collections import deque

from .models import (
    DeviceCredentials,
    DiscoveryConfig,
    DiscoveryResult,
    CDPNeighbor,
    LLDPNeighbor,
)
from .collector import DeviceCollector
from .neo4j_manager import Neo4jManager
from .utils import normalize_hostname


logger = logging.getLogger(__name__)


class NetworkDiscovery:
    """Orchestrate network topology discovery using queue-based traversal."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """
        Initialize network discovery.

        Args:
            config: Discovery configuration.
        """
        self.config = config
        self.collector = DeviceCollector(
            timeout=config.connection_timeout,
            command_timeout=config.command_timeout,
        )
        self.neo4j = Neo4jManager(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
        )

        # Track visited devices to prevent loops
        self.visited: Set[str] = set()

        # Work queue for devices to discover
        self.work_queue: Deque[DeviceCredentials] = deque()

        # Credential cache (hostname -> credentials)
        self.credential_cache: Dict[str, DeviceCredentials] = {}

        # Statistics
        self.devices_discovered = 0
        self.devices_failed = 0

    def run(self) -> None:
        """
        Run the discovery process.

        Starts with the configured start device and discovers neighbors
        until the queue is empty.
        """
        logger.info("Starting network discovery")

        # Load already visited devices from Neo4j
        existing_devices = self.neo4j.get_visited_devices()
        logger.info(f"Found {len(existing_devices)} existing devices in database")
        self.visited.update(existing_devices)

        # Add start device to queue
        start_hostname = normalize_hostname(self.config.start_device.hostname)
        self.credential_cache[start_hostname] = self.config.start_device
        self.work_queue.append(self.config.start_device)

        # Process queue until empty
        depth = 0
        while self.work_queue:
            # Check max depth if configured
            if self.config.max_depth is not None and depth >= self.config.max_depth:
                logger.info(f"Reached maximum depth of {self.config.max_depth}")
                break

            # Get next device from queue
            creds = self.work_queue.popleft()
            hostname = normalize_hostname(creds.hostname)

            # Skip if already visited
            if hostname in self.visited:
                logger.debug(f"Skipping already visited device: {hostname}")
                continue

            # Mark as visited BEFORE processing to prevent duplicates
            self.visited.add(hostname)
            logger.info(f"Processing device {hostname} ({self.devices_discovered + 1})")

            try:
                # Discover device
                result = self.collector.collect(creds)

                # Store in Neo4j
                self.neo4j.store_discovery_result(result)

                # Add neighbors to queue
                self._enqueue_neighbors(result)

                self.devices_discovered += 1
                logger.info(f"Successfully discovered {hostname}")

            except Exception as e:
                logger.error(f"Failed to discover {hostname}: {e}")
                self.devices_failed += 1
                # Remove from visited so it can be retried later if needed
                self.visited.discard(hostname)

            depth += 1

        # Print summary
        self._print_summary()

    def _enqueue_neighbors(self, result: DiscoveryResult) -> None:
        """
        Add discovered neighbors to the work queue.

        Args:
            result: Discovery result containing neighbor information.
        """
        neighbors_to_add: Set[str] = set()

        # Collect CDP neighbors
        if self.config.discover_cdp:
            for neighbor in result.cdp_neighbors:
                neighbor_hostname = normalize_hostname(neighbor.neighbor_device)
                if neighbor_hostname not in self.visited and neighbor_hostname not in neighbors_to_add:
                    neighbors_to_add.add(neighbor_hostname)

                    # Create credentials for neighbor
                    neighbor_creds = self._create_neighbor_credentials(
                        neighbor.neighbor_device,
                        neighbor.neighbor_ip,
                    )
                    if neighbor_creds:
                        self.work_queue.append(neighbor_creds)
                        logger.info(f"Added CDP neighbor to queue: {neighbor_hostname}")

        # Collect LLDP neighbors
        if self.config.discover_lldp:
            for neighbor in result.lldp_neighbors:
                neighbor_hostname = normalize_hostname(neighbor.neighbor_device)
                if neighbor_hostname not in self.visited and neighbor_hostname not in neighbors_to_add:
                    neighbors_to_add.add(neighbor_hostname)

                    # Create credentials for neighbor
                    neighbor_creds = self._create_neighbor_credentials(
                        neighbor.neighbor_device,
                        neighbor.neighbor_ip,
                    )
                    if neighbor_creds:
                        self.work_queue.append(neighbor_creds)
                        logger.info(f"Added LLDP neighbor to queue: {neighbor_hostname}")

    def _create_neighbor_credentials(
        self, hostname: str, ip: Optional[str]
    ) -> Optional[DeviceCredentials]:
        """
        Create credentials for a neighbor device.

        Uses the same credentials as the start device.

        Args:
            hostname: Neighbor hostname.
            ip: Neighbor IP address (optional).

        Returns:
            DeviceCredentials if IP is available, None otherwise.
        """
        if not ip or ip == "unknown":
            logger.warning(f"No IP address available for neighbor {hostname}")
            return None

        normalized_hostname = normalize_hostname(hostname)

        # Check if we already have credentials for this device
        if normalized_hostname in self.credential_cache:
            return self.credential_cache[normalized_hostname]

        # Create new credentials using start device template
        start_creds = self.config.start_device
        neighbor_creds = DeviceCredentials(
            hostname=normalized_hostname,
            ip=ip,
            username=start_creds.username,
            password=start_creds.password,
            enable_password=start_creds.enable_password,
            protocol=start_creds.protocol,
            port=start_creds.port,
            os=start_creds.os,
        )

        self.credential_cache[normalized_hostname] = neighbor_creds
        return neighbor_creds

    def _print_summary(self) -> None:
        """Print discovery summary."""
        logger.info("=" * 60)
        logger.info("Discovery Summary")
        logger.info("=" * 60)
        logger.info(f"Devices discovered: {self.devices_discovered}")
        logger.info(f"Devices failed: {self.devices_failed}")
        logger.info(f"Total devices visited: {len(self.visited)}")
        logger.info(f"Devices remaining in queue: {len(self.work_queue)}")
        logger.info("=" * 60)

    def close(self) -> None:
        """Close connections and cleanup."""
        self.neo4j.close()
        logger.info("Discovery connections closed")
