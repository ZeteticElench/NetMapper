import { GraphRenderer } from './renderer';
import { GraphLayout } from './layout';
import { InteractionController } from './interactions';
import { generateSampleGraph, generateLargeGraph } from './data';
import { generateClusteredGraph } from './cluster-data';
import { generateDataCenterGraph } from './datacenter-data';
import { GraphData, RenderConfig, GraphNode } from './types';
import { ClusterInfo } from './cluster-types';
import { Neo4jConnector } from './neo4j-connector';
import { HierarchyController } from './hierarchy-controller';

class GraphUI {
  private canvas: HTMLCanvasElement;
  private renderer: GraphRenderer;
  private layout: GraphLayout;
  private interactions: InteractionController;
  private graphData: GraphData;
  private clusters: ClusterInfo[] = [];
  private config: RenderConfig;
  private neo4j: Neo4jConnector;

  // Hierarchy mode
  private hierarchyMode: boolean = false;
  private hierarchyController: HierarchyController | null = null;

  private fps = 0;
  private frameCount = 0;
  private fpsUpdateTime = 0;

  constructor() {
    this.canvas = document.getElementById('graph-canvas') as HTMLCanvasElement;
    this.renderer = new GraphRenderer(this.canvas);
    this.layout = new GraphLayout(window.innerWidth, window.innerHeight);
    this.neo4j = new Neo4jConnector();

    this.config = {
      nodeSize: 20,
      infoDensity: 2,
      showLabels: true,
      showProperties: true,
      showIcons: true,
      colorByType: true,
      showClusters: true,
      showClusterRings: true,
      showClusterStats: true
    };

    // Initialize with clustered graph
    const clusteredData = generateClusteredGraph();
    this.graphData = clusteredData.graphData;
    this.clusters = clusteredData.clusters;

    this.interactions = new InteractionController(
      this.canvas,
      this.renderer,
      this.graphData.nodes,
      this.config,
      {
        onNodeDoubleClick: (node) => this.handleNodeDoubleClick(node)
      }
    );

    this.setupControls();
    this.setupNeo4jControls();
    this.setupHierarchyControls();
    this.setupWindowResize();
    this.updateInfoPanel();
    this.updateBreadcrumb();

    // Start render loop
    this.animate();
  }

  private handleNodeDoubleClick(node: GraphNode) {
    if (!this.hierarchyMode || !this.hierarchyController) return;

    console.log('Double-clicked node:', node.label);
    const success = this.hierarchyController.drillDown(node.id);

    if (success) {
      this.refreshHierarchyView();
    }
  }

  private refreshHierarchyView() {
    if (!this.hierarchyController) return;

    const view = this.hierarchyController.getCurrentView();
    this.graphData = view;

    // Apply layout to new level
    this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 100);

    this.interactions.updateNodes(this.graphData.nodes);
    this.updateInfoPanel();
    this.updateBreadcrumb();
    this.interactions.resetView();
  }

  private updateBreadcrumb() {
    const breadcrumbDiv = document.getElementById('breadcrumb');
    const breadcrumbPath = document.getElementById('breadcrumb-path');

    if (!this.hierarchyMode || !this.hierarchyController) {
      breadcrumbDiv?.classList.remove('visible');
      return;
    }

    breadcrumbDiv?.classList.add('visible');

    if (breadcrumbPath) {
      breadcrumbPath.textContent = this.hierarchyController.getBreadcrumbPath();
    }
  }

  private setupHierarchyControls() {
    const upBtn = document.getElementById('breadcrumb-up');
    const homeBtn = document.getElementById('breadcrumb-home');

    upBtn?.addEventListener('click', () => {
      if (!this.hierarchyController) return;

      const success = this.hierarchyController.drillUp();
      if (success) {
        this.refreshHierarchyView();
      }
    });

    homeBtn?.addEventListener('click', () => {
      if (!this.hierarchyController) return;

      this.hierarchyController.reset();
      this.refreshHierarchyView();
    });
  }

  private setupControls() {
    // Node size control
    const nodeSizeInput = document.getElementById('node-size') as HTMLInputElement;
    nodeSizeInput.addEventListener('input', (e) => {
      this.config.nodeSize = parseInt((e.target as HTMLInputElement).value);
    });

    // Info density control
    const densityInput = document.getElementById('info-density') as HTMLInputElement;
    densityInput.addEventListener('input', (e) => {
      this.config.infoDensity = parseInt((e.target as HTMLInputElement).value);
      this.interactions.updateConfig(this.config);
    });

    // Randomize layout button
    const randomizeBtn = document.getElementById('randomize');
    randomizeBtn?.addEventListener('click', () => {
      this.layout.randomize(this.graphData.nodes);
      this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 150);
    });

    // Reset view button
    const resetViewBtn = document.getElementById('reset-view');
    resetViewBtn?.addEventListener('click', () => {
      this.interactions.resetView();
    });

    // Keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.key === 'r') {
        this.interactions.resetView();
      } else if (e.key === 'l') {
        this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 100);
      } else if (e.key === 'c') {
        this.layout.applyClusterLayout(this.graphData.nodes, this.graphData.edges);
      } else if (e.key === 'h') {
        this.layout.applyHierarchicalLayout(this.graphData.nodes, this.graphData.edges);
      } else if (e.key === '1') {
        this.graphData = generateSampleGraph();
        this.clusters = [];
        this.layout.applyClusterLayout(this.graphData.nodes, this.graphData.edges);
        this.interactions.updateNodes(this.graphData.nodes);
        this.updateInfoPanel();
      } else if (e.key === '2') {
        this.graphData = generateLargeGraph(50);
        this.clusters = [];
        this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 150);
        this.interactions.updateNodes(this.graphData.nodes);
        this.updateInfoPanel();
      } else if (e.key === '3') {
        this.graphData = generateLargeGraph(100);
        this.clusters = [];
        this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 150);
        this.interactions.updateNodes(this.graphData.nodes);
        this.updateInfoPanel();
      } else if (e.key === '4') {
        this.hierarchyMode = false;
        this.hierarchyController = null;
        const clusteredData = generateClusteredGraph();
        this.graphData = clusteredData.graphData;
        this.clusters = clusteredData.clusters;
        this.interactions.updateNodes(this.graphData.nodes);
        this.updateInfoPanel();
        this.updateBreadcrumb();
      } else if (e.key === '5') {
        // Load data center hierarchy
        this.hierarchyMode = true;
        const dcData = generateDataCenterGraph();
        this.clusters = dcData.clusters;
        this.hierarchyController = new HierarchyController(dcData.hierarchyMap, dcData.graphData);

        // Show top level
        this.refreshHierarchyView();
        console.log('📊 Data Center Hierarchy Mode');
        console.log('Double-click nodes to drill down, use breadcrumb to navigate up');
      } else if (e.key === 't') {
        this.config.showClusters = !this.config.showClusters;
      } else if (e.key === 'g') {
        this.config.showClusterRings = !this.config.showClusterRings;
      } else if (e.key === 'ArrowUp' && this.hierarchyMode && this.hierarchyController) {
        const success = this.hierarchyController.drillUp();
        if (success) this.refreshHierarchyView();
      }
    });
  }

  private setupNeo4jControls() {
    const connectBtn = document.getElementById('connect-btn');
    const disconnectBtn = document.getElementById('disconnect-btn');
    const loadAllBtn = document.getElementById('load-all-btn');
    const statusDiv = document.getElementById('connection-status');
    const loadControls = document.getElementById('load-controls');

    connectBtn?.addEventListener('click', async () => {
      const uri = (document.getElementById('neo4j-uri') as HTMLInputElement).value;
      const username = (document.getElementById('neo4j-username') as HTMLInputElement).value;
      const password = (document.getElementById('neo4j-password') as HTMLInputElement).value;

      try {
        await this.neo4j.connect({ uri, username, password });

        statusDiv!.className = 'status success';
        statusDiv!.textContent = '✓ Connected to Neo4j';

        connectBtn!.classList.add('hidden');
        disconnectBtn!.classList.remove('hidden');
        loadControls!.classList.remove('hidden');

        // Get stats
        const stats = await this.neo4j.getStats();
        console.log('Neo4j stats:', stats);
      } catch (error) {
        statusDiv!.className = 'status error';
        statusDiv!.textContent = `✗ Connection failed: ${(error as Error).message}`;
      }
    });

    disconnectBtn?.addEventListener('click', async () => {
      await this.neo4j.disconnect();

      statusDiv!.className = 'status';
      statusDiv!.textContent = '';

      connectBtn!.classList.remove('hidden');
      disconnectBtn!.classList.add('hidden');
      loadControls!.classList.add('hidden');
    });

    loadAllBtn?.addEventListener('click', async () => {
      const limit = parseInt((document.getElementById('load-limit') as HTMLInputElement).value);

      try {
        statusDiv!.className = 'status';
        statusDiv!.textContent = 'Loading graph...';

        const result = await this.neo4j.loadGraph(limit);
        this.graphData = result.graphData;
        this.clusters = result.clusters;

        // Apply layout
        this.layout.applyForceLayout(this.graphData.nodes, this.graphData.edges, 150);

        this.interactions.updateNodes(this.graphData.nodes);
        this.updateInfoPanel();
        this.interactions.resetView();

        statusDiv!.className = 'status success';
        statusDiv!.textContent = `✓ Loaded ${this.graphData.nodes.length} nodes, ${this.graphData.edges.length} edges`;
      } catch (error) {
        statusDiv!.className = 'status error';
        statusDiv!.textContent = `✗ Load failed: ${(error as Error).message}`;
      }
    });
  }

  private setupWindowResize() {
    window.addEventListener('resize', () => {
      this.renderer.resize();
      this.layout.setSize(window.innerWidth, window.innerHeight);
    });
  }

  private updateInfoPanel() {
    document.getElementById('node-count')!.textContent = this.graphData.nodes.length.toString();
    document.getElementById('edge-count')!.textContent = this.graphData.edges.length.toString();
  }

  private animate = (timestamp: number = 0) => {
    // Calculate FPS
    if (timestamp - this.fpsUpdateTime > 1000) {
      this.fps = this.frameCount;
      this.frameCount = 0;
      this.fpsUpdateTime = timestamp;
      document.getElementById('fps')!.textContent = this.fps.toString();
    }
    this.frameCount++;

    // Render
    this.renderer.render(this.graphData.nodes, this.graphData.edges, this.config, this.clusters);

    requestAnimationFrame(this.animate);
  };
}

// Initialize the application
new GraphUI();

console.log(`
╔═══════════════════════════════════════════════════════════════╗
║      Dense Graph UI - Information Visualization              ║
║      🖥️  "Google Earth for Data Centers"                      ║
╚═══════════════════════════════════════════════════════════════╝

Keyboard Shortcuts:
  R - Reset view
  L - Force-directed layout
  C - Cluster layout
  H - Hierarchical layout
  1 - Load sample graph (small)
  2 - Load medium graph (50 nodes)
  3 - Load large graph (100 nodes)
  4 - Load clustered graph with demographics
  5 - Load Data Center Hierarchy (IT Infrastructure)
  T - Toggle cluster backgrounds
  G - Toggle cluster rings/donut charts
  ↑ - Navigate up in hierarchy (when in hierarchy mode)

Mouse Controls:
  Scroll - Zoom in/out
  Drag - Pan view
  Hover - Show node details
  Double-Click - Drill down (Data Center → Rack → Server → Process)

Hierarchy Mode (Key 5):
  Level 1: Data Centers (rings show PUE, power, bandwidth, temp)
  Level 2: Racks (rings show power phases, capacity)
  Level 3: Servers (heat-mapped by status, colored by OS)
  Level 4: Processes (show resource usage)
`);
