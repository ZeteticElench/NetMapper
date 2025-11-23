import { GraphData, GraphNode, GraphEdge } from './types';
import { ClusterInfo, StatSegment, AGE_COLORS, CLUSTER_BACKGROUNDS } from './cluster-types';
import { ClusterRenderer } from './cluster-renderer';

/**
 * Generate clustered graph data similar to the reference image
 * Three clusters with different demographic distributions
 */
export function generateClusteredGraph(): {
  graphData: GraphData;
  clusters: ClusterInfo[];
} {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  // Define three clusters with different positions and demographics
  const clusterConfigs = [
    {
      id: 'cluster_1',
      label: 'Cluster 1 (Seniors)',
      baseX: -400,
      baseY: -200,
      nodeCount: 20,
      demographics: {
        '<5': 2,
        '5-13': 5,
        '14-17': 3,
        '18-24': 18,
        '25-44': 12,
        '45-64': 22,
        '≥65': 38  // Largest segment
      }
    },
    {
      id: 'cluster_2',
      label: 'Cluster 2 (Youth)',
      baseX: 350,
      baseY: -100,
      nodeCount: 25,
      demographics: {
        '<5': 8,
        '5-13': 42,  // Largest segment
        '14-17': 7,
        '18-24': 15,
        '25-44': 10,
        '45-64': 12,
        '≥65': 6
      }
    },
    {
      id: 'cluster_3',
      label: 'Cluster 3 (Working Age)',
      baseX: -50,
      baseY: 300,
      nodeCount: 22,
      demographics: {
        '<5': 5,
        '5-13': 8,
        '14-17': 4,
        '18-24': 12,
        '25-44': 35,  // Largest segment
        '45-64': 26,
        '≥65': 10
      }
    }
  ];

  let nodeIdCounter = 0;

  // Generate nodes for each cluster
  clusterConfigs.forEach((clusterConfig) => {
    const { id, baseX, baseY, nodeCount, demographics } = clusterConfig;

    for (let i = 0; i < nodeCount; i++) {
      // Position nodes in a circular cluster pattern
      const angle = (i / nodeCount) * Math.PI * 2;
      const radius = 60 + Math.random() * 80;
      const x = baseX + Math.cos(angle) * radius + (Math.random() - 0.5) * 40;
      const y = baseY + Math.sin(angle) * radius + (Math.random() - 0.5) * 40;

      // Randomly assign age group based on demographics
      const ageGroup = sampleFromDistribution(demographics);

      // Some nodes are hub nodes (much larger)
      const isHub = Math.random() < 0.15;
      const importance = isHub ? 0.7 + Math.random() * 0.3 : Math.random() * 0.4;

      nodes.push({
        id: `n${nodeIdCounter}`,
        label: `Node ${nodeIdCounter}`,
        type: 'Person',
        properties: {
          age_group: ageGroup,
          cluster_id: id,
          is_hub: isHub
        },
        x,
        y,
        cluster: id,
        importance
      });

      nodeIdCounter++;
    }
  });

  // Generate edges within clusters (dense internal connections)
  clusterConfigs.forEach(clusterConfig => {
    const clusterNodes = nodes.filter(n => n.cluster === clusterConfig.id);

    // Each node connects to 2-5 random nodes in same cluster
    clusterNodes.forEach(node => {
      const connectionCount = 2 + Math.floor(Math.random() * 4);

      for (let i = 0; i < connectionCount; i++) {
        const target = clusterNodes[Math.floor(Math.random() * clusterNodes.length)];

        if (target.id !== node.id) {
          edges.push({
            source: node.id,
            target: target.id,
            type: 'CONNECTED',
            weight: 0.5 + Math.random() * 1.5
          });
        }
      }
    });

    // Hub nodes get extra connections
    const hubNodes = clusterNodes.filter(n => n.properties.is_hub);
    hubNodes.forEach(hub => {
      const extraConnections = 5 + Math.floor(Math.random() * 5);
      for (let i = 0; i < extraConnections; i++) {
        const target = clusterNodes[Math.floor(Math.random() * clusterNodes.length)];
        if (target.id !== hub.id) {
          edges.push({
            source: hub.id,
            target: target.id,
            type: 'CONNECTED',
            weight: 1.5 + Math.random()
          });
        }
      }
    });
  });

  // Add some inter-cluster edges
  for (let i = 0; i < 15; i++) {
    const sourceCluster = clusterConfigs[Math.floor(Math.random() * clusterConfigs.length)];
    let targetCluster = clusterConfigs[Math.floor(Math.random() * clusterConfigs.length)];

    // Ensure different clusters
    while (targetCluster.id === sourceCluster.id) {
      targetCluster = clusterConfigs[Math.floor(Math.random() * clusterConfigs.length)];
    }

    const sourceNodes = nodes.filter(n => n.cluster === sourceCluster.id);
    const targetNodes = nodes.filter(n => n.cluster === targetCluster.id);

    if (sourceNodes.length > 0 && targetNodes.length > 0) {
      const source = sourceNodes[Math.floor(Math.random() * sourceNodes.length)];
      const target = targetNodes[Math.floor(Math.random() * targetNodes.length)];

      edges.push({
        source: source.id,
        target: target.id,
        type: 'INTER_CLUSTER',
        weight: 0.8
      });
    }
  }

  // Calculate degrees
  const degreeMap = new Map<string, number>();
  edges.forEach(edge => {
    degreeMap.set(edge.source, (degreeMap.get(edge.source) || 0) + 1);
    degreeMap.set(edge.target, (degreeMap.get(edge.target) || 0) + 1);
  });
  nodes.forEach(node => {
    node.degree = degreeMap.get(node.id) || 0;
  });

  // Build cluster info with statistics
  const clusters: ClusterInfo[] = clusterConfigs.map((config, index) => {
    const bounds = ClusterRenderer.calculateClusterBounds(nodes, config.id, 80);
    const clusterNodes = nodes.filter(n => n.cluster === config.id);

    // Calculate actual age distribution from nodes
    const ageGroups = Object.keys(config.demographics) as Array<keyof typeof config.demographics>;
    const segments: StatSegment[] = ageGroups.map(ageGroup => {
      const percentage = config.demographics[ageGroup];
      return {
        label: ageGroup,
        value: Math.round((percentage / 100) * clusterNodes.length),
        percentage,
        color: AGE_COLORS[ageGroup]
      };
    });

    return {
      id: config.id,
      label: config.label,
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
    clusters
  };
}

/**
 * Sample an age group from demographic distribution
 */
function sampleFromDistribution(distribution: Record<string, number>): string {
  const total = Object.values(distribution).reduce((sum, val) => sum + val, 0);
  let random = Math.random() * total;

  for (const [key, value] of Object.entries(distribution)) {
    random -= value;
    if (random <= 0) {
      return key;
    }
  }

  return Object.keys(distribution)[0];
}
