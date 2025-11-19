/**
 * DataGenerator.js
 * Generates sample network infrastructure data for visualization
 *
 * Hierarchy: Data Center -> Rack -> Device -> Interface
 * Topology: Interface connections (edges)
 */

const STATUSES = ['up', 'down', 'warning'];
const DEVICE_TYPES = ['switch', 'router', 'firewall'];
const INTERFACE_TYPES = ['GigabitEthernet', 'TenGigabitEthernet', 'Port-Channel'];

/**
 * Generate random status with weighted probability
 * 70% up, 20% warning, 10% down
 */
const randomStatus = () => {
  const rand = Math.random();
  if (rand < 0.7) return 'up';
  if (rand < 0.9) return 'warning';
  return 'down';
};

/**
 * Generate a random IP address
 */
const randomIP = (subnet = '10.0') => {
  const oct3 = Math.floor(Math.random() * 255);
  const oct4 = Math.floor(Math.random() * 255);
  return `${subnet}.${oct3}.${oct4}`;
};

/**
 * Generate a sample interface
 */
const generateInterface = (deviceId, deviceName, index, deviceIP) => {
  const type = INTERFACE_TYPES[Math.floor(Math.random() * INTERFACE_TYPES.length)];
  const portNum = index + 1;
  const name = `${type}0/0/${portNum}`;

  return {
    id: `${deviceId}-int-${index}`,
    name,
    deviceId,
    deviceName,
    type: 'interface',
    status: randomStatus(),
    speed: type.includes('Ten') ? '10G' : '1G',
    ip: randomIP(),
    vlan: Math.floor(Math.random() * 100) + 1,
    description: `Port ${portNum} on ${deviceName}`,
    deviceIP,
    config: `interface ${name}
 description Port ${portNum}
 switchport mode access
 switchport access vlan ${Math.floor(Math.random() * 100) + 1}
 spanning-tree portfast
 no shutdown`,
  };
};

/**
 * Generate a sample device (switch/router/firewall)
 */
const generateDevice = (rackId, rackName, dcName, index, dcIndex, rackIndex) => {
  const deviceType = DEVICE_TYPES[Math.floor(Math.random() * DEVICE_TYPES.length)];
  const deviceName = `${deviceType}-${dcIndex + 1}-${rackIndex + 1}-${index + 1}`;
  const deviceId = `${rackId}-dev-${index}`;
  const deviceIP = randomIP(`10.${dcIndex}.${rackIndex}`);

  // Each device has 4-8 interfaces
  const interfaceCount = 4 + Math.floor(Math.random() * 5);
  const interfaces = Array.from({ length: interfaceCount }, (_, i) =>
    generateInterface(deviceId, deviceName, i, deviceIP)
  );

  return {
    id: deviceId,
    name: deviceName,
    rackId,
    rackName,
    dcName,
    type: 'device',
    deviceType,
    status: interfaces.some(i => i.status === 'down') ? 'warning' : 'up',
    model: `Catalyst ${3000 + Math.floor(Math.random() * 6000)}`,
    ip: deviceIP,
    serialNumber: `SN${Math.random().toString(36).substr(2, 9).toUpperCase()}`,
    version: `IOS ${15 + Math.floor(Math.random() * 2)}.${Math.floor(Math.random() * 10)}`,
    children: interfaces,
  };
};

/**
 * Generate a sample rack
 */
const generateRack = (dcId, dcName, index, dcIndex) => {
  const rackName = `Rack-${String.fromCharCode(65 + index)}`;
  const rackId = `${dcId}-rack-${index}`;

  // Each rack has 2-4 devices
  const deviceCount = 2 + Math.floor(Math.random() * 3);
  const devices = Array.from({ length: deviceCount }, (_, i) =>
    generateDevice(rackId, rackName, dcName, i, dcIndex, index)
  );

  return {
    id: rackId,
    name: rackName,
    dcId,
    dcName,
    type: 'rack',
    status: devices.some(d => d.status === 'warning') ? 'warning' : 'up',
    location: `Row ${index + 1}`,
    children: devices,
  };
};

/**
 * Generate a sample data center
 */
const generateDataCenter = (index) => {
  const dcName = `DC-${index + 1}`;
  const dcId = `dc-${index}`;

  // Each data center has 2-3 racks
  const rackCount = 2 + Math.floor(Math.random() * 2);
  const racks = Array.from({ length: rackCount }, (_, i) =>
    generateRack(dcId, dcName, i, index)
  );

  return {
    id: dcId,
    name: dcName,
    type: 'datacenter',
    status: racks.some(r => r.status === 'warning') ? 'warning' : 'up',
    location: `Region ${index + 1}`,
    children: racks,
  };
};

/**
 * Generate connections between interfaces
 * Creates a realistic network topology with:
 * - Core switches connected to each other
 * - Distribution switches connected to core
 * - Access switches connected to distribution
 */
const generateConnections = (hierarchy) => {
  const connections = [];
  const allInterfaces = [];

  // Flatten hierarchy to get all interfaces
  hierarchy.children.forEach(dc => {
    dc.children.forEach(rack => {
      rack.children.forEach(device => {
        device.children.forEach(iface => {
          allInterfaces.push({
            ...iface,
            deviceType: device.deviceType,
            rackId: rack.id,
            dcId: dc.id,
          });
        });
      });
    });
  });

  // Connect interfaces across devices
  // Strategy: Connect each device's first interface to 1-3 other devices
  const deviceInterfaces = {};
  allInterfaces.forEach(iface => {
    if (!deviceInterfaces[iface.deviceId]) {
      deviceInterfaces[iface.deviceId] = [];
    }
    deviceInterfaces[iface.deviceId].push(iface);
  });

  const deviceIds = Object.keys(deviceInterfaces);

  deviceIds.forEach((deviceId, index) => {
    const interfaces = deviceInterfaces[deviceId];
    const primaryInterface = interfaces[0];

    // Connect to 1-3 other devices
    const connectionCount = 1 + Math.floor(Math.random() * 3);

    for (let i = 0; i < connectionCount; i++) {
      // Find a different device to connect to
      const targetDeviceIndex = (index + i + 1) % deviceIds.length;
      const targetDeviceId = deviceIds[targetDeviceIndex];

      if (targetDeviceId !== deviceId) {
        const targetInterfaces = deviceInterfaces[targetDeviceId];
        const targetInterface = targetInterfaces[Math.floor(Math.random() * targetInterfaces.length)];

        // Avoid duplicate connections
        const existingConnection = connections.find(c =>
          (c.source === primaryInterface.id && c.target === targetInterface.id) ||
          (c.source === targetInterface.id && c.target === primaryInterface.id)
        );

        if (!existingConnection) {
          connections.push({
            id: `conn-${connections.length}`,
            source: primaryInterface.id,
            target: targetInterface.id,
            sourceDevice: primaryInterface.deviceId,
            targetDevice: targetInterface.deviceId,
            type: 'fiber',
            speed: primaryInterface.speed,
            status: primaryInterface.status === 'up' && targetInterface.status === 'up' ? 'up' : 'down',
          });
        }
      }
    }
  });

  return connections;
};

/**
 * Generate complete network infrastructure data
 * Returns both hierarchy (for D3) and topology (for Cytoscape)
 */
export const generateNetworkData = (datacenters = 2) => {
  // Generate hierarchy
  const hierarchy = {
    name: 'Network Infrastructure',
    type: 'root',
    children: Array.from({ length: datacenters }, (_, i) => generateDataCenter(i)),
  };

  // Generate connections
  const connections = generateConnections(hierarchy);

  // Create topology data (flat structure for Cytoscape)
  const topologyNodes = [];
  const topologyEdges = [];

  hierarchy.children.forEach(dc => {
    // Add datacenter node
    topologyNodes.push({
      data: {
        id: dc.id,
        label: dc.name,
        type: 'datacenter',
        status: dc.status,
      }
    });

    dc.children.forEach(rack => {
      // Add rack node
      topologyNodes.push({
        data: {
          id: rack.id,
          label: rack.name,
          type: 'rack',
          status: rack.status,
          parent: dc.id, // Compound node
        }
      });

      rack.children.forEach(device => {
        // Add device node
        topologyNodes.push({
          data: {
            id: device.id,
            label: device.name,
            type: 'device',
            deviceType: device.deviceType,
            status: device.status,
            parent: rack.id, // Compound node
            ip: device.ip,
            model: device.model,
          }
        });

        device.children.forEach(iface => {
          // Add interface node
          topologyNodes.push({
            data: {
              id: iface.id,
              label: iface.name,
              type: 'interface',
              status: iface.status,
              parent: device.id, // Compound node
              speed: iface.speed,
              ip: iface.ip,
              vlan: iface.vlan,
              description: iface.description,
              deviceIP: iface.deviceIP,
              deviceName: iface.deviceName,
              config: iface.config,
            }
          });
        });
      });
    });
  });

  // Add edges
  connections.forEach(conn => {
    topologyEdges.push({
      data: {
        id: conn.id,
        source: conn.source,
        target: conn.target,
        type: conn.type,
        speed: conn.speed,
        status: conn.status,
      }
    });
  });

  return {
    hierarchy,
    topology: {
      nodes: topologyNodes,
      edges: topologyEdges,
    },
    connections,
  };
};

export default generateNetworkData;
