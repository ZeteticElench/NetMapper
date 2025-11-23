export type HierarchyLevel = 'datacenter' | 'rack' | 'server' | 'process';

export interface HierarchicalNode {
  id: string;
  label: string;
  type: string;
  level: HierarchyLevel;
  parentId?: string;
  children?: string[];
  properties: Record<string, any>;
  x: number;
  y: number;
  importance?: number;
  status?: 'healthy' | 'warning' | 'critical' | 'offline';
  // IT-specific metrics
  metrics?: NodeMetrics;
}

export interface NodeMetrics {
  // Data Center level
  pue?: number;  // Power Usage Effectiveness
  totalPower?: number; // kW
  bandwidth?: number; // Gbps
  temperature?: number; // Celsius

  // Rack level
  powerPhaseA?: number; // kW on Feed A
  powerPhaseB?: number; // kW on Feed B
  usedRackUnits?: number;
  totalRackUnits?: number;
  switchPorts?: { used: number; total: number };

  // Server level
  cpuCores?: number;
  ramGB?: number;
  cpuUsage?: number; // percentage
  ramUsage?: number; // percentage
  diskIOPS?: number;
  networkThroughput?: number; // Mbps

  // Process level
  memoryMB?: number;
  cpuPercent?: number;
  threads?: number;
  connections?: number;
}

export interface HierarchyState {
  currentLevel: HierarchyLevel;
  currentParentId: string | null; // null = top level
  breadcrumb: Array<{ id: string; label: string; level: HierarchyLevel }>;
}

export const LEVEL_ORDER: HierarchyLevel[] = ['datacenter', 'rack', 'server', 'process'];

export const LEVEL_LABELS = {
  datacenter: 'Data Centers',
  rack: 'Racks',
  server: 'Servers',
  process: 'Processes'
};

// Status colors for heat mapping
export const STATUS_COLORS = {
  healthy: '#10b981',   // Green
  warning: '#f59e0b',   // Orange
  critical: '#ef4444',  // Red
  offline: '#6b7280'    // Gray
};

// OS colors
export const OS_COLORS = {
  'Linux': '#3b82f6',      // Blue
  'Windows': '#f97316',    // Orange
  'ESXi': '#8b5cf6',       // Purple
  'FreeBSD': '#ec4899',    // Pink
  'Container': '#06b6d4'   // Cyan
};
