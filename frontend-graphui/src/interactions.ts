import { GraphNode, RenderConfig, Transform } from './types';
import { GraphRenderer } from './renderer';

export class InteractionController {
  private canvas: HTMLCanvasElement;
  private renderer: GraphRenderer;
  private nodes: GraphNode[];
  private config: RenderConfig;

  private isDragging = false;
  private lastMouseX = 0;
  private lastMouseY = 0;
  private hoveredNode: GraphNode | null = null;

  private tooltip: HTMLElement;

  // Callbacks
  private onNodeDoubleClick?: (node: GraphNode) => void;

  constructor(
    canvas: HTMLCanvasElement,
    renderer: GraphRenderer,
    nodes: GraphNode[],
    config: RenderConfig,
    callbacks?: {
      onNodeDoubleClick?: (node: GraphNode) => void;
    }
  ) {
    this.canvas = canvas;
    this.renderer = renderer;
    this.nodes = nodes;
    this.config = config;

    this.tooltip = document.getElementById('tooltip')!;

    if (callbacks) {
      this.onNodeDoubleClick = callbacks.onNodeDoubleClick;
    }

    this.setupEventListeners();
  }

  updateNodes(nodes: GraphNode[]) {
    this.nodes = nodes;
  }

  updateConfig(config: RenderConfig) {
    this.config = config;
  }

  private setupEventListeners() {
    // Mouse wheel for zoom
    this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));

    // Mouse drag for pan
    this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseup', () => this.handleMouseUp());
    this.canvas.addEventListener('mouseleave', () => this.handleMouseLeave());

    // Double-click for drill-down
    this.canvas.addEventListener('dblclick', (e) => this.handleDoubleClick(e));

    // Touch support for mobile
    this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
    this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
    this.canvas.addEventListener('touchend', () => this.handleTouchEnd());
  }

  private handleDoubleClick(e: MouseEvent) {
    const node = this.renderer.findNodeAt(e.clientX, e.clientY, this.nodes, this.config);

    if (node && this.onNodeDoubleClick) {
      this.onNodeDoubleClick(node);
    }
  }

  private handleWheel(e: WheelEvent) {
    e.preventDefault();

    const transform = this.renderer.getTransform();
    const mouseX = e.clientX;
    const mouseY = e.clientY;

    // Zoom towards mouse position
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    const newScale = Math.max(0.1, Math.min(5, transform.scale * zoomFactor));

    // Adjust position to zoom towards mouse
    const worldBefore = this.renderer.screenToWorld(mouseX, mouseY);
    transform.scale = newScale;
    const worldAfter = this.renderer.screenToWorld(mouseX, mouseY);

    transform.x += (worldAfter.x - worldBefore.x) * transform.scale;
    transform.y += (worldAfter.y - worldBefore.y) * transform.scale;

    this.renderer.setTransform(transform);
  }

  private handleMouseDown(e: MouseEvent) {
    this.isDragging = true;
    this.lastMouseX = e.clientX;
    this.lastMouseY = e.clientY;
    this.canvas.style.cursor = 'grabbing';
  }

  private handleMouseMove(e: MouseEvent) {
    if (this.isDragging) {
      const dx = e.clientX - this.lastMouseX;
      const dy = e.clientY - this.lastMouseY;

      const transform = this.renderer.getTransform();
      transform.x += dx;
      transform.y += dy;
      this.renderer.setTransform(transform);

      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    } else {
      // Check for node hover
      const node = this.renderer.findNodeAt(e.clientX, e.clientY, this.nodes, this.config);

      if (node !== this.hoveredNode) {
        this.hoveredNode = node;
        this.updateTooltip(node, e.clientX, e.clientY);
      }

      this.canvas.style.cursor = node ? 'pointer' : 'grab';
    }
  }

  private handleMouseUp() {
    this.isDragging = false;
    this.canvas.style.cursor = 'grab';
  }

  private handleMouseLeave() {
    this.isDragging = false;
    this.hoveredNode = null;
    this.hideTooltip();
    this.canvas.style.cursor = 'grab';
  }

  private handleTouchStart(e: TouchEvent) {
    e.preventDefault();
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      this.isDragging = true;
      this.lastMouseX = touch.clientX;
      this.lastMouseY = touch.clientY;
    }
  }

  private handleTouchMove(e: TouchEvent) {
    e.preventDefault();
    if (this.isDragging && e.touches.length === 1) {
      const touch = e.touches[0];
      const dx = touch.clientX - this.lastMouseX;
      const dy = touch.clientY - this.lastMouseY;

      const transform = this.renderer.getTransform();
      transform.x += dx;
      transform.y += dy;
      this.renderer.setTransform(transform);

      this.lastMouseX = touch.clientX;
      this.lastMouseY = touch.clientY;
    }
  }

  private handleTouchEnd() {
    this.isDragging = false;
  }

  private updateTooltip(node: GraphNode | null, x: number, y: number) {
    if (!node) {
      this.hideTooltip();
      return;
    }

    // Build tooltip HTML
    let html = `<div class="node-label">${node.label}</div>`;
    html += `<div class="node-type">${node.type}</div>`;

    const props = Object.entries(node.properties);
    if (props.length > 0) {
      props.forEach(([key, value]) => {
        html += `<div class="property"><span class="property-key">${key}:</span>${value}</div>`;
      });
    }

    if (node.degree !== undefined) {
      html += `<div class="property"><span class="property-key">connections:</span>${node.degree}</div>`;
    }

    this.tooltip.innerHTML = html;
    this.tooltip.style.display = 'block';

    // Position tooltip near cursor
    const tooltipX = Math.min(x + 15, window.innerWidth - this.tooltip.offsetWidth - 10);
    const tooltipY = Math.min(y + 15, window.innerHeight - this.tooltip.offsetHeight - 10);

    this.tooltip.style.left = `${tooltipX}px`;
    this.tooltip.style.top = `${tooltipY}px`;
  }

  private hideTooltip() {
    this.tooltip.style.display = 'none';
  }

  resetView() {
    const transform: Transform = {
      x: 0,
      y: 0,
      scale: 1
    };
    this.renderer.setTransform(transform);
  }
}
