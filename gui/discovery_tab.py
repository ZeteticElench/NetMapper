"""Discovery configuration and execution tab."""

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
    QSpinBox,
    QCheckBox,
    QTextEdit,
    QProgressBar,
    QFormLayout,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from netmapper.models import DeviceCredentials, DiscoveryConfig

logger = logging.getLogger(__name__)


class DiscoveryWorker(QThread):
    """Worker thread for network discovery."""

    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, config: DiscoveryConfig):
        super().__init__()
        self.config = config
        self._is_running = True

    def run(self):
        """Run discovery in background thread."""
        try:
            from netmapper.hybrid_discovery import HybridNetworkDiscovery

            self.progress.emit("Starting network discovery...")

            # Create discovery instance
            discovery = HybridNetworkDiscovery(self.config)

            # Run discovery
            self.progress.emit("Discovering network topology...")
            discovery.discover()

            self.progress.emit("Discovery completed successfully!")
            self.finished.emit(True, "Discovery completed successfully")

        except Exception as e:
            logger.error(f"Discovery failed: {e}", exc_info=True)
            self.finished.emit(False, f"Discovery failed: {str(e)}")

    def stop(self):
        """Stop the discovery process."""
        self._is_running = False


class DiscoveryTab(QWidget):
    """Tab for configuring and running network discovery."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.neo4j_uri = "bolt://localhost:7687"
        self.neo4j_username = "neo4j"
        self.neo4j_password = "password"
        self.worker: Optional[DiscoveryWorker] = None
        self.setup_ui()

    def setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Device configuration group
        device_group = QGroupBox("Target Device")
        device_layout = QFormLayout()

        self.hostname_input = QLineEdit()
        self.hostname_input.setPlaceholderText("device-hostname")
        device_layout.addRow("Hostname:", self.hostname_input)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.1")
        device_layout.addRow("IP Address:", self.ip_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("admin")
        device_layout.addRow("Username:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        device_layout.addRow("Password:", self.password_input)

        self.enable_password_input = QLineEdit()
        self.enable_password_input.setEchoMode(QLineEdit.Password)
        device_layout.addRow("Enable Password:", self.enable_password_input)

        self.os_combo = QComboBox()
        self.os_combo.addItems(["ios", "iosxe", "nxos", "iosxr", "asa"])
        device_layout.addRow("OS Type:", self.os_combo)

        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # Discovery options group
        options_group = QGroupBox("Discovery Options")
        options_layout = QFormLayout()

        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(1, 100)
        self.max_depth_spin.setValue(10)
        options_layout.addRow("Max Depth:", self.max_depth_spin)

        self.discover_cdp_check = QCheckBox()
        self.discover_cdp_check.setChecked(True)
        options_layout.addRow("Discover CDP:", self.discover_cdp_check)

        self.discover_lldp_check = QCheckBox()
        self.discover_lldp_check.setChecked(True)
        options_layout.addRow("Discover LLDP:", self.discover_lldp_check)

        self.discover_stp_check = QCheckBox()
        self.discover_stp_check.setChecked(True)
        options_layout.addRow("Discover STP:", self.discover_stp_check)

        self.discover_vlans_check = QCheckBox()
        self.discover_vlans_check.setChecked(True)
        options_layout.addRow("Discover VLANs:", self.discover_vlans_check)

        self.enable_bejerano_check = QCheckBox()
        self.enable_bejerano_check.setChecked(True)
        options_layout.addRow("Enable Bejerano L2:", self.enable_bejerano_check)

        self.parallel_check = QCheckBox()
        self.parallel_check.setChecked(True)
        options_layout.addRow("Parallel Discovery:", self.parallel_check)

        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 100)
        self.max_workers_spin.setValue(10)
        options_layout.addRow("Max Workers:", self.max_workers_spin)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Discovery")
        self.start_button.clicked.connect(self.start_discovery)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_discovery)
        button_layout.addWidget(self.stop_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Log output
        log_label = QLabel("Discovery Log:")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        layout.addWidget(self.log_output)

        layout.addStretch()

    def start_discovery(self):
        """Start network discovery process."""
        # Validate inputs
        if not self.hostname_input.text() or not self.ip_input.text():
            self.log("Error: Hostname and IP address are required")
            return

        if not self.username_input.text() or not self.password_input.text():
            self.log("Error: Username and password are required")
            return

        # Create device credentials
        device_creds = DeviceCredentials(
            hostname=self.hostname_input.text(),
            ip=self.ip_input.text(),
            username=self.username_input.text(),
            password=self.password_input.text(),
            enable_password=self.enable_password_input.text() or None,
            os=self.os_combo.currentText(),
        )

        # Create discovery config
        config = DiscoveryConfig(
            start_device=device_creds,
            neo4j_uri=self.neo4j_uri,
            neo4j_username=self.neo4j_username,
            neo4j_password=self.neo4j_password,
            max_depth=self.max_depth_spin.value(),
            discover_cdp=self.discover_cdp_check.isChecked(),
            discover_lldp=self.discover_lldp_check.isChecked(),
            discover_stp=self.discover_stp_check.isChecked(),
            discover_vlans=self.discover_vlans_check.isChecked(),
            enable_bejerano=self.enable_bejerano_check.isChecked(),
            parallel_discovery=self.parallel_check.isChecked(),
            max_workers=self.max_workers_spin.value(),
        )

        # Start worker thread
        self.worker = DiscoveryWorker(config)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.discovery_finished)
        self.worker.start()

        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.log("Discovery started...")

    def stop_discovery(self):
        """Stop the running discovery."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.log("Discovery stopped by user")
            self.discovery_finished(False, "Stopped by user")

    def discovery_finished(self, success: bool, message: str):
        """Handle discovery completion."""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if success else 0)

        self.log(message)

        if success:
            self.log("\nDiscovery complete! Switch to the Topology tab to view results.")

    def log(self, message: str):
        """Add message to log output."""
        self.log_output.append(message)

    def update_neo4j_settings(self, uri: str, username: str, password: str):
        """Update Neo4j connection settings."""
        self.neo4j_uri = uri
        self.neo4j_username = username
        self.neo4j_password = password

    def cleanup(self):
        """Clean up resources."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
