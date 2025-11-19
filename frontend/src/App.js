/**
 * App.js
 * Main application component for Network Infrastructure Dashboard
 *
 * Features:
 * - View toggle between Hierarchy (D3) and Topology (Cytoscape)
 * - Shared Status Modal
 * - Data generation and management
 */

import React, { useState, useEffect } from 'react';
import HierarchyChart from './components/HierarchyChart';
import TopologyGraph from './components/TopologyGraph';
import StatusModal from './components/StatusModal';
import generateNetworkData from './utils/DataGenerator';

function App() {
  const [view, setView] = useState('hierarchy'); // 'hierarchy' or 'topology'
  const [networkData, setNetworkData] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [stats, setStats] = useState({
    totalDevices: 0,
    totalInterfaces: 0,
    upInterfaces: 0,
    downInterfaces: 0,
    warningInterfaces: 0,
  });

  // Generate data on mount
  useEffect(() => {
    const data = generateNetworkData(2); // 2 data centers
    setNetworkData(data);

    // Calculate stats
    let totalDevices = 0;
    let totalInterfaces = 0;
    let upInterfaces = 0;
    let downInterfaces = 0;
    let warningInterfaces = 0;

    data.hierarchy.children.forEach(dc => {
      dc.children.forEach(rack => {
        totalDevices += rack.children.length;
        rack.children.forEach(device => {
          totalInterfaces += device.children.length;
          device.children.forEach(iface => {
            if (iface.status === 'up') upInterfaces++;
            else if (iface.status === 'down') downInterfaces++;
            else if (iface.status === 'warning') warningInterfaces++;
          });
        });
      });
    });

    setStats({
      totalDevices,
      totalInterfaces,
      upInterfaces,
      downInterfaces,
      warningInterfaces,
    });
  }, []);

  const handleNodeClick = (nodeData) => {
    setSelectedNode(nodeData);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedNode(null);
  };

  const handleRegenerateData = () => {
    const data = generateNetworkData(2);
    setNetworkData(data);
    setModalOpen(false);

    // Recalculate stats
    let totalDevices = 0;
    let totalInterfaces = 0;
    let upInterfaces = 0;
    let downInterfaces = 0;
    let warningInterfaces = 0;

    data.hierarchy.children.forEach(dc => {
      dc.children.forEach(rack => {
        totalDevices += rack.children.length;
        rack.children.forEach(device => {
          totalInterfaces += device.children.length;
          device.children.forEach(iface => {
            if (iface.status === 'up') upInterfaces++;
            else if (iface.status === 'down') downInterfaces++;
            else if (iface.status === 'warning') warningInterfaces++;
          });
        });
      });
    });

    setStats({
      totalDevices,
      totalInterfaces,
      upInterfaces,
      downInterfaces,
      warningInterfaces,
    });
  };

  if (!networkData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Generating network topology...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Network Infrastructure Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Visualize network topology and device status
              </p>
            </div>

            {/* View Toggle */}
            <div className="flex items-center gap-4">
              <div className="bg-gray-200 rounded-lg p-1 flex">
                <button
                  onClick={() => setView('hierarchy')}
                  className={`px-4 py-2 rounded-md transition-all ${
                    view === 'hierarchy'
                      ? 'bg-white text-blue-600 shadow-sm font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  📊 Hierarchy View
                </button>
                <button
                  onClick={() => setView('topology')}
                  className={`px-4 py-2 rounded-md transition-all ${
                    view === 'topology'
                      ? 'bg-white text-blue-600 shadow-sm font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  🌐 Topology View
                </button>
              </div>

              <button
                onClick={handleRegenerateData}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Regenerate
              </button>
            </div>
          </div>

          {/* Stats Bar */}
          <div className="mt-4 grid grid-cols-5 gap-4">
            <div className="bg-blue-50 rounded-lg px-4 py-3">
              <div className="text-2xl font-bold text-blue-600">{stats.totalDevices}</div>
              <div className="text-sm text-gray-600">Devices</div>
            </div>
            <div className="bg-gray-50 rounded-lg px-4 py-3">
              <div className="text-2xl font-bold text-gray-600">{stats.totalInterfaces}</div>
              <div className="text-sm text-gray-600">Interfaces</div>
            </div>
            <div className="bg-green-50 rounded-lg px-4 py-3">
              <div className="text-2xl font-bold text-green-600">{stats.upInterfaces}</div>
              <div className="text-sm text-gray-600">Up</div>
            </div>
            <div className="bg-yellow-50 rounded-lg px-4 py-3">
              <div className="text-2xl font-bold text-yellow-600">{stats.warningInterfaces}</div>
              <div className="text-sm text-gray-600">Warning</div>
            </div>
            <div className="bg-red-50 rounded-lg px-4 py-3">
              <div className="text-2xl font-bold text-red-600">{stats.downInterfaces}</div>
              <div className="text-sm text-gray-600">Down</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6">
        <div className="bg-white rounded-lg shadow-lg h-full overflow-hidden">
          {view === 'hierarchy' && (
            <div className="h-full p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">
                    Hierarchical Circle Packing
                  </h2>
                  <p className="text-sm text-gray-600">
                    Click clusters to zoom in, click leaf nodes for details
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Color by status:</span>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <span className="text-xs">Up</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                      <span className="text-xs">Warning</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <span className="text-xs">Down</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="h-[calc(100%-4rem)]">
                <HierarchyChart
                  data={networkData.hierarchy}
                  onNodeClick={handleNodeClick}
                />
              </div>
            </div>
          )}

          {view === 'topology' && (
            <div className="h-full">
              <div className="px-4 pt-4 pb-2">
                <h2 className="text-xl font-semibold text-gray-900">
                  Network Topology Graph
                </h2>
                <p className="text-sm text-gray-600">
                  Compound nodes with fcose layout | Right-click or double-click interfaces
                </p>
              </div>
              <div className="h-[calc(100%-5rem)]">
                <TopologyGraph
                  data={networkData.topology}
                  onNodeClick={handleNodeClick}
                />
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Status Modal */}
      <StatusModal
        isOpen={modalOpen}
        onClose={handleCloseModal}
        data={selectedNode}
      />
    </div>
  );
}

export default App;
