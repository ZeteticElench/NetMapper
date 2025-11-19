"""Async network discovery with adaptive worker tuning and batched Neo4j writes.

This module enhances async_discovery.py with:
1. Adaptive worker tuning - automatically scale workers based on queue depth
2. Async Neo4j batch writer - dynamic batch sizing for maximum throughput
3. Self-optimizing system - "waiting is infinitely parallelizable until you run out of RAM"
"""

import asyncio
import logging
from typing import Set, Dict, Optional
from datetime import datetime

from .models import (
    DeviceCredentials,
    DiscoveryConfig,
    DiscoveryResult,
)
from .collector import DeviceCollector
from .async_neo4j import AsyncNeo4jManager
from .utils import normalize_hostname


logger = logging.getLogger(__name__)


class AdaptiveAsyncDiscovery:
    """
    Adaptive async network discovery with self-tuning workers and batched writes.

    Adaptive Scaling:
    - Monitors queue depth continuously
    - Spawns more workers when queue > 80% full
    - Reduces workers when queue < 20% full
    - Workers scale from min_workers to max_workers dynamically

    Batched Writes:
    - Neo4j writes are queued and batched
    - Batch size scales with write queue depth
    - Reduces database round-trips by 10-100x
    """

    def __init__(
        self,
        config: DiscoveryConfig,
        min_workers: int = 5,
        max_workers: int = 100,
        queue_max_size: int = 1000,
        enable_adaptive_tuning: bool = True,
    ) -> None:
        """
        Initialize adaptive async discovery.

        Args:
            config: Discovery configuration.
            min_workers: Minimum concurrent workers.
            max_workers: Maximum concurrent workers (RAM is the limit!).
            queue_max_size: Maximum queue size.
            enable_adaptive_tuning: Enable adaptive worker scaling.
        """
        self.config = config
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.queue_max_size = queue_max_size
        self.enable_adaptive_tuning = enable_adaptive_tuning

        # Collectors and storage
        self.collector = DeviceCollector(
            timeout=config.connection_timeout,
            command_timeout=config.command_timeout,
        )

        # Async Neo4j with batched writes
        self.neo4j = AsyncNeo4jManager(
            uri=config.neo4j_uri,
            username=config.neo4j_username,
            password=config.neo4j_password,
            enable_batching=True,
        )

        # Thread-safe queue and tracking
        self.work_queue: asyncio.Queue[DeviceCredentials] = asyncio.Queue(
            maxsize=queue_max_size
        )
        self.visited_lock = asyncio.Lock()
        self.visited: Set[str] = set()

        # Credential cache
        self.credential_cache: Dict[str, DeviceCredentials] = {}

        # Worker management
        self.active_workers: Set[asyncio.Task] = set()
        self.worker_id_counter = 0
        self.worker_lock = asyncio.Lock()

        # Statistics
        self.devices_discovered = 0
        self.devices_failed = 0
        self.start_time: Optional[datetime] = None
        self.stats_lock = asyncio.Lock()

        # Adaptive tuning task
        self.tuning_task: Optional[asyncio.Task] = None

    async def run(self) -> None:
        """
        Run adaptive async discovery.

        Flow:
        1. Connect to Neo4j batch writer
        2. Load existing devices
        3. Enqueue start device
        4. Spawn initial workers
        5. Start adaptive tuning (if enabled)
        6. Wait for completion
        7. Flush Neo4j batches
        """
        logger.info(
            f"Starting adaptive async discovery "
            f"(min={self.min_workers}, max={self.max_workers} workers)"
        )
        self.start_time = datetime.now()

        # Connect to async Neo4j
        await self.neo4j.connect()

        # Load existing devices
        existing_devices = await self.neo4j.get_visited_devices()
        logger.info(f"Found {len(existing_devices)} existing devices in database")

        async with self.visited_lock:
            self.visited.update(existing_devices)

        # Enqueue start device
        start_hostname = normalize_hostname(self.config.start_device.hostname)
        self.credential_cache[start_hostname] = self.config.start_device
        await self.work_queue.put(self.config.start_device)

        # Spawn initial workers
        await self._spawn_workers(self.min_workers)

        # Start adaptive tuning
        if self.enable_adaptive_tuning:
            self.tuning_task = asyncio.create_task(self._adaptive_tuning())

        # Wait for queue to drain and all workers to finish
        await self.work_queue.join()

        # Stop adaptive tuning
        if self.tuning_task:
            self.tuning_task.cancel()
            try:
                await self.tuning_task
            except asyncio.CancelledError:
                pass

        # Stop all workers
        await self._stop_all_workers()

        # Close Neo4j (flushes remaining batches)
        await self.neo4j.close()

        # Print summary
        self._print_summary()

    async def _spawn_workers(self, count: int) -> None:
        """
        Spawn additional workers.

        Args:
            count: Number of workers to spawn.
        """
        async with self.worker_lock:
            for _ in range(count):
                worker_id = self.worker_id_counter
                self.worker_id_counter += 1

                task = asyncio.create_task(self._worker(worker_id))
                self.active_workers.add(task)

            logger.info(f"Spawned {count} workers (total: {len(self.active_workers)})")

    async def _stop_workers(self, count: int) -> None:
        """
        Stop and remove idle workers.

        Args:
            count: Number of workers to stop.
        """
        async with self.worker_lock:
            # Cancel the requested number of workers
            workers_to_cancel = list(self.active_workers)[:count]

            for task in workers_to_cancel:
                task.cancel()
                self.active_workers.discard(task)

            if workers_to_cancel:
                logger.info(
                    f"Stopped {len(workers_to_cancel)} workers "
                    f"(remaining: {len(self.active_workers)})"
                )

    async def _stop_all_workers(self) -> None:
        """Stop all workers."""
        async with self.worker_lock:
            for task in self.active_workers:
                task.cancel()

            # Wait for cancellation
            if self.active_workers:
                await asyncio.gather(*self.active_workers, return_exceptions=True)

            self.active_workers.clear()
            logger.info("All workers stopped")

    async def _adaptive_tuning(self) -> None:
        """
        Adaptive worker tuning based on queue depth.

        Strategy:
        - Queue > 80% full: Spawn more workers (up to max_workers)
        - Queue < 20% full: Reduce workers (down to min_workers)
        - Check every 2 seconds

        The beauty: Async coroutines use ~5 KB each, so we can spawn
        hundreds of workers without worrying about RAM!
        """
        logger.info("Adaptive tuning enabled")

        while True:
            try:
                await asyncio.sleep(2.0)  # Check every 2 seconds

                queue_size = self.work_queue.qsize()
                queue_percent = (queue_size / self.queue_max_size) * 100

                async with self.worker_lock:
                    current_workers = len(self.active_workers)

                # Scale up: Queue is filling up
                if queue_percent > 80 and current_workers < self.max_workers:
                    # Spawn 10% more workers
                    spawn_count = max(1, int(current_workers * 0.1))
                    spawn_count = min(spawn_count, self.max_workers - current_workers)

                    await self._spawn_workers(spawn_count)

                    logger.info(
                        f"Adaptive scale UP: queue {queue_percent:.1f}% full, "
                        f"spawned {spawn_count} workers"
                    )

                # Scale down: Queue is mostly empty
                elif queue_percent < 20 and current_workers > self.min_workers:
                    # Remove 10% of workers
                    remove_count = max(1, int(current_workers * 0.1))
                    remove_count = min(remove_count, current_workers - self.min_workers)

                    await self._stop_workers(remove_count)

                    logger.info(
                        f"Adaptive scale DOWN: queue {queue_percent:.1f}% full, "
                        f"removed {remove_count} workers"
                    )

            except asyncio.CancelledError:
                logger.info("Adaptive tuning stopped")
                break
            except Exception as e:
                logger.error(f"Adaptive tuning error: {e}")

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
                    f"(queue: {self.work_queue.qsize()}, "
                    f"workers: {len(self.active_workers)})"
                )

                try:
                    # Discover device (blocking I/O, run in thread pool)
                    result = await asyncio.to_thread(self.collector.collect, creds)

                    # Store in Neo4j (async batched)
                    await self.neo4j.store_discovery_result(result)

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
            logger.debug(
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
        logger.info("Adaptive Async Discovery Summary")
        logger.info("=" * 60)
        logger.info(f"Worker range: {self.min_workers}-{self.max_workers}")
        logger.info(f"Peak workers: {self.worker_id_counter}")
        logger.info(f"Devices discovered: {self.devices_discovered}")
        logger.info(f"Devices failed: {self.devices_failed}")
        logger.info(f"Total devices visited: {len(self.visited)}")
        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Rate: {rate:.2f} devices/second")
        logger.info("=" * 60)


async def run_adaptive_discovery(
    config: DiscoveryConfig,
    min_workers: int = 5,
    max_workers: int = 100,
    enable_adaptive_tuning: bool = True,
) -> None:
    """
    Helper function to run adaptive async discovery.

    Args:
        config: Discovery configuration.
        min_workers: Minimum concurrent workers.
        max_workers: Maximum concurrent workers.
        enable_adaptive_tuning: Enable adaptive worker scaling.
    """
    discovery = AdaptiveAsyncDiscovery(
        config,
        min_workers=min_workers,
        max_workers=max_workers,
        enable_adaptive_tuning=enable_adaptive_tuning,
    )
    await discovery.run()
