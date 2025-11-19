/**
 * StatusModal.js
 * Modal component for displaying device/interface details
 * Triggered by clicking on D3 leaf nodes or Cytoscape context menu
 */

import React from 'react';

const StatusModal = ({ isOpen, onClose, data }) => {
  if (!isOpen || !data) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'up':
        return 'text-green-600 bg-green-100';
      case 'down':
        return 'text-red-600 bg-red-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const handleSSH = () => {
    const ip = data.deviceIP || data.ip;
    if (ip) {
      // Simulate SSH connection (in real app, this would trigger terminal)
      window.open(`ssh://${ip}`, '_blank');
      alert(`Opening SSH connection to ${ip}\n\nIn production, this would launch your SSH client.`);
    }
  };

  const handleTrace = () => {
    alert(`Tracing route to ${data.name || data.label}...\n\nThis would show the path through the network.`);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-auto">
          {/* Header */}
          <div className="border-b border-gray-200 px-6 py-4 flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {data.name || data.label}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {data.type === 'interface' ? 'Network Interface' : 'Network Device'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {/* Status Badge */}
            <div className="mb-6">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(data.status)}`}>
                <span className="w-2 h-2 mr-2 rounded-full bg-current"></span>
                {data.status?.toUpperCase()}
              </span>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              {data.ip && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">IP Address</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{data.ip}</dd>
                </div>
              )}
              {data.deviceIP && data.deviceIP !== data.ip && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Device IP</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{data.deviceIP}</dd>
                </div>
              )}
              {data.deviceName && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Device Name</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.deviceName}</dd>
                </div>
              )}
              {data.speed && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Speed</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.speed}</dd>
                </div>
              )}
              {data.vlan && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">VLAN</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.vlan}</dd>
                </div>
              )}
              {data.model && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Model</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.model}</dd>
                </div>
              )}
              {data.serialNumber && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Serial Number</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{data.serialNumber}</dd>
                </div>
              )}
              {data.version && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Software Version</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.version}</dd>
                </div>
              )}
              {data.deviceType && (
                <div>
                  <dt className="text-sm font-medium text-gray-500">Device Type</dt>
                  <dd className="mt-1 text-sm text-gray-900 capitalize">{data.deviceType}</dd>
                </div>
              )}
              {data.description && (
                <div className="col-span-2">
                  <dt className="text-sm font-medium text-gray-500">Description</dt>
                  <dd className="mt-1 text-sm text-gray-900">{data.description}</dd>
                </div>
              )}
            </div>

            {/* Configuration */}
            {data.config && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Configuration</h3>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm font-mono">
                  {data.config}
                </pre>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleSSH}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                SSH Connect
              </button>
              <button
                onClick={handleTrace}
                className="flex-1 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Trace Route
              </button>
              <button
                onClick={onClose}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default StatusModal;
