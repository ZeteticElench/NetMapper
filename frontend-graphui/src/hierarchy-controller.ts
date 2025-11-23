import { HierarchyState, HierarchicalNode, LEVEL_ORDER } from './hierarchy-types';
import { GraphData } from './types';
import { filterByLevel } from './datacenter-data';

export class HierarchyController {
  private hierarchyMap: Map<string, HierarchicalNode>;
  private fullGraphData: GraphData;
  private state: HierarchyState;

  constructor(hierarchyMap: Map<string, HierarchicalNode>, fullGraphData: GraphData) {
    this.hierarchyMap = hierarchyMap;
    this.fullGraphData = fullGraphData;
    this.state = {
      currentLevel: 'datacenter',
      currentParentId: null,
      breadcrumb: []
    };
  }

  /**
   * Get current filtered graph data based on hierarchy state
   */
  getCurrentView(): { nodes: any[]; edges: any[] } {
    return filterByLevel(this.hierarchyMap, this.fullGraphData, this.state.currentParentId);
  }

  /**
   * Drill down into a node (zoom in)
   */
  drillDown(nodeId: string): boolean {
    const node = this.hierarchyMap.get(nodeId);
    if (!node) return false;

    // Can't drill down into leaf nodes (processes)
    if (node.level === 'process') return false;

    // Can't drill down if node has no children
    if (!node.children || node.children.length === 0) return false;

    // Update state
    this.state.currentParentId = nodeId;

    const currentLevelIndex = LEVEL_ORDER.indexOf(node.level);
    if (currentLevelIndex >= 0 && currentLevelIndex < LEVEL_ORDER.length - 1) {
      this.state.currentLevel = LEVEL_ORDER[currentLevelIndex + 1];
    }

    // Update breadcrumb
    this.state.breadcrumb.push({
      id: node.id,
      label: node.label,
      level: node.level
    });

    return true;
  }

  /**
   * Go back one level (zoom out)
   */
  drillUp(): boolean {
    if (this.state.breadcrumb.length === 0) {
      return false; // Already at top level
    }

    // Remove last breadcrumb
    this.state.breadcrumb.pop();

    // Set current parent to previous breadcrumb or null
    if (this.state.breadcrumb.length > 0) {
      const previousCrumb = this.state.breadcrumb[this.state.breadcrumb.length - 1];
      this.state.currentParentId = previousCrumb.id;
      this.state.currentLevel = LEVEL_ORDER[LEVEL_ORDER.indexOf(previousCrumb.level) + 1];
    } else {
      this.state.currentParentId = null;
      this.state.currentLevel = 'datacenter';
    }

    return true;
  }

  /**
   * Jump to specific level in breadcrumb
   */
  jumpTo(breadcrumbIndex: number): boolean {
    if (breadcrumbIndex < 0 || breadcrumbIndex >= this.state.breadcrumb.length) {
      // Jump to root
      if (breadcrumbIndex === -1) {
        this.state.currentParentId = null;
        this.state.currentLevel = 'datacenter';
        this.state.breadcrumb = [];
        return true;
      }
      return false;
    }

    // Trim breadcrumb
    this.state.breadcrumb = this.state.breadcrumb.slice(0, breadcrumbIndex + 1);

    const crumb = this.state.breadcrumb[breadcrumbIndex];
    this.state.currentParentId = crumb.id;
    this.state.currentLevel = LEVEL_ORDER[LEVEL_ORDER.indexOf(crumb.level) + 1];

    return true;
  }

  /**
   * Reset to top level
   */
  reset(): void {
    this.state = {
      currentLevel: 'datacenter',
      currentParentId: null,
      breadcrumb: []
    };
  }

  /**
   * Get current state
   */
  getState(): HierarchyState {
    return { ...this.state };
  }

  /**
   * Get node by ID
   */
  getNode(nodeId: string): HierarchicalNode | undefined {
    return this.hierarchyMap.get(nodeId);
  }

  /**
   * Get current level name
   */
  getCurrentLevelName(): string {
    return this.state.currentLevel;
  }

  /**
   * Get breadcrumb path as string
   */
  getBreadcrumbPath(): string {
    if (this.state.breadcrumb.length === 0) {
      return 'All Data Centers';
    }

    return 'All > ' + this.state.breadcrumb.map(c => c.label).join(' > ');
  }
}
