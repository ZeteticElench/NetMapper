"""Main entry point for hybrid NetMapper discovery (PyATS + Bejerano SNMP)."""

import sys
import logging
import argparse
from pathlib import Path
from typing import Any, Dict

import yaml

from .models import DiscoveryConfig, DeviceCredentials
from .hybrid_discovery import HybridNetworkDiscovery


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
    logging.getLogger('pysnmp').setLevel(logging.WARNING)


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

    # Parse Bejerano options
    bejerano_opts = config_data.get('bejerano', {})

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
        enable_bejerano=bejerano_opts.get('enable', True),
        snmp_community=bejerano_opts.get('snmp_community', 'public'),
        mac_collection_method=bejerano_opts.get('mac_collection_method', 'snmp'),
    )

    return config


def main() -> int:
    """
    Main entry point for hybrid discovery.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description='NetMapper Hybrid Discovery - PyATS + Bejerano SNMP topology discovery'
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
    parser.add_argument(
        '--no-bejerano',
        action='store_true',
        help='Disable Bejerano SNMP-based discovery',
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)

        # Override Bejerano setting if --no-bejerano specified
        if args.no_bejerano:
            config.enable_bejerano = False
            logger.info("Bejerano SNMP discovery disabled via command line")

        # Run hybrid discovery
        logger.info("Starting hybrid network discovery")
        logger.info(f"PyATS discovery: CDP={config.discover_cdp}, LLDP={config.discover_lldp}, "
                   f"STP={config.discover_stp}, VLAN={config.discover_vlans}")
        logger.info(f"Bejerano topology discovery: {config.enable_bejerano}")
        logger.info(f"MAC collection method: {config.mac_collection_method}")

        discovery = HybridNetworkDiscovery(
            config=config,
            snmp_community=config.snmp_community,
            enable_bejerano=config.enable_bejerano,
            mac_collection_method=config.mac_collection_method,
        )

        try:
            discovery.run()
            logger.info("Hybrid discovery completed successfully")
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
