export interface ClusterInfo {
  id: string;
  label: string;
  centerX: number;
  centerY: number;
  radius: number;
  backgroundColor: string;
  nodeIds: Set<string>;
  statistics?: ClusterStatistics;
}

export interface ClusterStatistics {
  segments: StatSegment[];
  totalCount: number;
}

export interface StatSegment {
  label: string;
  value: number;
  percentage: number;
  color: string;
}

export interface AgeDistribution {
  '<5': number;
  '5-13': number;
  '14-17': number;
  '18-24': number;
  '25-44': number;
  '45-64': number;
  '≥65': number;
}

export const AGE_COLORS = {
  '<5': '#7dd3fc',        // Light Blue
  '5-13': '#a78bfa',      // Grey-Purple
  '14-17': '#7c3aed',     // Dark Purple
  '18-24': '#5b21b6',     // Deep Violet
  '25-44': '#b45309',     // Reddish-Brown
  '45-64': '#c2410c',     // Terra-cotta
  '≥65': '#f97316'        // Bright Orange
};

export const CLUSTER_BACKGROUNDS = [
  '#e5e9f0',  // Pale grey-blue
  '#dcf4e8',  // Pale mint green
  '#fef3e2',  // Pale cream/yellow
  '#f4e4f7',  // Pale lavender
  '#fde8e8',  // Pale pink
  '#e0f2fe'   // Pale sky blue
];
