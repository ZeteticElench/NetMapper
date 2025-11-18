"""Async network discovery with producer-consumer pattern and worker pools.

This module implements concurrent network discovery using asyncio and worker pools.
The producer-consumer pattern allows discovering CDP/LLDP neighbors quickly and
processing them in parallel, dramatically improving performance.
"""

import asyncio
import logging
from typing import Set, Dict, Optional, Deque
from collections import deque
from datetime import datetime

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


class AsyncNetworkDiscovery:
    """
    Async network discovery with producer-consumer pattern.

    Architecture:
    - Producer: Discovers devices and enqueues neighbors immediately after CDP/LLDP
    - Consumer Pool: Multiple workers process devices concurrently
    - Thread-safe queue and visited set prevent infinite loops
    - Natural backpressure handling via queue size
    """

    def __init__(
        self,
        config: DiscoveryConfig,
        max_workers: int = 10,
        queue_max_size: int = 100,
    ) -> None:
        """
        Initialize async network discovery.

        Args:
            config: Discovery configuration.
            max_workers: Maximum number of concurrent workers.
            queue_max_size: Maximum queue size (backpressure).
        """
        self.config = config
        self.max_workers = max_workers
        self.queue_max_size = queue_max_size

        # Collectors and storage
        self.collector = DeviceCollector(
            timeout=config.connection_timeout,
            command_timeout=config.command_timeout,
        )
        self.neo4j = Neo4jManager(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
        )

        # Thread-safe queue and tracking
        self.work_queue: asyncio.Queue[DeviceCredentials] = asyncio.Queue(
            maxsize=queue_max_size
        )
        self.visited_lock = asyncio.Lock()
        self.visited: Set[str] = set()

        # Credential cache
        self.credential_cache: Dict[str, DeviceCredentials] = {}

        # Statistics
        self.devices_discovered = 0
        self.devices_failed = 0
        self.start_time: Optional[datetime] = None
        self.stats_lock = asyncio.Lock()

    async def run(self) -> None:
        """
        Run async discovery with worker pool.

        Flow:
        1. Load existing devices from Neo4j
        2. Enqueue start device
        3. Spawn worker pool
        4. Workers process queue until empty
        5. Each worker discovers device and enqueues neighbors
        """
        logger.info(f"Starting async network discovery with {self.max_workers} workers")
        self.start_time = datetime.now()

        # Load existing devices
        existing_devices = await asyncio.to_thread(self.neo4j.get_visited_devices)
        logger.info(f"Found {len(existing_devices)} existing devices in database")

        async with self.visited_lock:
            self.visited.update(existing_devices)

        # Enqueue start device
        start_hostname = normalize_hostname(self.config.start_device.hostname)
        self.credential_cache[start_hostname] = self.config.start_device
        await self.work_queue.put(self.config.start_device)

        # Create worker tasks
        workers = [
            asyncio.create_task(self._worker(worker_id))
            for worker_id in range(self.max_workers)
        ]

        # Wait for queue to be empty and all workers to finish
        await self.work_queue.join()

        # Cancel workers
        for worker in workers:
            worker.cancel()

        # Wait for workers to finish cancellation
        await asyncio.gather(*workers, return_exceptions=True)

        # Print summary
        self._print_summary()

    async def _worker(self, worker_id: int) -> None:
        """
        Worker task that processes devices from the queue.

        Args:
            worker_id: Worker identifier for logging.
        """
        logger.debug(f"Worker {worker_id} started")

        while True:
            try:
                # Get next device from queue (with timeout to allow cancellation)
                try:
                    creds = await asyncio.wait_for(
                        self.work_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                hostname = normalize_hostname(creds.hostname)

                # Check if already visited (double-check with lock)
                async with self.visited_lock:
                    if hostname in self.visited:
                        logger.debug(
                            f"Worker {worker_id}: Skipping visited device {hostname}"
                        )
                        self.work_queue.task_done()
                        continue

                    # Mark as visited immediately to prevent other workers from taking it
                    self.visited.add(hostname)

                # Process device
                logger.info(
                    f"Worker {worker_id}: Processing {hostname} "
                    f"(queue size: {self.work_queue.qsize()})"
                )

                try:
                    # Discover device (blocking I/O, run in thread pool)
                    result = await asyncio.to_thread(self.collector.collect, creds)

                    # Store in Neo4j (blocking I/O, run in thread pool)
                    await asyncio.to_thread(
                        self.neo4j.store_discovery_result, result
                    )

                    # Update stats
                    async with self.stats_lock:
                        self.devices_discovered += 1

                    # Enqueue neighbors IMMEDIATELY after discovery
                    await self._enqueue_neighbors(result)

                    logger.info(
                        f"Worker {worker_id}: Completed {hostname} "
                        f"({self.devices_discovered} total)"
                    )

                except Exception as e:
                    logger.error(f"Worker {worker_id}: Failed to process {hostname}: {e}")

                    # Update stats
                    async with self.stats_lock:
                        self.devices_failed += 1

                    # Remove from visited so it can be retried
                    async with self.visited_lock:
                        self.visited.discard(hostname)

                finally:
                    self.work_queue.task_done()

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    async def _enqueue_neighbors(self, result: DiscoveryResult) -> None:
        """
        Enqueue discovered neighbors to work queue.

        Args:
            result: Discovery result containing neighbor information.
        """
        neighbors_added = 0

        # Process CDP neighbors
        if self.config.discover_cdp:
            for neighbor in result.cdp_neighbors:
                added = await self._try_enqueue_neighbor(
                    neighbor.neighbor_device,
                    neighbor.neighbor_ip,
                )
                if added:
                    neighbors_added += 1

        # Process LLDP neighbors
        if self.config.discover_lldp:
            for neighbor in result.lldp_neighbors:
                added = await self._try_enqueue_neighbor(
                    neighbor.neighbor_device,
                    neighbor.neighbor_ip,
                )
                if added:
                    neighbors_added += 1

        if neighbors_added > 0:
            logger.info(
                f"Enqueued {neighbors_added} neighbors from {result.device.hostname}"
            )

    async def _try_enqueue_neighbor(
        self,
        hostname: str,
        ip: Optional[str],
    ) -> bool:
        """
        Try to enqueue a neighbor if not visited and has valid IP.

        Args:
            hostname: Neighbor hostname.
            ip: Neighbor IP address.

        Returns:
            True if enqueued, False otherwise.
        """
        if not ip or ip == "unknown":
            return False

        normalized_hostname = normalize_hostname(hostname)

        # Check if already visited
        async with self.visited_lock:
            if normalized_hostname in self.visited:
                return False

        # Create credentials
        neighbor_creds = self._create_neighbor_credentials(normalized_hostname, ip)
        if not neighbor_creds:
            return False

        # Enqueue (will block if queue is full - backpressure)
        try:
            await self.work_queue.put(neighbor_creds)
            logger.debug(f"Enqueued neighbor: {normalized_hostname}")
            return True
        except asyncio.QueueFull:
            logger.warning(f"Queue full, skipping {normalized_hostname}")
            return False

    def _create_neighbor_credentials(
        self,
        hostname: str,
        ip: str,
    ) -> Optional[DeviceCredentials]:
        """
        Create credentials for neighbor device.

        Args:
            hostname: Neighbor hostname.
            ip: Neighbor IP address.

        Returns:
            DeviceCredentials or None.
        """
        # Check cache
        if hostname in self.credential_cache:
            return self.credential_cache[hostname]

        # Use start device credentials as template
        start_creds = self.config.start_device
        neighbor_creds = DeviceCredentials(
            hostname=hostname,
            ip=ip,
            username=start_creds.username,
            password=start_creds.password,
            enable_password=start_creds.enable_password,
            protocol=start_creds.protocol,
            port=start_creds.port,
            os=start_creds.os,
        )

        self.credential_cache[hostname] = neighbor_creds
        return neighbor_creds

    def _print_summary(self) -> None:
        """Print discovery summary."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            rate = self.devices_discovered / duration if duration > 0 else 0
        else:
            duration = 0
            rate = 0

        logger.info("=" * 60)
        logger.info("Async Discovery Summary")
        logger.info("=" * 60)
        logger.info(f"Workers: {self.max_workers}")
        logger.info(f"Devices discovered: {self.devices_discovered}")
        logger.info(f"Devices failed: {self.devices_failed}")
        logger.info(f"Total devices visited: {len(self.visited)}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Rate: {rate:.2f} devices/second")
        logger.info("=" * 60)

    def close(self) -> None:
        """Close connections and cleanup."""
        self.neo4j.close()
        logger.info("Async discovery connections closed")


async def run_async_discovery(config: DiscoveryConfig, max_workers: int = 10) -> None:
    """
    Helper function to run async discovery.

    Args:
        config: Discovery configuration.
        max_workers: Maximum number of concurrent workers.
    """
    discovery = AsyncNetworkDiscovery(config, max_workers=max_workers)
    try:
        await discovery.run()
    finally:
        discovery.close()
