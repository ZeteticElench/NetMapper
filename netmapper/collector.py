"""PyATS-based data collector for network devices."""

import logging
from typing import Optional, List, Dict, Any
from pyats.topology import Device as PyATSDevice
from pyats.topology import Testbed
from genie.libs.parser.utils.common import ParserNotFound

from .models import (
    NetworkDevice,
    Port,
    Interface,
    CDPNeighbor,
    LLDPNeighbor,
    VLANInfo,
    STPInstance,
    STPInterface,
    PortStatus,
    DeviceCredentials,
    DiscoveryResult,
)
from .utils import normalize_hostname, normalize_interface_name


logger = logging.getLogger(__name__)


class DeviceCollector:
    """Collect network topology data from devices using PyATS."""

    def __init__(self, timeout: int = 30, command_timeout: int = 30) -> None:
        """
        Initialize the device collector.

        Args:
            timeout: Connection timeout in seconds.
            command_timeout: Command execution timeout in seconds.
        """
        self.timeout = timeout
        self.command_timeout = command_timeout

    def _create_device(self, creds: DeviceCredentials) -> PyATSDevice:
        """
        Create a PyATS device from credentials.

        Args:
            creds: Device credentials.

        Returns:
            PyATS Device object.
        """
        testbed = Testbed('dynamic_testbed')
        device = PyATSDevice(
            name=creds.hostname,
            os=creds.os,
            credentials={
                'default': {
                    'username': creds.username,
                    'password': creds.password,
                },
                'enable': {
                    'password': creds.enable_password or creds.password,
                }
            },
            connections={
                'cli': {
                    'protocol': creds.protocol,
                    'ip': creds.ip,
                    'port': creds.port,
                }
            },
            testbed=testbed,
        )
        return device

    def collect(self, creds: DeviceCredentials) -> DiscoveryResult:
        """
        Collect all network data from a device.

        Args:
            creds: Device credentials.

        Returns:
            DiscoveryResult containing all collected data.
        """
        logger.info(f"Connecting to device {creds.hostname} ({creds.ip})")
        device = self._create_device(creds)

        try:
            device.connect(
                learn_hostname=True,
                init_exec_commands=[],
                init_config_commands=[],
                log_stdout=False,
                connection_timeout=self.timeout,
            )

            # Collect device information
            network_device = self._collect_device_info(device, creds.ip)

            # Collect neighbors
            cdp_neighbors = self._collect_cdp_neighbors(device)
            lldp_neighbors = self._collect_lldp_neighbors(device)

            # Collect interfaces and ports
            interfaces, ports = self._collect_interfaces(device)
            network_device.interfaces = interfaces
            network_device.ports = ports

            # Collect VLAN information
            vlans = self._collect_vlans(device)

            # Collect STP information
            stp_instances = self._collect_stp(device)

            return DiscoveryResult(
                device=network_device,
                cdp_neighbors=cdp_neighbors,
                lldp_neighbors=lldp_neighbors,
                vlans=vlans,
                stp_instances=stp_instances,
            )

        finally:
            if device.is_connected():
                device.disconnect()
                logger.info(f"Disconnected from {creds.hostname}")

    def _collect_device_info(self, device: PyATSDevice, mgmt_ip: str) -> NetworkDevice:
        """Collect basic device information."""
        logger.info(f"Collecting device info from {device.name}")

        try:
            output = device.parse('show version')
            hostname = normalize_hostname(output.get('version', {}).get('hostname', device.name))
            platform = output.get('version', {}).get('platform', 'unknown')
            model = output.get('version', {}).get('chassis', platform)
            serial = output.get('version', {}).get('chassis_sn', 'unknown')
            version = output.get('version', {}).get('version', 'unknown')

            return NetworkDevice(
                hostname=hostname,
                mgmt_ip=mgmt_ip,
                platform=platform,
                model=model,
                serial_number=serial,
                software_version=version,
            )
        except Exception as e:
            logger.warning(f"Error collecting device info: {e}")
            return NetworkDevice(
                hostname=normalize_hostname(device.name),
                mgmt_ip=mgmt_ip,
                platform='unknown',
            )

    def _collect_cdp_neighbors(self, device: PyATSDevice) -> List[CDPNeighbor]:
        """Collect CDP neighbor information."""
        logger.info(f"Collecting CDP neighbors from {device.name}")
        neighbors: List[CDPNeighbor] = []

        try:
            output = device.parse('show cdp neighbors detail')
            cdp_data = output.get('index', {})

            for idx, neighbor_data in cdp_data.items():
                local_intf = neighbor_data.get('local_interface', '')
                neighbor_host = neighbor_data.get('device_id', '')
                neighbor_intf = neighbor_data.get('port_id', '')
                neighbor_ip = neighbor_data.get('management_addresses', {})
                neighbor_ip_addr = list(neighbor_ip.keys())[0] if neighbor_ip else None
                platform = neighbor_data.get('platform', '')
                capabilities = neighbor_data.get('capabilities', '').split()

                if local_intf and neighbor_host and neighbor_intf:
                    neighbors.append(
                        CDPNeighbor(
                            local_interface=normalize_interface_name(local_intf),
                            neighbor_device=normalize_hostname(neighbor_host),
                            neighbor_interface=normalize_interface_name(neighbor_intf),
                            neighbor_ip=neighbor_ip_addr,
                            platform=platform,
                            capabilities=capabilities,
                        )
                    )

        except ParserNotFound:
            logger.warning(f"CDP not supported on {device.name}")
        except Exception as e:
            logger.error(f"Error collecting CDP neighbors: {e}")

        return neighbors

    def _collect_lldp_neighbors(self, device: PyATSDevice) -> List[LLDPNeighbor]:
        """Collect LLDP neighbor information."""
        logger.info(f"Collecting LLDP neighbors from {device.name}")
        neighbors: List[LLDPNeighbor] = []

        try:
            output = device.parse('show lldp neighbors detail')
            lldp_data = output.get('interfaces', {})

            for local_intf, intf_data in lldp_data.items():
                port_id = intf_data.get('port_id', {})
                for neighbor_intf, neighbor_data in port_id.items():
                    neighbor_host = neighbor_data.get('system_name', '')
                    neighbor_ip_list = neighbor_data.get('management_addresses', {})
                    neighbor_ip = list(neighbor_ip_list.keys())[0] if neighbor_ip_list else None
                    system_desc = neighbor_data.get('system_description', '')

                    if local_intf and neighbor_host and neighbor_intf:
                        neighbors.append(
                            LLDPNeighbor(
                                local_interface=normalize_interface_name(local_intf),
                                neighbor_device=normalize_hostname(neighbor_host),
                                neighbor_interface=normalize_interface_name(neighbor_intf),
                                neighbor_ip=neighbor_ip,
                                system_description=system_desc,
                            )
                        )

        except ParserNotFound:
            logger.warning(f"LLDP not supported on {device.name}")
        except Exception as e:
            logger.error(f"Error collecting LLDP neighbors: {e}")

        return neighbors

    def _collect_interfaces(self, device: PyATSDevice) -> tuple[List[Interface], List[Port]]:
        """Collect interface and port information."""
        logger.info(f"Collecting interfaces from {device.name}")
        interfaces: List[Interface] = []
        ports: List[Port] = []

        try:
            output = device.parse('show interfaces')
            intf_data = output

            for intf_name, intf_info in intf_data.items():
                status_raw = intf_info.get('oper_status', 'down')
                status = PortStatus.UP if status_raw == 'up' else PortStatus.DOWN

                # Physical port information
                if 'port_speed' in intf_info or 'duplex_mode' in intf_info:
                    port = Port(
                        name=normalize_interface_name(intf_name),
                        status=status,
                        speed=intf_info.get('port_speed', ''),
                        duplex=intf_info.get('duplex_mode', ''),
                        description=intf_info.get('description', ''),
                    )
                    ports.append(port)

                # Logical interface information
                ipv4_data = intf_info.get('ipv4', {})
                ip_addr = None
                subnet = None

                if ipv4_data:
                    for ip, ip_info in ipv4_data.items():
                        if ip != 'unnumbered':
                            ip_addr = ip
                            subnet = ip_info.get('prefix_length', '')
                            break

                interface = Interface(
                    name=normalize_interface_name(intf_name),
                    ip_address=ip_addr,
                    subnet_mask=subnet,
                    status=status,
                    description=intf_info.get('description', ''),
                )
                interfaces.append(interface)

        except Exception as e:
            logger.error(f"Error collecting interfaces: {e}")

        return interfaces, ports

    def _collect_vlans(self, device: PyATSDevice) -> List[VLANInfo]:
        """Collect VLAN information."""
        logger.info(f"Collecting VLANs from {device.name}")
        vlans: List[VLANInfo] = []

        try:
            output = device.parse('show vlan')
            vlan_data = output.get('vlans', {})

            for vlan_id_str, vlan_info in vlan_data.items():
                try:
                    vlan_id = int(vlan_id_str)
                    name = vlan_info.get('name', f'VLAN{vlan_id}')
                    status = vlan_info.get('state', 'unknown')
                    ports_dict = vlan_info.get('interfaces', {})
                    port_list = list(ports_dict.keys()) if ports_dict else []

                    vlans.append(
                        VLANInfo(
                            vlan_id=vlan_id,
                            name=name,
                            status=status,
                            ports=[normalize_interface_name(p) for p in port_list],
                        )
                    )
                except ValueError:
                    continue

        except ParserNotFound:
            logger.warning(f"VLAN commands not supported on {device.name}")
        except Exception as e:
            logger.error(f"Error collecting VLANs: {e}")

        return vlans

    def _collect_stp(self, device: PyATSDevice) -> List[STPInstance]:
        """Collect STP information."""
        logger.info(f"Collecting STP data from {device.name}")
        stp_instances: List[STPInstance] = []

        try:
            output = device.parse('show spanning-tree')

            # Handle different STP output formats
            if 'mstp' in output:
                stp_data = output['mstp']
            elif 'rapid_pvst' in output:
                stp_data = output['rapid_pvst']
            elif 'pvst' in output:
                stp_data = output['pvst']
            else:
                return stp_instances

            for vlan_id_str, vlan_stp in stp_data.items():
                try:
                    vlan_id = int(vlan_id_str.replace('VLAN', '').replace('MST', ''))
                except ValueError:
                    continue

                bridge_priority = vlan_stp.get('bridge', {}).get('priority', 32768)
                bridge_address = vlan_stp.get('bridge', {}).get('address', '0000.0000.0000')
                root_priority = vlan_stp.get('root', {}).get('priority', bridge_priority)
                root_address = vlan_stp.get('root', {}).get('address', bridge_address)
                root_port = vlan_stp.get('root', {}).get('port', None)
                root_cost = vlan_stp.get('root', {}).get('cost', None)
                is_root = (bridge_address == root_address)

                # Collect interface-level STP data
                stp_interfaces: List[STPInterface] = []
                interfaces_data = vlan_stp.get('interfaces', {})

                for intf_name, intf_stp in interfaces_data.items():
                    stp_intf = STPInterface(
                        interface=normalize_interface_name(intf_name),
                        role=intf_stp.get('role', 'unknown'),
                        state=intf_stp.get('status', 'unknown'),
                        cost=intf_stp.get('cost'),
                        priority=intf_stp.get('priority'),
                        port_id=intf_stp.get('port_num'),
                    )
                    stp_interfaces.append(stp_intf)

                stp_instance = STPInstance(
                    vlan_id=vlan_id,
                    bridge_priority=bridge_priority,
                    bridge_address=bridge_address,
                    root_bridge_priority=root_priority,
                    root_bridge_address=root_address,
                    root_port=root_port,
                    root_path_cost=root_cost,
                    interfaces=stp_interfaces,
                    is_root=is_root,
                )
                stp_instances.append(stp_instance)

        except ParserNotFound:
            logger.warning(f"STP not supported on {device.name}")
        except Exception as e:
            logger.error(f"Error collecting STP data: {e}")

        return stp_instances
