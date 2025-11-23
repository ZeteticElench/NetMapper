#!/usr/bin/env python3
"""
NetMapper PySide6 GUI - Main Window

Network topology discovery and visualization with DMTF CIM relationship management.
"""

import sys
import logging
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QStatusBar,
    QToolBar,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QSettings

from .discovery_tab import DiscoveryTab
from .topology_tab import TopologyTab
from .cim_relationships_tab import CIMRelationshipsTab
from .query_tab import QueryTab
from .settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class NetMapperMainWindow(QMainWindow):
    """Main window for NetMapper GUI application."""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("NetMapper", "NetMapperGUI")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("NetMapper - Network Topology Discovery")
        self.setMinimumSize(1200, 800)

        # Create central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create tab widgets
        self.discovery_tab = DiscoveryTab(self)
        self.topology_tab = TopologyTab(self)
        self.cim_tab = CIMRelationshipsTab(self)
        self.query_tab = QueryTab(self)

        # Add tabs
        self.tabs.addTab(self.discovery_tab, "Discovery")
        self.tabs.addTab(self.topology_tab, "Topology")
        self.tabs.addTab(self.cim_tab, "CIM Relationships")
        self.tabs.addTab(self.query_tab, "Query")

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Apply stylesheet
        self.apply_stylesheet()

    def create_toolbar(self):
        """Create application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.setStatusTip("Open settings dialog")
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setStatusTip("Refresh current view")
        refresh_action.triggered.connect(self.refresh_current_tab)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # About action
        about_action = QAction("About", self)
        about_action.setStatusTip("About NetMapper")
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

    def apply_stylesheet(self):
        """Apply modern dark theme stylesheet."""
        stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QTabWidget::pane {
            border: 1px solid #444;
            background-color: #2b2b2b;
        }
        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ddd;
            padding: 8px 16px;
            border: 1px solid #444;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background-color: #2b2b2b;
            color: #fff;
        }
        QTabBar::tab:hover {
            background-color: #4a4a4a;
        }
        QLabel {
            color: #ddd;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
            background-color: #3c3c3c;
            color: #ddd;
            border: 1px solid #555;
            padding: 4px;
        }
        QPushButton {
            background-color: #0d7377;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #14b1b8;
        }
        QPushButton:pressed {
            background-color: #0a5c5f;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #888;
        }
        QTableWidget, QTreeWidget {
            background-color: #3c3c3c;
            color: #ddd;
            border: 1px solid #555;
            gridline-color: #555;
        }
        QTableWidget::item:selected, QTreeWidget::item:selected {
            background-color: #0d7377;
        }
        QHeaderView::section {
            background-color: #2b2b2b;
            color: #ddd;
            padding: 4px;
            border: 1px solid #555;
        }
        QStatusBar {
            background-color: #2b2b2b;
            color: #ddd;
        }
        QToolBar {
            background-color: #3c3c3c;
            border-bottom: 1px solid #555;
            spacing: 3px;
            padding: 4px;
        }
        QGroupBox {
            color: #ddd;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }
        """
        self.setStyleSheet(stylesheet)

    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.load_settings()
            self.statusBar.showMessage("Settings updated", 3000)

    def refresh_current_tab(self):
        """Refresh the currently active tab."""
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, "refresh"):
            current_widget.refresh()
            self.statusBar.showMessage("Refreshed", 2000)

    def show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>NetMapper</h2>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Network Topology Discovery Tool</b></p>
        <p>Features:</p>
        <ul>
        <li>Automated network discovery via CDP/LLDP</li>
        <li>DMTF CIM-based relationship modeling</li>
        <li>Neo4j graph database storage</li>
        <li>Interactive topology visualization</li>
        <li>STP and VLAN analysis</li>
        </ul>
        <p><b>Technologies:</b> PyATS, Neo4j, PySide6, DMTF CIM</p>
        <p>© 2024 NetMapper Project</p>
        """
        QMessageBox.about(self, "About NetMapper", about_text)

    def load_settings(self):
        """Load application settings."""
        # Restore window geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Load Neo4j connection settings
        neo4j_uri = self.settings.value("neo4j/uri", "bolt://localhost:7687")
        neo4j_user = self.settings.value("neo4j/username", "neo4j")
        neo4j_pass = self.settings.value("neo4j/password", "password")

        # Propagate settings to tabs
        for tab in [self.discovery_tab, self.topology_tab, self.cim_tab, self.query_tab]:
            if hasattr(tab, "update_neo4j_settings"):
                tab.update_neo4j_settings(neo4j_uri, neo4j_user, neo4j_pass)

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window geometry
        self.settings.setValue("geometry", self.saveGeometry())

        # Close Neo4j connections in tabs
        for tab in [self.discovery_tab, self.topology_tab, self.cim_tab, self.query_tab]:
            if hasattr(tab, "cleanup"):
                tab.cleanup()

        event.accept()


def main():
    """Main entry point for GUI application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("NetMapper")
    app.setOrganizationName("NetMapper")

    # Create and show main window
    window = NetMapperMainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
