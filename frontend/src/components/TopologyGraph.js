/**
 * TopologyGraph.js
 * Cytoscape.js Network Topology visualization with Compound Nodes
 * Based on: https://js.cytoscape.org/demos/compound-nodes/
 *
 * Features:
 * - Compound nodes (nested boxes) for Data Centers, Racks, Devices
 * - Interface nodes with connections
 * - fcose layout for non-overlapping compound nodes
 * - Circular context menu on interface nodes
 */

import React, { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import cxtmenu from 'cytoscape-cxtmenu';

// Register extensions
cytoscape.use(fcose);
cytoscape.use(cxtmenu);

const TopologyGraph = ({ data, onNodeClick }) => {
  const containerRef = useRef();
  const cyRef = useRef(null);

  useEffect(() => {
    if (!data || !containerRef.current) return;

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Create Cytoscape instance
    const cy = cytoscape({
      container: containerRef.current,

      elements: [
        ...data.nodes,
        ...data.edges,
      ],

      style: [
        // Datacenter style (largest container)
        {
          selector: 'node[type="datacenter"]',
          style: {
            'background-color': '#1e40af',
            'background-opacity': 0.1,
            'border-width': 3,
            'border-color': '#1e40af',
            'label': 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'font-size': '16px',
            'font-weight': 'bold',
            'color': '#1e40af',
            'padding': '20px',
          }
        },
        // Rack style (medium container)
        {
          selector: 'node[type="rack"]',
          style: {
            'background-color': '#3b82f6',
            'background-opacity': 0.1,
            'border-width': 2,
            'border-color': '#3b82f6',
            'label': 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'font-size': '14px',
            'font-weight': 'bold',
            'color': '#3b82f6',
            'padding': '15px',
          }
        },
        // Device style (small container)
        {
          selector: 'node[type="device"]',
          style: {
            'background-color': '#60a5fa',
            'background-opacity': 0.15,
            'border-width': 2,
            'border-color': '#60a5fa',
            'label': 'data(label)',
            'text-valign': 'top',
            'text-halign': 'center',
            'font-size': '12px',
            'font-weight': 'bold',
            'color': '#60a5fa',
            'padding': '10px',
          }
        },
        // Interface style (leaf nodes)
        {
          selector: 'node[type="interface"]',
          style: {
            'width': 30,
            'height': 30,
            'background-color': (ele) => {
              const status = ele.data('status');
              if (status === 'up') return '#10b981';
              if (status === 'down') return '#ef4444';
              if (status === 'warning') return '#f59e0b';
              return '#6b7280';
            },
            'label': 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'font-size': '10px',
            'color': '#333',
            'text-background-color': '#fff',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px',
          }
        },
        // Status-based styles
        {
          selector: 'node[status="up"]',
          style: {
            'border-color': '#10b981',
          }
        },
        {
          selector: 'node[status="down"]',
          style: {
            'border-color': '#ef4444',
          }
        },
        {
          selector: 'node[status="warning"]',
          style: {
            'border-color': '#f59e0b',
          }
        },
        // Edge styles
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': (ele) => {
              const status = ele.data('status');
              if (status === 'up') return '#10b981';
              if (status === 'down') return '#ef4444';
              return '#6b7280';
            },
            'target-arrow-color': (ele) => {
              const status = ele.data('status');
              if (status === 'up') return '#10b981';
              if (status === 'down') return '#ef4444';
              return '#6b7280';
            },
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'opacity': 0.6,
          }
        },
        // Highlighted edge
        {
          selector: 'edge.highlighted',
          style: {
            'width': 4,
            'opacity': 1,
            'line-color': '#8b5cf6',
            'target-arrow-color': '#8b5cf6',
          }
        },
      ],

      layout: {
        name: 'fcose',
        quality: 'proof',
        randomize: false,
        animate: true,
        animationDuration: 1000,
        fit: true,
        padding: 30,
        nodeDimensionsIncludeLabels: true,
        uniformNodeDimensions: false,
        packComponents: true,
        nodeRepulsion: 8000,
        idealEdgeLength: 100,
        edgeElasticity: 0.45,
        nestingFactor: 0.1,
        gravity: 0.25,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 10,
        tilingPaddingHorizontal: 10,
      },

      minZoom: 0.1,
      maxZoom: 3,
    });

    cyRef.current = cy;

    // Context menu for interface nodes
    const menu = cy.cxtmenu({
      selector: 'node[type="interface"]',
      commands: [
        {
          content: '<span style="font-size: 12px; font-weight: bold;">⚙️ Config</span>',
          select: (ele) => {
            if (onNodeClick) {
              onNodeClick(ele.data());
            }
          },
        },
        {
          content: '<span style="font-size: 12px; font-weight: bold;">🔍 Trace</span>',
          select: (ele) => {
            const data = ele.data();
            alert(`Tracing route to ${data.label}...\n\nThis would show the path through the network.`);
          },
        },
        {
          content: '<span style="font-size: 12px; font-weight: bold;">💻 SSH</span>',
          select: (ele) => {
            const data = ele.data();
            const ip = data.deviceIP || data.ip;
            if (ip) {
              window.open(`ssh://${ip}`, '_blank');
              alert(`Opening SSH connection to ${ip}\n\nIn production, this would launch your SSH client.`);
            }
          },
        },
      ],
      fillColor: 'rgba(0, 0, 0, 0.75)',
      activeFillColor: 'rgba(59, 130, 246, 0.75)',
      activePadding: 20,
      indicatorSize: 24,
      separatorWidth: 3,
      spotlightPadding: 4,
      minSpotlightRadius: 24,
      maxSpotlightRadius: 38,
      openMenuEvents: 'cxttapstart taphold',
      itemColor: 'white',
      itemTextShadowColor: 'transparent',
      zIndex: 9999,
      atMouse: false,
    });

    // Click handler for interface nodes (double click)
    cy.on('dbltap', 'node[type="interface"]', (evt) => {
      if (onNodeClick) {
        onNodeClick(evt.target.data());
      }
    });

    // Highlight connected edges on hover
    cy.on('mouseover', 'node[type="interface"]', (evt) => {
      const node = evt.target;
      node.connectedEdges().addClass('highlighted');
    });

    cy.on('mouseout', 'node[type="interface"]', (evt) => {
      const node = evt.target;
      node.connectedEdges().removeClass('highlighted');
    });

    // Fit to screen
    cy.fit();

    // Cleanup
    return () => {
      if (menu) {
        menu.destroy();
      }
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [data, onNodeClick]);

  return (
    <div className="w-full h-full relative">
      <div ref={containerRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-4 z-10">
        <h3 className="font-bold text-sm mb-2">Status Legend</h3>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-green-500"></div>
            <span className="text-xs">Up</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
            <span className="text-xs">Warning</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-red-500"></div>
            <span className="text-xs">Down</span>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-200">
          <p className="text-xs text-gray-600">
            Right-click interface nodes for options
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Double-click for details
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-2 flex gap-2 z-10">
        <button
          onClick={() => cyRef.current?.fit()}
          className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
          title="Fit to screen"
        >
          🔍 Fit
        </button>
        <button
          onClick={() => cyRef.current?.reset()}
          className="px-3 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors text-sm"
          title="Reset zoom"
        >
          ↻ Reset
        </button>
      </div>
    </div>
  );
};

export default TopologyGraph;
