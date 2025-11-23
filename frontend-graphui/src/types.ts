export interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  degree?: number;
  cluster?: string;
  importance?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight?: number;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RenderConfig {
  nodeSize: number;
  infoDensity: number;
  showLabels: boolean;
  showProperties: boolean;
  showIcons: boolean;
  colorByType: boolean;
  showClusters: boolean;
  showClusterRings: boolean;
  showClusterStats: boolean;
}

export interface Transform {
  x: number;
  y: number;
  scale: number;
}
