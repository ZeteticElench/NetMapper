/**
 * HierarchyChart.js
 * D3.js Zoomable Circle Packing visualization
 * Based on: https://observablehq.com/@d3/zoomable-circle-packing
 *
 * Hierarchy: Data Center -> Rack -> Device -> Interface
 * Click to zoom in/out, click leaf nodes to open status modal
 */

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const HierarchyChart = ({ data, onNodeClick }) => {
  const svgRef = useRef();
  const containerRef = useRef();

  useEffect(() => {
    if (!data || !svgRef.current) return;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();

    // Get container dimensions
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .style('background', '#f9fafb')
      .style('cursor', 'pointer');

    // Create hierarchy
    const root = d3.hierarchy(data)
      .sum(d => d.type === 'interface' ? 1 : 0)
      .sort((a, b) => b.value - a.value);

    // Create pack layout
    const pack = d3.pack()
      .size([width, height])
      .padding(3);

    pack(root);

    // Color scale based on depth and status
    const getColor = (d) => {
      if (d.data.type === 'interface') {
        // Leaf nodes colored by status
        switch (d.data.status) {
          case 'up':
            return '#10b981'; // green
          case 'down':
            return '#ef4444'; // red
          case 'warning':
            return '#f59e0b'; // yellow
          default:
            return '#6b7280'; // gray
        }
      } else {
        // Non-leaf nodes colored by depth
        const colors = ['#1e40af', '#3b82f6', '#60a5fa', '#93c5fd'];
        return colors[Math.min(d.depth, colors.length - 1)];
      }
    };

    // Create groups
    const node = svg.append('g')
      .selectAll('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', d => `translate(${d.x},${d.y})`)
      .style('cursor', d => d.children ? 'pointer' : 'pointer');

    // Add circles
    node.append('circle')
      .attr('r', d => d.r)
      .attr('fill', d => getColor(d))
      .attr('fill-opacity', d => d.children ? 0.6 : 0.9)
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // Add labels
    const text = node.append('text')
      .attr('text-anchor', 'middle')
      .style('font-size', d => Math.min(d.r / 3, 14) + 'px')
      .style('fill', d => d.children ? '#fff' : '#fff')
      .style('font-weight', d => d.children ? 'bold' : 'normal')
      .style('pointer-events', 'none')
      .style('user-select', 'none');

    // Add name
    text.append('tspan')
      .attr('x', 0)
      .attr('dy', '0.3em')
      .text(d => {
        const name = d.data.name;
        if (!name) return '';

        // Truncate long names
        const maxLength = Math.floor(d.r / 4);
        if (name.length > maxLength) {
          return name.substring(0, maxLength) + '...';
        }
        return name;
      });

    // Add status for leaf nodes
    text.filter(d => !d.children)
      .append('tspan')
      .attr('x', 0)
      .attr('dy', '1.2em')
      .style('font-size', d => Math.min(d.r / 4, 10) + 'px')
      .style('fill-opacity', 0.9)
      .text(d => d.data.status ? d.data.status.toUpperCase() : '');

    // Zoom behavior
    let focus = root;
    let view;

    const zoomTo = (v) => {
      const k = width / v[2];

      view = v;

      text.attr('opacity', d => {
        // Show text only if circle is large enough
        return k * d.r > 10 ? 1 : 0;
      });

      node.attr('transform', d => {
        return `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`;
      });

      node.select('circle')
        .attr('r', d => d.r * k);
    };

    const zoom = (event, d) => {
      event.stopPropagation();

      // If leaf node, open modal instead of zooming
      if (!d.children) {
        if (onNodeClick) {
          onNodeClick(d.data);
        }
        return;
      }

      // Zoom to clicked node
      focus = d;

      const transition = svg.transition()
        .duration(750)
        .tween('zoom', () => {
          const i = d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2]);
          return t => zoomTo(i(t));
        });
    };

    // Click handler
    node.on('click', zoom);

    // Initial zoom
    zoomTo([root.x, root.y, root.r * 2]);

    // Click on background to zoom out
    svg.on('click', (event) => {
      if (event.target === svg.node()) {
        zoom(event, root);
      }
    });

    // Tooltip
    const tooltip = d3.select('body')
      .append('div')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'rgba(0, 0, 0, 0.8)')
      .style('color', '#fff')
      .style('padding', '8px 12px')
      .style('border-radius', '6px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('z-index', '1000');

    node.on('mouseenter', (event, d) => {
      tooltip.style('visibility', 'visible')
        .html(`
          <strong>${d.data.name}</strong><br/>
          Type: ${d.data.type}<br/>
          ${d.data.status ? `Status: ${d.data.status}` : ''}
          ${d.children ? `<br/>Children: ${d.children.length}` : ''}
        `);
    })
    .on('mousemove', (event) => {
      tooltip
        .style('top', (event.pageY - 10) + 'px')
        .style('left', (event.pageX + 10) + 'px');
    })
    .on('mouseleave', () => {
      tooltip.style('visibility', 'hidden');
    });

    // Cleanup
    return () => {
      tooltip.remove();
    };
  }, [data, onNodeClick]);

  return (
    <div ref={containerRef} className="w-full h-full">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
};

export default HierarchyChart;
