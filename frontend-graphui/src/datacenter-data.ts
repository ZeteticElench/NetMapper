import { GraphData, GraphNode, GraphEdge } from './types';
import { ClusterInfo, CLUSTER_BACKGROUNDS } from './cluster-types';
import { HierarchicalNode, NodeMetrics, STATUS_COLORS } from './hierarchy-types';
import { ClusterRenderer } from './cluster-renderer';

/**
 * Generate a hierarchical data center infrastructure graph
 * Level 1: Data Centers
 * Level 2: Racks
 * Level 3: Servers
 * Level 4: Processes
 */
export function generateDataCenterGraph(): {
  graphData: GraphData;
  clusters: ClusterInfo[];
  hierarchyMap: Map<string, HierarchicalNode>;
} {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const hierarchyMap = new Map<string, HierarchicalNode>();

  // Define 3 data centers
  const dataCenters = [
    {
      id: 'dc1',
      label: 'US-East-1',
      x: -400,
      y: 0,
      racks: 5,
      metrics: { pue: 1.2, totalPower: 850, bandwidth: 400, temperature: 22 },
      status: 'healthy' as const
    },
    {
      id: 'dc2',
      label: 'US-West-2',
      x: 0,
      y: 0,
      racks: 4,
      metrics: { pue: 1.4, totalPower: 620, bandwidth: 300, temperature: 25 },
      status: 'warning' as const
    },
    {
      id: 'dc3',
      label: 'EU-Central-1',
      x: 400,
      y: 0,
      racks: 6,
      metrics: { pue: 1.1, totalPower: 990, bandwidth: 500, temperature: 21 },
      status: 'healthy' as const
    }
  ];

  // Generate data centers, racks, servers, and processes
  dataCenters.forEach((dc) => {
    // Create data center node
    const dcNode: GraphNode = {
      id: dc.id,
      label: dc.label,
      type: 'DataCenter',
      properties: {
        level: 'datacenter',
        pue: dc.metrics.pue,
        totalPower: dc.metrics.totalPower,
        bandwidth: dc.metrics.bandwidth,
        temperature: dc.metrics.temperature,
        status: dc.status
      },
      x: dc.x,
      y: dc.y,
      cluster: dc.id,
      importance: 1.0
    };

    nodes.push(dcNode);
    hierarchyMap.set(dc.id, {
      ...dcNode,
      level: 'datacenter',
      metrics: dc.metrics,
      status: dc.status,
      children: []
    });

    // Generate racks for this data center
    for (let r = 0; r < dc.racks; r++) {
      const rackId = `${dc.id}_rack${r}`;
      const angle = (r / dc.racks) * Math.PI * 2;
      const radius = 150;

      const rackMetrics: NodeMetrics = {
        powerPhaseA: 15 + Math.random() * 10,
        powerPhaseB: 14 + Math.random() * 10,
        usedRackUnits: Math.floor(30 + Math.random() * 12),
        totalRackUnits: 42,
        switchPorts: { used: Math.floor(20 + Math.random() * 24), total: 48 }
      };

      const rackStatus = rackMetrics.powerPhaseA! > 22 ? 'warning' : 'healthy';

      const rackNode: GraphNode = {
        id: rackId,
        label: `Rack ${r + 1}`,
        type: 'Rack',
        properties: {
          level: 'rack',
          parentId: dc.id,
          ...rackMetrics,
          status: rackStatus
        },
        x: dc.x + Math.cos(angle) * radius,
        y: dc.y + Math.sin(angle) * radius,
        cluster: dc.id,
        importance: 0.6 + Math.random() * 0.3
      };

      nodes.push(rackNode);
      hierarchyMap.set(rackId, {
        ...rackNode,
        level: 'rack',
        parentId: dc.id,
        metrics: rackMetrics,
        status: rackStatus,
        children: []
      });
      hierarchyMap.get(dc.id)!.children!.push(rackId);

      // Add edge from DC to Rack
      edges.push({
        source: dc.id,
        target: rackId,
        type: 'CONTAINS',
        weight: 1.5
      });

      // Generate servers for this rack
      const serverCount = 6 + Math.floor(Math.random() * 6);
      for (let s = 0; s < serverCount; s++) {
        const serverId = `${rackId}_srv${s}`;
        const serverAngle = (s / serverCount) * Math.PI * 2;
        const serverRadius = 60;

        const osTypes = ['Linux', 'Windows', 'ESXi', 'Linux', 'Linux']; // More Linux
        const osType = osTypes[Math.floor(Math.random() * osTypes.length)];

        const serverMetrics: NodeMetrics = {
          cpuCores: [16, 32, 64, 128][Math.floor(Math.random() * 4)],
          ramGB: [64, 128, 256, 512][Math.floor(Math.random() * 4)],
          cpuUsage: 20 + Math.random() * 60,
          ramUsage: 30 + Math.random() * 50,
          diskIOPS: Math.floor(1000 + Math.random() * 5000),
          networkThroughput: Math.floor(100 + Math.random() * 900)
        };

        const serverStatus =
          serverMetrics.cpuUsage! > 80 ? 'critical' :
          serverMetrics.cpuUsage! > 65 ? 'warning' : 'healthy';

        const serverNode: GraphNode = {
          id: serverId,
          label: `Server-${s + 1}`,
          type: osType,
          properties: {
            level: 'server',
            parentId: rackId,
            os: osType,
            ...serverMetrics,
            status: serverStatus
          },
          x: rackNode.x + Math.cos(serverAngle) * serverRadius,
          y: rackNode.y + Math.sin(serverAngle) * serverRadius,
          cluster: dc.id,
          importance: 0.3 + Math.random() * 0.4
        };

        nodes.push(serverNode);
        hierarchyMap.set(serverId, {
          ...serverNode,
          level: 'server',
          parentId: rackId,
          metrics: serverMetrics,
          status: serverStatus,
          children: []
        });
        hierarchyMap.get(rackId)!.children!.push(serverId);

        // Add edge from Rack to Server
        edges.push({
          source: rackId,
          target: serverId,
          type: 'HOSTS',
          weight: 1.0
        });

        // Generate processes for this server
        const processCount = 4 + Math.floor(Math.random() * 6);
        for (let p = 0; p < processCount; p++) {
          const processId = `${serverId}_proc${p}`;
          const processAngle = (p / processCount) * Math.PI * 2;
          const processRadius = 30;

          const processNames = ['nginx', 'postgres', 'redis', 'api-server', 'worker', 'kafka'];
          const processName = processNames[Math.floor(Math.random() * processNames.length)];

          const processMetrics: NodeMetrics = {
            memoryMB: Math.floor(100 + Math.random() * 2000),
            cpuPercent: Math.random() * 50,
            threads: Math.floor(1 + Math.random() * 20),
            connections: Math.floor(Math.random() * 200)
          };

          const processStatus = processMetrics.cpuPercent! > 40 ? 'warning' : 'healthy';

          const processNode: GraphNode = {
            id: processId,
            label: processName,
            type: 'Process',
            properties: {
              level: 'process',
              parentId: serverId,
              ...processMetrics,
              status: processStatus
            },
            x: serverNode.x + Math.cos(processAngle) * processRadius,
            y: serverNode.y + Math.sin(processAngle) * processRadius,
            cluster: dc.id,
            importance: 0.1 + Math.random() * 0.2
          };

          nodes.push(processNode);
          hierarchyMap.set(processId, {
            ...processNode,
            level: 'process',
            parentId: serverId,
            metrics: processMetrics,
            status: processStatus
          });
          hierarchyMap.get(serverId)!.children!.push(processId);

          // Add edge from Server to Process
          edges.push({
            source: serverId,
            target: processId,
            type: 'RUNS',
            weight: 0.5
          });
        }
      }

      // Add some inter-rack network connections (spine-leaf)
      if (r > 0) {
        const prevRackId = `${dc.id}_rack${r - 1}`;
        edges.push({
          source: prevRackId,
          target: rackId,
          type: 'NETWORK',
          weight: 2.0,
          properties: { bandwidth: '100GbE' }
        });
      }
    }

    // Add inter-server traffic within racks (east-west)
    const dcRacks = Array.from(hierarchyMap.values()).filter(n =>
      n.level === 'rack' && n.parentId === dc.id
    );

    dcRacks.forEach(rack => {
      const servers = rack.children?.map(id => hierarchyMap.get(id)!).filter(n => n) || [];

      // Random server-to-server connections
      for (let i = 0; i < servers.length; i++) {
        const connectionCount = Math.floor(Math.random() * 3);
        for (let j = 0; j < connectionCount; j++) {
          const targetServer = servers[Math.floor(Math.random() * servers.length)];
          if (targetServer && targetServer.id !== servers[i].id) {
            edges.push({
              source: servers[i].id,
              target: targetServer.id,
              type: 'TRAFFIC',
              weight: 0.5 + Math.random()
            });
          }
        }
      }
    });
  });

  // Add inter-datacenter connections
  edges.push(
    { source: 'dc1', target: 'dc2', type: 'WAN', weight: 2.5, properties: { latency: '45ms' } },
    { source: 'dc2', target: 'dc3', type: 'WAN', weight: 2.5, properties: { latency: '120ms' } },
    { source: 'dc1', target: 'dc3', type: 'WAN', weight: 2.5, properties: { latency: '85ms' } }
  );

  // Calculate degrees
  const degreeMap = new Map<string, number>();
  edges.forEach(edge => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
  });
  nodes.forEach(node => {
    node.degree = degreeMap.get(node.id) || 0;
  });

  // Build clusters (one per data center)
  const clusters: ClusterInfo[] = dataCenters.map((dc, index) => {
    const clusterNodes = nodes.filter(n => n.cluster === dc.id);
    const bounds = ClusterRenderer.calculateClusterBounds(clusterNodes, dc.id, 200);

    // Create ring segments for data center metrics
    const segments = [
      {
        label: `PUE ${dc.metrics.pue}`,
        value: dc.metrics.pue,
        percentage: (dc.metrics.pue / 2.0) * 100, // Normalize to 0-100%
        color: dc.metrics.pue < 1.3 ? STATUS_COLORS.healthy : STATUS_COLORS.warning
      },
      {
        label: `${dc.metrics.totalPower}kW`,
        value: dc.metrics.totalPower,
        percentage: (dc.metrics.totalPower / 1000) * 100,
        color: dc.metrics.totalPower > 800 ? STATUS_COLORS.warning : STATUS_COLORS.healthy
      },
      {
        label: `${dc.metrics.bandwidth}Gbps`,
        value: dc.metrics.bandwidth,
        percentage: (dc.metrics.bandwidth / 500) * 100,
        color: STATUS_COLORS.healthy
      },
      {
        label: `${dc.metrics.temperature}°C`,
        value: dc.metrics.temperature,
        percentage: (dc.metrics.temperature / 30) * 100,
        color: dc.metrics.temperature > 24 ? STATUS_COLORS.warning : STATUS_COLORS.healthy
      }
    ];

    return {
      id: dc.id,
      label: dc.label,
      centerX: bounds.centerX,
      centerY: bounds.centerY,
      radius: bounds.radius,
      backgroundColor: CLUSTER_BACKGROUNDS[index % CLUSTER_BACKGROUNDS.length],
      nodeIds: new Set(clusterNodes.map(n => n.id)),
      statistics: {
        segments,
        totalCount: clusterNodes.length
      }
    };
  });

  return {
    graphData: { nodes, edges },
    clusters,
    hierarchyMap
  };
}

/**
 * Filter graph data by hierarchy level
 */
export function filterByLevel(
  hierarchyMap: Map<string, HierarchicalNode>,
  graphData: GraphData,
  currentParentId: string | null
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  if (currentParentId === null) {
    // Show top level (data centers)
    const nodes = graphData.nodes.filter(n => n.properties.level === 'datacenter');
    const nodeIds = new Set(nodes.map(n => n.id));
    const edges = graphData.edges.filter(e =>
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );
    return { nodes, edges };
  }

  // Show children of current parent
  const parent = hierarchyMap.get(currentParentId);
  if (!parent || !parent.children) {
    return { nodes: [], edges: [] };
  }

  const childIds = new Set(parent.children);
  const nodes = graphData.nodes.filter(n => childIds.has(n.id));
  const edges = graphData.edges.filter(e =>
    childIds.has(e.source) && childIds.has(e.target)
  );

  return { nodes, edges };
}
