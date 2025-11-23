"""Settings dialog for NetMapper GUI."""

import logging

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QDialogButtonBox,
)
from PySide6.QtCore import QSettings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("NetMapper", "NetMapperGUI")
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Neo4j connection settings
        neo4j_group = QGroupBox("Neo4j Connection")
        neo4j_layout = QFormLayout()

        self.neo4j_uri_input = QLineEdit()
        self.neo4j_uri_input.setPlaceholderText("bolt://localhost:7687")
        neo4j_layout.addRow("URI:", self.neo4j_uri_input)

        self.neo4j_username_input = QLineEdit()
        self.neo4j_username_input.setPlaceholderText("neo4j")
        neo4j_layout.addRow("Username:", self.neo4j_username_input)

        self.neo4j_password_input = QLineEdit()
        self.neo4j_password_input.setEchoMode(QLineEdit.Password)
        self.neo4j_password_input.setPlaceholderText("password")
        neo4j_layout.addRow("Password:", self.neo4j_password_input)

        # Test connection button
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self.test_connection)
        neo4j_layout.addRow("", test_button)

        neo4j_group.setLayout(neo4j_layout)
        layout.addWidget(neo4j_group)

        # Application settings
        app_group = QGroupBox("Application Settings")
        app_layout = QFormLayout()

        # Add more settings here as needed

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_settings(self):
        """Load settings from QSettings."""
        self.neo4j_uri_input.setText(
            self.settings.value("neo4j/uri", "bolt://localhost:7687")
        )
        self.neo4j_username_input.setText(
            self.settings.value("neo4j/username", "neo4j")
        )
        self.neo4j_password_input.setText(
            self.settings.value("neo4j/password", "password")
        )

    def test_connection(self):
        """Test Neo4j connection with current settings."""
        from PySide6.QtWidgets import QMessageBox
        from neo4j import GraphDatabase

        uri = self.neo4j_uri_input.text()
        username = self.neo4j_username_input.text()
        password = self.neo4j_password_input.text()

        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
            driver.close()

            QMessageBox.information(
                self,
                "Connection Test",
                "Successfully connected to Neo4j!"
            )
        except Exception as e:
            logger.error(f"Connection test failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Connection Test Failed",
                f"Failed to connect to Neo4j:\n{str(e)}"
            )

    def accept(self):
        """Save settings and close dialog."""
        # Save Neo4j settings
        self.settings.setValue("neo4j/uri", self.neo4j_uri_input.text())
        self.settings.setValue("neo4j/username", self.neo4j_username_input.text())
        self.settings.setValue("neo4j/password", self.neo4j_password_input.text())

        super().accept()
