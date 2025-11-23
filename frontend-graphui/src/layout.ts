import { GraphNode, GraphEdge } from './types';

export class GraphLayout {
  private width: number;
  private height: number;

  constructor(width: number, height: number) {
    this.width = width;
    this.height = height;
  }

  setSize(width: number, height: number) {
    this.width = width;
    this.height = height;
  }

  /**
   * Force-directed layout using simplified physics simulation
   */
  applyForceLayout(
    nodes: GraphNode[],
    edges: GraphEdge[],
    iterations: number = 100
  ): void {
    const centerX = this.width / 2;
    const centerY = this.height / 2;

    // Initialize positions if not set
    nodes.forEach((node, i) => {
      if (node.x === undefined || node.y === undefined) {
        const angle = (i / nodes.length) * Math.PI * 2;
        const radius = Math.min(this.width, this.height) * 0.3;
        node.x = centerX + Math.cos(angle) * radius;
        node.y = centerY + Math.sin(angle) * radius;
      }
      node.vx = node.vx || 0;
      node.vy = node.vy || 0;
    });

    // Build adjacency map
    const adjacency = new Map<string, Set<string>>();
    nodes.forEach(n => adjacency.set(n.id, new Set()));

    edges.forEach(edge => {
      adjacency.get(edge.source)?.add(edge.target);
      adjacency.get(edge.target)?.add(edge.source);
    });

    // Calculate node degrees
    nodes.forEach(node => {
      node.degree = adjacency.get(node.id)?.size || 0;
    });

    // Force simulation
    const k = Math.sqrt((this.width * this.height) / nodes.length);
    const repulsion = k * k;
    const attraction = k;

    for (let iter = 0; iter < iterations; iter++) {
      const temperature = 1 - iter / iterations;

      // Reset forces
      nodes.forEach(node => {
        node.vx = 0;
        node.vy = 0;
      });

      // Repulsive forces (all pairs)
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const nodeA = nodes[i];
          const nodeB = nodes[j];

          const dx = nodeB.x - nodeA.x;
          const dy = nodeB.y - nodeA.y;
          const distSq = dx * dx + dy * dy + 0.01; // Avoid division by zero
          const dist = Math.sqrt(distSq);

          const force = repulsion / distSq;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          nodeA.vx! -= fx;
          nodeA.vy! -= fy;
          nodeB.vx! += fx;
          nodeB.vy! += fy;
        }
      }

      // Attractive forces (edges)
      edges.forEach(edge => {
        const source = nodes.find(n => n.id === edge.source);
        const target = nodes.find(n => n.id === edge.target);

        if (!source || !target) return;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy + 0.01);

        const force = (dist * dist) / attraction;
        const fx = (dx / dist) * force * 0.5;
        const fy = (dy / dist) * force * 0.5;

        source.vx! += fx;
        source.vy! += fy;
        target.vx! -= fx;
        target.vy! -= fy;
      });

      // Gravity towards center
      nodes.forEach(node => {
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        node.vx! += dx * 0.01;
        node.vy! += dy * 0.01;
      });

      // Apply forces with dampening
      nodes.forEach(node => {
        const dampening = 0.9;
        const maxVelocity = 10;

        node.vx = Math.max(-maxVelocity, Math.min(maxVelocity, node.vx! * dampening));
        node.vy = Math.max(-maxVelocity, Math.min(maxVelocity, node.vy! * dampening));

        node.x += node.vx! * temperature;
        node.y += node.vy! * temperature;
      });
    }
  }

  /**
   * Cluster-based layout for categorical data
   */
  applyClusterLayout(nodes: GraphNode[], edges: GraphEdge[]): void {
    // Group nodes by type
    const clusters = new Map<string, GraphNode[]>();
    nodes.forEach(node => {
      const type = node.type || 'default';
      if (!clusters.has(type)) {
        clusters.set(type, []);
      }
      clusters.get(type)!.push(node);
    });

    const numClusters = clusters.size;
    const clusterRadius = Math.min(this.width, this.height) * 0.15;
    const centerX = this.width / 2;
    const centerY = this.height / 2;
    const orbitRadius = Math.min(this.width, this.height) * 0.3;

    let clusterIndex = 0;
    clusters.forEach((clusterNodes, type) => {
      const angle = (clusterIndex / numClusters) * Math.PI * 2;
      const clusterX = centerX + Math.cos(angle) * orbitRadius;
      const clusterY = centerY + Math.sin(angle) * orbitRadius;

      // Arrange nodes in cluster
      clusterNodes.forEach((node, i) => {
        const nodeAngle = (i / clusterNodes.length) * Math.PI * 2;
        const nodeRadius = clusterRadius * Math.sqrt(i / clusterNodes.length);
        node.x = clusterX + Math.cos(nodeAngle) * nodeRadius;
        node.y = clusterY + Math.sin(nodeAngle) * nodeRadius;
        node.cluster = type;
      });

      clusterIndex++;
    });

    // Refine with force layout
    this.applyForceLayout(nodes, edges, 50);
  }

  /**
   * Hierarchical layout for tree-like structures
   */
  applyHierarchicalLayout(nodes: GraphNode[], edges: GraphEdge[]): void {
    // Find root nodes (nodes with no incoming edges)
    const hasIncoming = new Set<string>();
    edges.forEach(edge => hasIncoming.add(edge.target));
    const roots = nodes.filter(n => !hasIncoming.has(n.id));

    if (roots.length === 0 && nodes.length > 0) {
      roots.push(nodes[0]); // Fallback to first node
    }

    // Build adjacency list
    const children = new Map<string, string[]>();
    edges.forEach(edge => {
      if (!children.has(edge.source)) {
        children.set(edge.source, []);
      }
      children.get(edge.source)!.push(edge.target);
    });

    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    const levels = new Map<string, number>();
    const visited = new Set<string>();

    // BFS to assign levels
    const queue: [string, number][] = roots.map(r => [r.id, 0]);
    while (queue.length > 0) {
      const [nodeId, level] = queue.shift()!;
      if (visited.has(nodeId)) continue;

      visited.add(nodeId);
      levels.set(nodeId, level);

      const nodeChildren = children.get(nodeId) || [];
      nodeChildren.forEach(childId => {
        queue.push([childId, level + 1]);
      });
    }

    // Group by level
    const levelGroups = new Map<number, string[]>();
    levels.forEach((level, nodeId) => {
      if (!levelGroups.has(level)) {
        levelGroups.set(level, []);
      }
      levelGroups.get(level)!.push(nodeId);
    });

    const maxLevel = Math.max(...Array.from(levels.values()), 0);
    const levelHeight = this.height / (maxLevel + 2);

    // Position nodes
    levelGroups.forEach((nodeIds, level) => {
      const y = levelHeight * (level + 1);
      const spacing = this.width / (nodeIds.length + 1);

      nodeIds.forEach((nodeId, index) => {
        const node = nodeMap.get(nodeId);
        if (node) {
          node.x = spacing * (index + 1);
          node.y = y;
        }
      });
    });
  }

  /**
   * Randomize positions for testing
   */
  randomize(nodes: GraphNode[]): void {
    const padding = 100;
    nodes.forEach(node => {
      node.x = padding + Math.random() * (this.width - 2 * padding);
      node.y = padding + Math.random() * (this.height - 2 * padding);
    });
  }
}
