import { ClusterInfo, StatSegment } from './cluster-types';
import { GraphNode } from './types';

export class ClusterRenderer {
  private ctx: CanvasRenderingContext2D;

  constructor(ctx: CanvasRenderingContext2D) {
    this.ctx = ctx;
  }

  /**
   * Render cluster backgrounds and boundaries
   */
  renderClusterBackgrounds(clusters: ClusterInfo[]) {
    clusters.forEach(cluster => {
      this.ctx.save();

      // Draw background circle
      this.ctx.beginPath();
      this.ctx.arc(cluster.centerX, cluster.centerY, cluster.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = cluster.backgroundColor;
      this.ctx.fill();

      // Subtle border
      this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
      this.ctx.lineWidth = 1;
      this.ctx.stroke();

      this.ctx.restore();
    });
  }

  /**
   * Render donut chart rings around clusters with aggregate statistics
   */
  renderClusterRings(clusters: ClusterInfo[], ringWidth: number = 40) {
    clusters.forEach(cluster => {
      if (!cluster.statistics || cluster.statistics.segments.length === 0) {
        return;
      }

      const innerRadius = cluster.radius;
      const outerRadius = cluster.radius + ringWidth;

      let startAngle = -Math.PI / 2; // Start at top

      cluster.statistics.segments.forEach(segment => {
        const sweepAngle = (segment.percentage / 100) * Math.PI * 2;
        const endAngle = startAngle + sweepAngle;

        // Draw segment
        this.ctx.save();
        this.ctx.beginPath();
        this.ctx.arc(cluster.centerX, cluster.centerY, outerRadius, startAngle, endAngle);
        this.ctx.arc(cluster.centerX, cluster.centerY, innerRadius, endAngle, startAngle, true);
        this.ctx.closePath();

        this.ctx.fillStyle = segment.color;
        this.ctx.fill();

        // Segment border
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.lineWidth = 1.5;
        this.ctx.stroke();

        this.ctx.restore();

        // Draw label for larger segments
        if (segment.percentage > 8) {
          const labelAngle = startAngle + sweepAngle / 2;
          const labelRadius = innerRadius + ringWidth / 2;
          const labelX = cluster.centerX + Math.cos(labelAngle) * labelRadius;
          const labelY = cluster.centerY + Math.sin(labelAngle) * labelRadius;

          this.drawSegmentLabel(labelX, labelY, segment, labelAngle);
        }

        startAngle = endAngle;
      });
    });
  }

  /**
   * Draw label on donut segment
   */
  private drawSegmentLabel(x: number, y: number, segment: StatSegment, angle: number) {
    this.ctx.save();

    this.ctx.font = 'bold 9px sans-serif';
    this.ctx.fillStyle = '#ffffff';
    this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.8)';
    this.ctx.lineWidth = 3;
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    const text = segment.label;

    // Rotate text to follow arc for side segments
    const normalizedAngle = ((angle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    const shouldRotate = normalizedAngle > Math.PI / 4 && normalizedAngle < (3 * Math.PI) / 4;

    if (shouldRotate) {
      this.ctx.save();
      this.ctx.translate(x, y);
      this.ctx.rotate(angle + Math.PI / 2);
      this.ctx.strokeText(text, 0, 0);
      this.ctx.fillText(text, 0, 0);
      this.ctx.restore();
    } else {
      this.ctx.strokeText(text, x, y);
      this.ctx.fillText(text, x, y);
    }

    this.ctx.restore();
  }

  /**
   * Render cluster labels and annotations
   */
  renderClusterLabels(clusters: ClusterInfo[]) {
    clusters.forEach(cluster => {
      this.ctx.save();

      // Draw cluster label below the cluster
      const labelY = cluster.centerY + cluster.radius + 60;

      this.ctx.font = 'bold 16px sans-serif';
      this.ctx.fillStyle = '#333333';
      this.ctx.strokeStyle = '#ffffff';
      this.ctx.lineWidth = 4;
      this.ctx.textAlign = 'center';

      this.ctx.strokeText(cluster.label, cluster.centerX, labelY);
      this.ctx.fillText(cluster.label, cluster.centerX, labelY);

      this.ctx.restore();
    });
  }

  /**
   * Render inter-cluster connection lines
   */
  renderInterClusterConnections(clusters: ClusterInfo[]) {
    // Draw lines between all cluster centers
    for (let i = 0; i < clusters.length; i++) {
      for (let j = i + 1; j < clusters.length; j++) {
        const clusterA = clusters[i];
        const clusterB = clusters[j];

        this.ctx.save();
        this.ctx.beginPath();
        this.ctx.moveTo(clusterA.centerX, clusterA.centerY);
        this.ctx.lineTo(clusterB.centerX, clusterB.centerY);
        this.ctx.strokeStyle = 'rgba(100, 100, 120, 0.15)';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();
        this.ctx.restore();
      }
    }
  }

  /**
   * Calculate cluster bounds from nodes
   */
  static calculateClusterBounds(
    nodes: GraphNode[],
    clusterId: string,
    padding: number = 50
  ): { centerX: number; centerY: number; radius: number } {
    const clusterNodes = nodes.filter(n => n.cluster === clusterId);

    if (clusterNodes.length === 0) {
      return { centerX: 0, centerY: 0, radius: 100 };
    }

    // Find bounding box
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    clusterNodes.forEach(node => {
      minX = Math.min(minX, node.x);
      maxX = Math.max(maxX, node.x);
      minY = Math.min(minY, node.y);
      maxY = Math.max(maxY, node.y);
    });

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    // Calculate radius to encompass all nodes
    let maxDistance = 0;
    clusterNodes.forEach(node => {
      const dx = node.x - centerX;
      const dy = node.y - centerY;
      const distance = Math.sqrt(dx * dx + dy * dy);
      maxDistance = Math.max(maxDistance, distance);
    });

    const radius = maxDistance + padding;

    return { centerX, centerY, radius };
  }
}
