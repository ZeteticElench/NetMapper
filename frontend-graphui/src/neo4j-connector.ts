import neo4j, { Driver } from 'neo4j-driver';
import { GraphData, GraphNode, GraphEdge } from './types';
import { ClusterInfo, CLUSTER_BACKGROUNDS } from './cluster-types';
import { ClusterRenderer } from './cluster-renderer';

export interface Neo4jConfig {
  uri: string;
  username: string;
  password: string;
  database?: string;
}

export class Neo4jConnector {
  private driver: Driver | null = null;
  private config: Neo4jConfig | null = null;

  /**
   * Connect to Neo4j database
   */
  async connect(config: Neo4jConfig): Promise<void> {
    try {
      this.config = config;
      this.driver = neo4j.driver(
        config.uri,
        neo4j.auth.basic(config.username, config.password)
      );

      // Test connection
      const serverInfo = await this.driver.getServerInfo();
      console.log('Connected to Neo4j:', serverInfo.address);
    } catch (error) {
      console.error('Failed to connect to Neo4j:', error);
      throw error;
    }
  }

  /**
   * Disconnect from Neo4j
   */
  async disconnect(): Promise<void> {
    if (this.driver) {
      await this.driver.close();
      this.driver = null;
      this.config = null;
    }
  }

  /**
   * Execute a custom Cypher query and return graph data
   */
  async executeQuery(
    cypher: string,
    params: Record<string, any> = {}
  ): Promise<{ graphData: GraphData; clusters: ClusterInfo[] }> {
    if (!this.driver) {
      throw new Error('Not connected to Neo4j');
    }

    const session = this.driver.session({
      database: this.config?.database || 'neo4j'
    });

    try {
      const result = await session.run(cypher, params);

      const nodes = new Map<string, GraphNode>();
      const edges: GraphEdge[] = [];

      result.records.forEach(record => {
        // Extract nodes from record
        record.keys.forEach(key => {
          const value = record.get(key);

          if (value && typeof value === 'object') {
            // Neo4j node
            if ('labels' in value && 'properties' in value && 'identity' in value) {
              const nodeId = value.identity.toString();

              if (!nodes.has(nodeId)) {
                nodes.set(nodeId, {
                  id: nodeId,
                  label: value.properties.name || value.properties.title || nodeId,
                  type: value.labels[0] || 'Unknown',
                  properties: { ...value.properties },
                  x: 0,
                  y: 0,
                  cluster: value.properties.cluster || value.labels[0]
                });
              }
            }
            // Neo4j relationship
            else if ('type' in value && 'start' in value && 'end' in value) {
              edges.push({
                source: value.start.toString(),
                target: value.end.toString(),
                type: value.type,
                weight: value.properties?.weight || 1,
                properties: value.properties
              });
            }
            // Path
            else if ('segments' in value) {
              value.segments.forEach((segment: any) => {
                // Add nodes
                const startId = segment.start.identity.toString();
                const endId = segment.end.identity.toString();

                if (!nodes.has(startId)) {
                  nodes.set(startId, {
                    id: startId,
                    label: segment.start.properties.name || startId,
                    type: segment.start.labels[0] || 'Unknown',
                    properties: { ...segment.start.properties },
                    x: 0,
                    y: 0,
                    cluster: segment.start.properties.cluster || segment.start.labels[0]
                  });
                }

                if (!nodes.has(endId)) {
                  nodes.set(endId, {
                    id: endId,
                    label: segment.end.properties.name || endId,
                    type: segment.end.labels[0] || 'Unknown',
                    properties: { ...segment.end.properties },
                    x: 0,
                    y: 0,
                    cluster: segment.end.properties.cluster || segment.end.labels[0]
                  });
                }

                // Add relationship
                edges.push({
                  source: startId,
                  target: endId,
                  type: segment.relationship.type,
                  weight: segment.relationship.properties?.weight || 1,
                  properties: segment.relationship.properties
                });
              });
            }
          }
        });
      });

      const nodeArray = Array.from(nodes.values());

      // Calculate clusters
      const clusters = this.calculateClusters(nodeArray);

      return {
        graphData: { nodes: nodeArray, edges },
        clusters
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Load graph with limit
   */
  async loadGraph(limit: number = 100): Promise<{ graphData: GraphData; clusters: ClusterInfo[] }> {
    const cypher = `
      MATCH (n)
      WITH n LIMIT $limit
      OPTIONAL MATCH (n)-[r]-(m)
      RETURN n, r, m
    `;

    return this.executeQuery(cypher, { limit });
  }

  /**
   * Load graph by node label/type
   */
  async loadByLabel(
    label: string,
    limit: number = 100
  ): Promise<{ graphData: GraphData; clusters: ClusterInfo[] }> {
    const cypher = `
      MATCH (n:${label})
      WITH n LIMIT $limit
      OPTIONAL MATCH (n)-[r]-(m)
      RETURN n, r, m
    `;

    return this.executeQuery(cypher, { limit });
  }

  /**
   * Load neighborhood around a specific node
   */
  async loadNeighborhood(
    nodeId: string,
    depth: number = 2
  ): Promise<{ graphData: GraphData; clusters: ClusterInfo[] }> {
    const cypher = `
      MATCH path = (start)-[*1..${depth}]-(end)
      WHERE id(start) = $nodeId
      RETURN path
      LIMIT 200
    `;

    return this.executeQuery(cypher, { nodeId: parseInt(nodeId) });
  }

  /**
   * Get available node labels
   */
  async getLabels(): Promise<string[]> {
    if (!this.driver) {
      throw new Error('Not connected to Neo4j');
    }

    const session = this.driver.session();
    try {
      const result = await session.run('CALL db.labels()');
      return result.records.map(record => record.get(0));
    } finally {
      await session.close();
    }
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<{ nodeCount: number; relationshipCount: number }> {
    if (!this.driver) {
      throw new Error('Not connected to Neo4j');
    }

    const session = this.driver.session();
    try {
      const nodeResult = await session.run('MATCH (n) RETURN count(n) as count');
      const relResult = await session.run('MATCH ()-[r]->() RETURN count(r) as count');

      return {
        nodeCount: nodeResult.records[0]?.get('count').toNumber() || 0,
        relationshipCount: relResult.records[0]?.get('count').toNumber() || 0
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Calculate clusters from nodes
   */
  private calculateClusters(nodes: GraphNode[]): ClusterInfo[] {
    // Group by cluster field
    const clusterGroups = new Map<string, GraphNode[]>();

    nodes.forEach(node => {
      const clusterId = node.cluster || 'default';
      if (!clusterGroups.has(clusterId)) {
        clusterGroups.set(clusterId, []);
      }
      clusterGroups.get(clusterId)!.push(node);
    });

    const clusters: ClusterInfo[] = [];
    let colorIndex = 0;

    clusterGroups.forEach((clusterNodes, clusterId) => {
      const bounds = ClusterRenderer.calculateClusterBounds(clusterNodes, clusterId, 80);

      clusters.push({
        id: clusterId,
        label: clusterId,
        centerX: bounds.centerX,
        centerY: bounds.centerY,
        radius: bounds.radius,
        backgroundColor: CLUSTER_BACKGROUNDS[colorIndex % CLUSTER_BACKGROUNDS.length],
        nodeIds: new Set(clusterNodes.map(n => n.id)),
        statistics: undefined // Can be calculated based on node properties
      });

      colorIndex++;
    });

    return clusters;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.driver !== null;
  }
}
