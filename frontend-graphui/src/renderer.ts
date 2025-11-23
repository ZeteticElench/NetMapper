import { GraphNode, GraphEdge, RenderConfig, Transform } from './types';
import { ClusterRenderer } from './cluster-renderer';
import { ClusterInfo } from './cluster-types';
import { STATUS_COLORS, OS_COLORS } from './hierarchy-types';

export class GraphRenderer {
  private ctx: CanvasRenderingContext2D;
  private canvas: HTMLCanvasElement;
  private transform: Transform = { x: 0, y: 0, scale: 1 };
  private clusterRenderer: ClusterRenderer;

  // Color schemes for different node types
  private typeColors: Map<string, string> = new Map([
    ['Person', '#3b82f6'],
    ['Organization', '#8b5cf6'],
    ['Location', '#10b981'],
    ['Event', '#f59e0b'],
    ['Document', '#ef4444'],
    ['Concept', '#06b6d4'],
    ['Product', '#ec4899'],
    // IT Infrastructure types
    ['DataCenter', '#8b5cf6'],
    ['Rack', '#3b82f6'],
    ['Process', '#10b981'],
    ['default', '#6b7280']
  ]);

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d')!;
    this.clusterRenderer = new ClusterRenderer(this.ctx);
    this.resize();
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  setTransform(transform: Transform) {
    this.transform = transform;
  }

  getTransform(): Transform {
    return { ...this.transform };
  }

  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  render(nodes: GraphNode[], edges: GraphEdge[], config: RenderConfig, clusters?: ClusterInfo[]) {
    this.clear();

    this.ctx.save();
    this.ctx.translate(this.transform.x, this.transform.y);
    this.ctx.scale(this.transform.scale, this.transform.scale);

    // Layer 1: Cluster backgrounds (bottom layer)
    if (config.showClusters && clusters && clusters.length > 0) {
      this.clusterRenderer.renderClusterBackgrounds(clusters);
    }

    // Layer 2: Inter-cluster connections
    if (config.showClusters && clusters && clusters.length > 1) {
      this.clusterRenderer.renderInterClusterConnections(clusters);
    }

    // Layer 3: Edges (background layer)
    this.renderEdges(edges, nodes, config);

    // Layer 4: Nodes (foreground layer)
    this.renderNodes(nodes, config);

    // Layer 5: Cluster rings with statistics (on top of nodes)
    if (config.showClusterRings && clusters && clusters.length > 0) {
      this.clusterRenderer.renderClusterRings(clusters, 40);
    }

    // Layer 6: Cluster labels (top layer)
    if (config.showClusters && clusters && clusters.length > 0) {
      this.clusterRenderer.renderClusterLabels(clusters);
    }

    this.ctx.restore();
  }

  private renderEdges(edges: GraphEdge[], nodes: GraphNode[], config: RenderConfig) {
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    edges.forEach(edge => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);

      if (!source || !target) return;

      const weight = edge.weight || 1;
      const alpha = Math.min(0.6, 0.2 + (weight * 0.4));

      this.ctx.beginPath();
      this.ctx.strokeStyle = `rgba(100, 100, 120, ${alpha})`;
      this.ctx.lineWidth = Math.max(0.5, weight);
      this.ctx.moveTo(source.x, source.y);
      this.ctx.lineTo(target.x, target.y);
      this.ctx.stroke();

      // Draw edge labels for high-importance edges
      if (config.infoDensity >= 2 && weight > 1.5) {
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;

        this.ctx.save();
        this.ctx.fillStyle = 'rgba(150, 150, 170, 0.8)';
        this.ctx.font = '8px monospace';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(edge.type, midX, midY - 3);
        this.ctx.restore();
      }
    });
  }

  private renderNodes(nodes: GraphNode[], config: RenderConfig) {
    nodes.forEach(node => {
      this.renderNode(node, config);
    });
  }

  private renderNode(node: GraphNode, config: RenderConfig) {
    const size = config.nodeSize * (1 + (node.importance || 0) * 0.5);

    // Use heat-map colors if status is present, otherwise use type colors
    let color: string;
    if (node.properties.status && STATUS_COLORS[node.properties.status as keyof typeof STATUS_COLORS]) {
      color = STATUS_COLORS[node.properties.status as keyof typeof STATUS_COLORS];
    } else if (node.properties.os && OS_COLORS[node.properties.os as keyof typeof OS_COLORS]) {
      color = OS_COLORS[node.properties.os as keyof typeof OS_COLORS];
    } else {
      color = this.typeColors.get(node.type) || this.typeColors.get('default')!;
    }

    // Draw node shadow for depth
    this.ctx.save();
    this.ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
    this.ctx.shadowBlur = 8;
    this.ctx.shadowOffsetX = 2;
    this.ctx.shadowOffsetY = 2;

    // Draw main node circle
    this.ctx.beginPath();
    this.ctx.arc(node.x, node.y, size, 0, Math.PI * 2);
    this.ctx.fillStyle = color;
    this.ctx.fill();

    // Node border
    this.ctx.strokeStyle = this.lightenColor(color, 30);
    this.ctx.lineWidth = 2;
    this.ctx.stroke();

    this.ctx.restore();

    // Draw degree indicator (inner ring)
    if (node.degree && node.degree > 0) {
      const ringSize = size * 0.6;
      const ringWidth = Math.min(size * 0.2, node.degree * 0.5);

      this.ctx.beginPath();
      this.ctx.arc(node.x, node.y, ringSize, 0, Math.PI * 2);
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      this.ctx.lineWidth = ringWidth;
      this.ctx.stroke();
    }

    // Draw type badge
    this.ctx.save();
    this.ctx.font = 'bold 9px monospace';
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(node.type.substring(0, 3).toUpperCase(), node.x, node.y + 3);
    this.ctx.restore();

    // Draw node label
    if (config.showLabels) {
      this.ctx.save();
      this.ctx.font = 'bold 11px sans-serif';
      this.ctx.fillStyle = '#ffffff';
      this.ctx.strokeStyle = '#000000';
      this.ctx.lineWidth = 3;
      this.ctx.textAlign = 'center';

      const labelY = node.y + size + 14;
      this.ctx.strokeText(node.label, node.x, labelY);
      this.ctx.fillText(node.label, node.x, labelY);
      this.ctx.restore();
    }

    // High density: Show property count badges
    if (config.infoDensity >= 2) {
      const propCount = Object.keys(node.properties).length;
      if (propCount > 0) {
        this.drawBadge(node.x + size - 6, node.y - size + 6, propCount.toString(), '#ec4899');
      }
    }

    // Ultra high density: Show key properties inline
    if (config.infoDensity >= 3 && config.showProperties) {
      this.renderInlineProperties(node, size);
    }

    // Draw importance indicator
    if (node.importance && node.importance > 0.5) {
      this.drawStar(node.x - size + 6, node.y - size + 6, 4, '#fbbf24');
    }
  }

  private renderInlineProperties(node: GraphNode, size: number) {
    const props = Object.entries(node.properties).slice(0, 3);
    let offsetY = size + 28;

    this.ctx.save();
    this.ctx.font = '9px monospace';
    this.ctx.textAlign = 'center';

    props.forEach(([key, value]) => {
      const text = `${key}: ${String(value).substring(0, 15)}`;

      // Background
      this.ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      const metrics = this.ctx.measureText(text);
      this.ctx.fillRect(
        node.x - metrics.width / 2 - 3,
        node.y + offsetY - 9,
        metrics.width + 6,
        11
      );

      // Text
      this.ctx.fillStyle = '#a0a0a0';
      this.ctx.fillText(text, node.x, node.y + offsetY);
      offsetY += 12;
    });

    this.ctx.restore();
  }

  private drawBadge(x: number, y: number, text: string, color: string) {
    const size = 10;

    this.ctx.save();

    // Badge circle
    this.ctx.beginPath();
    this.ctx.arc(x, y, size, 0, Math.PI * 2);
    this.ctx.fillStyle = color;
    this.ctx.fill();
    this.ctx.strokeStyle = '#000';
    this.ctx.lineWidth = 1.5;
    this.ctx.stroke();

    // Badge text
    this.ctx.fillStyle = '#fff';
    this.ctx.font = 'bold 8px sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(text, x, y + 3);

    this.ctx.restore();
  }

  private drawStar(x: number, y: number, size: number, color: string) {
    this.ctx.save();
    this.ctx.fillStyle = color;
    this.ctx.beginPath();

    for (let i = 0; i < 5; i++) {
      const angle = (i * 4 * Math.PI) / 5 - Math.PI / 2;
      const r = i % 2 === 0 ? size : size / 2;
      const px = x + Math.cos(angle) * r;
      const py = y + Math.sin(angle) * r;

      if (i === 0) {
        this.ctx.moveTo(px, py);
      } else {
        this.ctx.lineTo(px, py);
      }
    }

    this.ctx.closePath();
    this.ctx.fill();
    this.ctx.restore();
  }

  private lightenColor(color: string, percent: number): string {
    const num = parseInt(color.replace('#', ''), 16);
    const r = Math.min(255, ((num >> 16) & 0xff) + percent);
    const g = Math.min(255, ((num >> 8) & 0xff) + percent);
    const b = Math.min(255, (num & 0xff) + percent);
    return `rgb(${r}, ${g}, ${b})`;
  }

  screenToWorld(screenX: number, screenY: number): { x: number; y: number } {
    return {
      x: (screenX - this.transform.x) / this.transform.scale,
      y: (screenY - this.transform.y) / this.transform.scale
    };
  }

  findNodeAt(x: number, y: number, nodes: GraphNode[], config: RenderConfig): GraphNode | null {
    const worldPos = this.screenToWorld(x, y);

    for (let i = nodes.length - 1; i >= 0; i--) {
      const node = nodes[i];
      const size = config.nodeSize * (1 + (node.importance || 0) * 0.5);
      const dx = worldPos.x - node.x;
      const dy = worldPos.y - node.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      if (distance <= size) {
        return node;
      }
    }

    return null;
  }
}
