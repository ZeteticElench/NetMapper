"""Main entry point for NetMapper network discovery."""

import sys
import logging
import argparse
from pathlib import Path
from typing import Any, Dict

import yaml

from .models import DiscoveryConfig, DeviceCredentials
from .discovery import NetworkDiscovery


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        verbose: Enable verbose (DEBUG) logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Reduce noise from libraries
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    logging.getLogger('pyats').setLevel(logging.WARNING)
    logging.getLogger('unicon').setLevel(logging.WARNING)


def load_config(config_file: Path) -> DiscoveryConfig:
    """
    Load configuration from YAML file.

    Args:
        config_file: Path to configuration file.

    Returns:
        DiscoveryConfig object.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If config is invalid.
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, 'r') as f:
        config_data: Dict[str, Any] = yaml.safe_load(f)

    # Parse start device credentials
    device_data = config_data.get('start_device', {})
    start_device = DeviceCredentials(**device_data)

    # Parse Neo4j configuration
    neo4j_config = config_data.get('neo4j', {})

    # Parse discovery options
    discovery_opts = config_data.get('discovery', {})

    config = DiscoveryConfig(
        start_device=start_device,
        neo4j_uri=neo4j_config.get('uri', 'bolt://localhost:7687'),
        neo4j_username=neo4j_config.get('username', 'neo4j'),
        neo4j_password=neo4j_config.get('password', 'password'),
        max_depth=discovery_opts.get('max_depth'),
        discover_cdp=discovery_opts.get('discover_cdp', True),
        discover_lldp=discovery_opts.get('discover_lldp', True),
        discover_stp=discovery_opts.get('discover_stp', True),
        discover_vlans=discovery_opts.get('discover_vlans', True),
        connection_timeout=discovery_opts.get('connection_timeout', 30),
        command_timeout=discovery_opts.get('command_timeout', 30),
    )

    return config


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description='NetMapper - Network topology discovery using PyATS and Neo4j'
    )
    parser.add_argument(
        '-c',
        '--config',
        type=Path,
        default=Path('config.yaml'),
        help='Path to configuration file (default: config.yaml)',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging',
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)

        # Run discovery
        logger.info("Starting network discovery")
        discovery = NetworkDiscovery(config)

        try:
            discovery.run()
            logger.info("Discovery completed successfully")
            return 0

        finally:
            discovery.close()

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except KeyboardInterrupt:
        logger.info("Discovery interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
