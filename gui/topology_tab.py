"""Network topology visualization tab."""

import logging
import math
from typing import Dict, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsTextItem,
    QLabel,
    QComboBox,
    QSlider,
)
from PySide6.QtGui import QPen, QBrush, QColor, QPainter
from PySide6.QtCore import Qt, QPointF, QRectF

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class NetworkNode(QGraphicsEllipseItem):
    """Graphical representation of a network device."""

    def __init__(self, node_id: str, x: float, y: float, radius: float = 30):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.node_id = node_id
        self.setPos(x, y)

        # Make node movable
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges)

        # Style
        self.setPen(QPen(QColor("#0d7377"), 2))
        self.setBrush(QBrush(QColor("#14b1b8")))

        # Label
        self.label = QGraphicsTextItem(node_id, self)
        self.label.setDefaultTextColor(QColor("#fff"))
        self.label.setPos(-radius, radius + 5)

        # Store connected edges
        self.edges = []

    def add_edge(self, edge):
        """Add an edge connected to this node."""
        self.edges.append(edge)

    def itemChange(self, change, value):
        """Update connected edges when node moves."""
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)


class NetworkEdge(QGraphicsLineItem):
    """Graphical representation of a network link."""

    def __init__(self, source: NetworkNode, target: NetworkNode, edge_type: str = ""):
        super().__init__()
        self.source = source
        self.target = target
        self.edge_type = edge_type

        # Style based on edge type
        if "CDP" in edge_type or "LLDP" in edge_type:
            pen = QPen(QColor("#32CD32"), 2)  # Green for neighbor relationships
        elif "CIM" in edge_type:
            pen = QPen(QColor("#FFA500"), 2)  # Orange for CIM relationships
        else:
            pen = QPen(QColor("#888"), 2)  # Gray for other

        self.setPen(pen)
        self.update_position()

        # Add to nodes' edge lists
        source.add_edge(self)
        target.add_edge(self)

    def update_position(self):
        """Update line position based on node positions."""
        source_pos = self.source.scenePos()
        target_pos = self.target.scenePos()
        self.setLine(
            source_pos.x(),
            source_pos.y(),
            target_pos.x(),
            target_pos.y(),
        )


class TopologyView(QGraphicsView):
    """Custom graphics view for network topology."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        # Zoom factor
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Get mouse position
        old_pos = self.mapToScene(event.position().toPoint())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

        # Get new position
        new_pos = self.mapToScene(event.position().toPoint())

        # Move scene to keep mouse position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


class TopologyTab(QWidget):
    """Tab for visualizing network topology."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_username = "neo4j"
        self.neo4j_password = "password"
        self.driver = None
        self.nodes: Dict[str, NetworkNode] = {}
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Control panel
        control_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh Topology")
        refresh_button.clicked.connect(self.load_topology)
        control_layout.addWidget(refresh_button)

        # Layout algorithm selector
        control_layout.addWidget(QLabel("Layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["Circular", "Force-Directed", "Hierarchical"])
        self.layout_combo.currentTextChanged.connect(self.apply_layout)
        control_layout.addWidget(self.layout_combo)

        # Zoom controls
        control_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.valueChanged.connect(self.set_zoom)
        control_layout.addWidget(self.zoom_slider)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Graphics view
        self.scene = QGraphicsScene()
        self.view = TopologyView()
        self.view.setScene(self.scene)
        layout.addWidget(self.view)

        # Status label
        self.status_label = QLabel("No topology loaded. Click 'Refresh Topology' to load.")
        layout.addWidget(self.status_label)

    def load_topology(self):
        """Load network topology from Neo4j."""
        try:
            # Connect to Neo4j
            if not self.driver:
                self.driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_username, self.neo4j_password),
                )

            # Clear existing scene
            self.scene.clear()
            self.nodes.clear()

            # Query all devices and relationships
            with self.driver.session() as session:
                # Get all devices
                devices_query = "MATCH (d:NetworkDevice) RETURN d.hostname as hostname"
                result = session.run(devices_query)
                device_list = [record["hostname"] for record in result]

                # Get all relationships
                rel_query = """
                MATCH (a)-[r]->(b)
                WHERE (a:NetworkDevice OR a:Port OR a:Interface)
                  AND (b:NetworkDevice OR b:Port OR b:Interface)
                RETURN DISTINCT
                    COALESCE(a.hostname, a.device_hostname) as source,
                    COALESCE(b.hostname, b.device_hostname) as target,
                    type(r) as rel_type
                """
                result = session.run(rel_query)
                relationships = [
                    {
                        "source": record["source"],
                        "target": record["target"],
                        "type": record["rel_type"],
                    }
                    for record in result
                ]

            # Create nodes
            for i, hostname in enumerate(device_list):
                angle = (2 * math.pi * i) / len(device_list)
                x = 300 * math.cos(angle)
                y = 300 * math.sin(angle)
                node = NetworkNode(hostname, x, y)
                self.nodes[hostname] = node
                self.scene.addItem(node)

            # Create edges
            edge_count = 0
            for rel in relationships:
                source = rel["source"]
                target = rel["target"]
                if source in self.nodes and target in self.nodes:
                    edge = NetworkEdge(
                        self.nodes[source],
                        self.nodes[target],
                        rel["type"],
                    )
                    self.scene.addItem(edge)
                    edge_count += 1

            # Update status
            self.status_label.setText(
                f"Loaded {len(device_list)} devices and {edge_count} connections"
            )

            # Apply selected layout
            self.apply_layout()

        except Exception as e:
            logger.error(f"Failed to load topology: {e}", exc_info=True)
            self.status_label.setText(f"Error loading topology: {str(e)}")

    def apply_layout(self):
        """Apply selected layout algorithm."""
        layout_type = self.layout_combo.currentText()

        if not self.nodes:
            return

        node_list = list(self.nodes.values())
        n = len(node_list)

        if layout_type == "Circular":
            # Circular layout
            radius = 300
            for i, node in enumerate(node_list):
                angle = (2 * math.pi * i) / n
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                node.setPos(x, y)

        elif layout_type == "Force-Directed":
            # Simple force-directed layout (spring embedding)
            iterations = 100
            k = 200  # Optimal distance
            area = 800 * 800

            for _ in range(iterations):
                # Repulsive forces
                for i, node1 in enumerate(node_list):
                    force_x = 0
                    force_y = 0

                    for j, node2 in enumerate(node_list):
                        if i != j:
                            dx = node1.x() - node2.x()
                            dy = node1.y() - node2.y()
                            distance = math.sqrt(dx * dx + dy * dy) or 0.001

                            # Repulsive force
                            force = (k * k) / distance
                            force_x += (dx / distance) * force
                            force_y += (dy / distance) * force

                    # Attractive forces (edges)
                    for edge in node1.edges:
                        other = edge.target if edge.source == node1 else edge.source
                        dx = node1.x() - other.x()
                        dy = node1.y() - other.y()
                        distance = math.sqrt(dx * dx + dy * dy) or 0.001

                        # Attractive force
                        force = (distance * distance) / k
                        force_x -= (dx / distance) * force
                        force_y -= (dy / distance) * force

                    # Apply forces
                    node1.setPos(
                        node1.x() + force_x * 0.01,
                        node1.y() + force_y * 0.01,
                    )

        elif layout_type == "Hierarchical":
            # Simple hierarchical layout (by level)
            levels: Dict[str, int] = {}

            # Assign levels (BFS-like)
            if node_list:
                queue = [(node_list[0], 0)]
                visited = set()

                while queue:
                    node, level = queue.pop(0)
                    if node.node_id not in visited:
                        visited.add(node.node_id)
                        levels[node.node_id] = level

                        for edge in node.edges:
                            other = edge.target if edge.source == node else edge.source
                            if other.node_id not in visited:
                                queue.append((other, level + 1))

            # Position nodes by level
            level_nodes: Dict[int, List[NetworkNode]] = {}
            for node in node_list:
                level = levels.get(node.node_id, 0)
                if level not in level_nodes:
                    level_nodes[level] = []
                level_nodes[level].append(node)

            y_spacing = 150
            for level, nodes in level_nodes.items():
                x_spacing = 800 / (len(nodes) + 1)
                for i, node in enumerate(nodes):
                    x = -400 + (i + 1) * x_spacing
                    y = level * y_spacing
                    node.setPos(x, y)

    def set_zoom(self, value: int):
        """Set zoom level."""
        scale = value / 100.0
        self.view.resetTransform()
        self.view.scale(scale, scale)

    def refresh(self):
        """Refresh the topology view."""
        self.load_topology()

    def update_neo4j_settings(self, uri: str, username: str, password: str):
        """Update Neo4j connection settings."""
        self.neo4j_uri = uri
        self.neo4j_username = username
        self.neo4j_password = password

        # Close existing connection
        if self.driver:
            self.driver.close()
            self.driver = None

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.close()
