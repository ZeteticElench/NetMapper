"""CIM relationship management tab."""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFormLayout,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QHeaderView,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt

from neo4j import GraphDatabase
from netmapper.models import (
    CIMNestingRelationship,
    CIMRelationshipType,
    RemovalConditions,
)
from netmapper.neo4j_manager import Neo4jManager

logger = logging.getLogger(__name__)


class CIMRelationshipsTab(QWidget):
    """Tab for creating and managing CIM nesting relationships."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_username = "neo4j"
        self.neo4j_password = "password"
        self.manager: Optional[Neo4jManager] = None
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create relationship form
        form_group = QGroupBox("Create CIM Relationship")
        form_layout = QFormLayout()

        self.parent_id_input = QLineEdit()
        self.parent_id_input.setPlaceholderText("e.g., rack-01")
        form_layout.addRow("Parent ID:", self.parent_id_input)

        self.child_id_input = QLineEdit()
        self.child_id_input.setPlaceholderText("e.g., server-01")
        form_layout.addRow("Child ID:", self.child_id_input)

        self.rel_type_combo = QComboBox()
        self.rel_type_combo.addItems([
            "CIM_CONTAINER",
            "CIM_COMPONENT",
            "CIM_MEMBER_OF_COLLECTION",
        ])
        self.rel_type_combo.currentTextChanged.connect(self.on_rel_type_changed)
        form_layout.addRow("Relationship Type:", self.rel_type_combo)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("e.g., U42, Slot 1, Bay 2")
        form_layout.addRow("Location:", self.location_input)

        self.removal_combo = QComboBox()
        self.removal_combo.addItems([
            "Unknown",
            "Not Applicable",
            "Removable when off",
            "Removable when on or off",
        ])
        form_layout.addRow("Removal Conditions:", self.removal_combo)

        self.is_weak_check = QCheckBox()
        self.is_weak_check.setToolTip(
            "If checked, child cannot exist without parent (Composition)"
        )
        form_layout.addRow("Is Weak (Composition):", self.is_weak_check)

        # Custom properties
        self.custom_props_input = QLineEdit()
        self.custom_props_input.setPlaceholderText('JSON: {"key": "value"}')
        form_layout.addRow("Custom Properties:", self.custom_props_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        button_layout = QHBoxLayout()
        create_button = QPushButton("Create Relationship")
        create_button.clicked.connect(self.create_relationship)
        button_layout.addWidget(create_button)

        clear_button = QPushButton("Clear Form")
        clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(clear_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Existing relationships table
        table_label = QLabel("Existing CIM Relationships:")
        layout.addWidget(table_label)

        self.relationships_table = QTableWidget()
        self.relationships_table.setColumnCount(7)
        self.relationships_table.setHorizontalHeaderLabels([
            "Parent ID",
            "Child ID",
            "Type",
            "Location",
            "Removal Conditions",
            "Is Weak",
            "Properties",
        ])
        self.relationships_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        layout.addWidget(self.relationships_table)

        # Control buttons
        table_button_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.load_relationships)
        table_button_layout.addWidget(refresh_button)

        view_hierarchy_button = QPushButton("View Hierarchy Tree")
        view_hierarchy_button.clicked.connect(self.show_hierarchy)
        table_button_layout.addWidget(view_hierarchy_button)

        table_button_layout.addStretch()
        layout.addLayout(table_button_layout)

        # Update form based on initial selection
        self.on_rel_type_changed(self.rel_type_combo.currentText())

    def on_rel_type_changed(self, rel_type: str):
        """Update form fields based on relationship type."""
        if rel_type == "CIM_MEMBER_OF_COLLECTION":
            # Logical relationship - disable physical properties
            self.location_input.setEnabled(False)
            self.removal_combo.setEnabled(False)
            self.is_weak_check.setChecked(False)
        else:
            # Physical relationship - enable all properties
            self.location_input.setEnabled(True)
            self.removal_combo.setEnabled(True)

    def create_relationship(self):
        """Create a new CIM relationship."""
        try:
            # Validate inputs
            parent_id = self.parent_id_input.text().strip()
            child_id = self.child_id_input.text().strip()

            if not parent_id or not child_id:
                QMessageBox.warning(
                    self, "Validation Error", "Parent ID and Child ID are required"
                )
                return

            # Parse custom properties
            custom_props = {}
            if self.custom_props_input.text().strip():
                import json

                try:
                    custom_props = json.loads(self.custom_props_input.text())
                except json.JSONDecodeError:
                    QMessageBox.warning(
                        self, "Validation Error", "Invalid JSON in custom properties"
                    )
                    return

            # Create relationship object
            rel_type_str = self.rel_type_combo.currentText()
            relationship = CIMNestingRelationship(
                parent_id=parent_id,
                child_id=child_id,
                relationship_type=CIMRelationshipType(rel_type_str),
                location_within_container=self.location_input.text().strip() or None,
                removal_conditions=RemovalConditions(self.removal_combo.currentText())
                if self.removal_combo.isEnabled()
                else None,
                is_weak=self.is_weak_check.isChecked(),
                properties=custom_props,
            )

            # Connect to Neo4j and create relationship
            if not self.manager:
                self.manager = Neo4jManager(
                    self.neo4j_uri, self.neo4j_username, self.neo4j_password
                )

            self.manager.create_cim_nesting_relationship(relationship)

            QMessageBox.information(
                self, "Success", "CIM relationship created successfully"
            )

            # Clear form and refresh
            self.clear_form()
            self.load_relationships()

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to create relationship: {str(e)}")

    def clear_form(self):
        """Clear all form fields."""
        self.parent_id_input.clear()
        self.child_id_input.clear()
        self.location_input.clear()
        self.custom_props_input.clear()
        self.rel_type_combo.setCurrentIndex(0)
        self.removal_combo.setCurrentIndex(0)
        self.is_weak_check.setChecked(False)

    def load_relationships(self):
        """Load and display existing CIM relationships."""
        try:
            if not self.manager:
                self.manager = Neo4jManager(
                    self.neo4j_uri, self.neo4j_username, self.neo4j_password
                )

            # Query all CIM relationships
            query = """
            MATCH (parent)-[r]->(child)
            WHERE r.relationship_type IS NOT NULL
            RETURN
                COALESCE(parent.id, parent.hostname) as parent_id,
                COALESCE(child.id, child.hostname) as child_id,
                r.relationship_type as type,
                r.location_within_container as location,
                r.removal_conditions as removal,
                r.is_weak as is_weak,
                properties(r) as props
            """

            with self.manager.driver.session() as session:
                result = session.run(query)
                relationships = list(result)

            # Clear table
            self.relationships_table.setRowCount(0)

            # Populate table
            for row_idx, record in enumerate(relationships):
                self.relationships_table.insertRow(row_idx)

                # Parent ID
                self.relationships_table.setItem(
                    row_idx, 0, QTableWidgetItem(str(record["parent_id"]))
                )

                # Child ID
                self.relationships_table.setItem(
                    row_idx, 1, QTableWidgetItem(str(record["child_id"]))
                )

                # Type
                self.relationships_table.setItem(
                    row_idx, 2, QTableWidgetItem(str(record["type"]))
                )

                # Location
                location = record.get("location") or "N/A"
                self.relationships_table.setItem(
                    row_idx, 3, QTableWidgetItem(str(location))
                )

                # Removal conditions
                removal = record.get("removal") or "N/A"
                self.relationships_table.setItem(
                    row_idx, 4, QTableWidgetItem(str(removal))
                )

                # Is weak
                is_weak = record.get("is_weak", False)
                self.relationships_table.setItem(
                    row_idx, 5, QTableWidgetItem("Yes" if is_weak else "No")
                )

                # Custom properties
                props = record.get("props", {})
                # Filter out standard properties
                custom_props = {
                    k: v
                    for k, v in props.items()
                    if k
                    not in [
                        "relationship_type",
                        "is_weak",
                        "location_within_container",
                        "removal_conditions",
                    ]
                }
                self.relationships_table.setItem(
                    row_idx, 6, QTableWidgetItem(str(custom_props))
                )

        except Exception as e:
            logger.error(f"Failed to load relationships: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Error", f"Failed to load relationships: {str(e)}"
            )

    def show_hierarchy(self):
        """Show hierarchy tree in a dialog."""
        try:
            if not self.manager:
                self.manager = Neo4jManager(
                    self.neo4j_uri, self.neo4j_username, self.neo4j_password
                )

            # Get root nodes (nodes with no parents via CIM relationships)
            query = """
            MATCH (n)
            WHERE NOT EXISTS {
                MATCH (parent)-[r]->(n)
                WHERE r.relationship_type IS NOT NULL
            }
            AND EXISTS {
                MATCH (n)-[r]->(child)
                WHERE r.relationship_type IS NOT NULL
            }
            RETURN COALESCE(n.id, n.hostname) as root_id
            """

            with self.manager.driver.session() as session:
                result = session.run(query)
                root_ids = [record["root_id"] for record in result]

            if not root_ids:
                QMessageBox.information(
                    self, "No Hierarchy", "No CIM hierarchy found in database"
                )
                return

            # Create tree dialog
            from PySide6.QtWidgets import QDialog

            dialog = QDialog(self)
            dialog.setWindowTitle("CIM Hierarchy Tree")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout()
            tree = QTreeWidget()
            tree.setHeaderLabels(["Node", "Type", "Location"])
            tree.setColumnWidth(0, 300)

            # Build tree for each root
            for root_id in root_ids:
                hierarchy = self.manager.get_cim_hierarchy(root_id)
                root_item = self.build_tree_item(hierarchy)
                tree.addTopLevelItem(root_item)
                root_item.setExpanded(True)

            layout.addWidget(tree)

            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            logger.error(f"Failed to show hierarchy: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to show hierarchy: {str(e)}")

    def build_tree_item(self, node_data: dict) -> QTreeWidgetItem:
        """Recursively build tree widget items from hierarchy data."""
        item = QTreeWidgetItem()
        item.setText(0, node_data.get("id", "Unknown"))

        # Add labels
        labels = node_data.get("labels", [])
        item.setText(1, ", ".join(labels) if labels else "N/A")

        # Add location if available
        relationship = node_data.get("relationship", {})
        location = relationship.get("location_within_container", "N/A")
        item.setText(2, location)

        # Add children
        children = node_data.get("children", {})
        for child_data in children.values():
            child_item = self.build_tree_item(child_data)
            item.addChild(child_item)

        return item

    def refresh(self):
        """Refresh the relationships table."""
        self.load_relationships()

    def update_neo4j_settings(self, uri: str, username: str, password: str):
        """Update Neo4j connection settings."""
        self.neo4j_uri = uri
        self.neo4j_username = username
        self.neo4j_password = password

        # Close existing connection
        if self.manager:
            self.manager.close()
            self.manager = None

    def cleanup(self):
        """Clean up resources."""
        if self.manager:
            self.manager.close()
