"""Query and browse tab for Neo4j database."""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSplitter,
    QComboBox,
)
from PySide6.QtCore import Qt

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class QueryTab(QWidget):
    """Tab for running Cypher queries against Neo4j."""

    # Predefined query templates
    QUERY_TEMPLATES = {
        "All Devices": "MATCH (d:NetworkDevice) RETURN d.hostname, d.platform, d.model, d.mgmt_ip LIMIT 25",
        "All CIM Relationships": """
            MATCH (parent)-[r]->(child)
            WHERE r.relationship_type IS NOT NULL
            RETURN
                COALESCE(parent.id, parent.hostname) as parent,
                type(r) as relationship,
                COALESCE(child.id, child.hostname) as child,
                r.location_within_container as location
            LIMIT 50
        """,
        "CIM Containers": """
            MATCH (parent)-[r:CIM_CONTAINER]->(child)
            RETURN
                COALESCE(parent.id, parent.hostname) as parent,
                COALESCE(child.id, child.hostname) as child,
                r.location_within_container as location,
                r.removal_conditions as removable
            LIMIT 50
        """,
        "CIM Components": """
            MATCH (parent)-[r:CIM_COMPONENT]->(child)
            WHERE r.is_weak = true
            RETURN
                COALESCE(parent.id, parent.hostname) as parent,
                COALESCE(child.id, child.hostname) as child,
                r.location_within_container as location
            LIMIT 50
        """,
        "Device Connections": """
            MATCH (d1:NetworkDevice)-[r]-(d2:NetworkDevice)
            WHERE type(r) IN ['CDP_NEIGHBOR', 'LLDP_NEIGHBOR']
            RETURN DISTINCT d1.hostname, type(r) as connection_type, d2.hostname
            LIMIT 50
        """,
        "Cables": """
            MATCH (p1:Port)-[:CABLE_END_A]->(c:Cable)<-[:CABLE_END_B]-(p2:Port)
            RETURN
                p1.device_hostname + ':' + p1.name as port1,
                c.id as cable_id,
                c.type as cable_type,
                p2.device_hostname + ':' + p2.name as port2
            LIMIT 50
        """,
        "VLANs": """
            MATCH (d:NetworkDevice)-[:HAS_VLAN]->(v:VLAN)
            RETURN d.hostname, v.vlan_id, v.name, v.status
            ORDER BY v.vlan_id
            LIMIT 50
        """,
        "STP Root Bridges": """
            MATCH (d:NetworkDevice)-[:HAS_STP]->(s:STPInstance)
            WHERE s.is_root = true
            RETURN d.hostname, s.vlan_id, s.bridge_address
            LIMIT 25
        """,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_username = "neo4j"
        self.neo4j_password = "password"
        self.driver = None
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Query template selector
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("Query Template:"))

        self.template_combo = QComboBox()
        self.template_combo.addItems(["Custom"] + list(self.QUERY_TEMPLATES.keys()))
        self.template_combo.currentTextChanged.connect(self.load_template)
        template_layout.addWidget(self.template_combo)

        template_layout.addStretch()
        layout.addLayout(template_layout)

        # Create splitter for query editor and results
        splitter = QSplitter(Qt.Vertical)

        # Query editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        editor_widget.setLayout(editor_layout)

        editor_layout.addWidget(QLabel("Cypher Query:"))

        self.query_editor = QTextEdit()
        self.query_editor.setPlaceholderText(
            "Enter Cypher query here...\nExample: MATCH (d:NetworkDevice) RETURN d.hostname LIMIT 10"
        )
        self.query_editor.setMaximumHeight(150)
        editor_layout.addWidget(self.query_editor)

        # Execute button
        execute_button = QPushButton("Execute Query")
        execute_button.clicked.connect(self.execute_query)
        editor_layout.addWidget(execute_button)

        splitter.addWidget(editor_widget)

        # Results table
        results_widget = QWidget()
        results_layout = QVBoxLayout()
        results_widget.setLayout(results_layout)

        results_layout.addWidget(QLabel("Query Results:"))

        self.results_table = QTableWidget()
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)

        # Status label
        self.status_label = QLabel("Ready. Select a template or enter a custom query.")
        results_layout.addWidget(self.status_label)

        splitter.addWidget(results_widget)

        layout.addWidget(splitter)

    def load_template(self, template_name: str):
        """Load a query template into the editor."""
        if template_name == "Custom":
            return

        if template_name in self.QUERY_TEMPLATES:
            query = self.QUERY_TEMPLATES[template_name]
            self.query_editor.setPlainText(query.strip())

    def execute_query(self):
        """Execute the Cypher query and display results."""
        query = self.query_editor.toPlainText().strip()

        if not query:
            self.status_label.setText("Error: Query is empty")
            return

        try:
            # Connect to Neo4j if not connected
            if not self.driver:
                self.driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_username, self.neo4j_password),
                )

            # Execute query
            with self.driver.session() as session:
                result = session.run(query)
                records = list(result)

            # Clear previous results
            self.results_table.clear()
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)

            if not records:
                self.status_label.setText("Query executed successfully. No results returned.")
                return

            # Get column names
            columns = list(records[0].keys())
            self.results_table.setColumnCount(len(columns))
            self.results_table.setHorizontalHeaderLabels(columns)

            # Populate table
            self.results_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                for col_idx, column in enumerate(columns):
                    value = record[column]
                    # Convert value to string
                    if value is None:
                        value_str = "NULL"
                    elif isinstance(value, (dict, list)):
                        value_str = str(value)
                    else:
                        value_str = str(value)

                    item = QTableWidgetItem(value_str)
                    self.results_table.setItem(row_idx, col_idx, item)

            self.status_label.setText(f"Query executed successfully. {len(records)} rows returned.")

        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.results_table.clear()
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)

    def refresh(self):
        """Refresh by re-executing the current query."""
        if self.query_editor.toPlainText().strip():
            self.execute_query()

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
