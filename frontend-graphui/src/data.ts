import { GraphData, GraphNode, GraphEdge } from './types';

/**
 * Generate sample graph data demonstrating information-dense visualization
 */
export function generateSampleGraph(): GraphData {
  const nodes: GraphNode[] = [
    // People
    {
      id: 'p1',
      label: 'Alice Chen',
      type: 'Person',
      properties: {
        age: 32,
        role: 'CEO',
        location: 'San Francisco',
        status: 'active'
      },
      x: 0,
      y: 0,
      importance: 0.9
    },
    {
      id: 'p2',
      label: 'Bob Kumar',
      type: 'Person',
      properties: {
        age: 28,
        role: 'CTO',
        location: 'Seattle',
        experience: '5 years'
      },
      x: 0,
      y: 0,
      importance: 0.8
    },
    {
      id: 'p3',
      label: 'Carol White',
      type: 'Person',
      properties: {
        age: 35,
        role: 'VP Engineering',
        location: 'Austin'
      },
      x: 0,
      y: 0,
      importance: 0.7
    },
    {
      id: 'p4',
      label: 'David Park',
      type: 'Person',
      properties: {
        age: 29,
        role: 'Lead Developer',
        skills: 'Full Stack'
      },
      x: 0,
      y: 0
    },

    // Organizations
    {
      id: 'o1',
      label: 'TechCorp Inc',
      type: 'Organization',
      properties: {
        industry: 'Software',
        founded: 2015,
        employees: 250,
        revenue: '$50M'
      },
      x: 0,
      y: 0,
      importance: 1.0
    },
    {
      id: 'o2',
      label: 'DataSystems LLC',
      type: 'Organization',
      properties: {
        industry: 'Analytics',
        founded: 2018,
        employees: 80
      },
      x: 0,
      y: 0,
      importance: 0.6
    },

    // Products
    {
      id: 'pr1',
      label: 'GraphDB Pro',
      type: 'Product',
      properties: {
        version: '2.5.0',
        price: '$999/mo',
        users: 1500,
        rating: 4.8
      },
      x: 0,
      y: 0,
      importance: 0.8
    },
    {
      id: 'pr2',
      label: 'AnalyticsPlatform',
      type: 'Product',
      properties: {
        version: '1.2.0',
        price: '$499/mo',
        users: 800
      },
      x: 0,
      y: 0
    },

    // Locations
    {
      id: 'l1',
      label: 'San Francisco HQ',
      type: 'Location',
      properties: {
        address: '123 Market St',
        capacity: 300,
        floor: '15-17'
      },
      x: 0,
      y: 0
    },
    {
      id: 'l2',
      label: 'Seattle Office',
      type: 'Location',
      properties: {
        address: '456 Pine Ave',
        capacity: 100
      },
      x: 0,
      y: 0
    },

    // Events
    {
      id: 'e1',
      label: 'Product Launch 2024',
      type: 'Event',
      properties: {
        date: '2024-03-15',
        attendees: 500,
        budget: '$100k'
      },
      x: 0,
      y: 0,
      importance: 0.7
    },
    {
      id: 'e2',
      label: 'Team Offsite Q1',
      type: 'Event',
      properties: {
        date: '2024-01-20',
        attendees: 50
      },
      x: 0,
      y: 0
    },

    // Documents
    {
      id: 'd1',
      label: 'Q4 Strategy',
      type: 'Document',
      properties: {
        type: 'Strategy Doc',
        pages: 45,
        confidential: true
      },
      x: 0,
      y: 0
    },
    {
      id: 'd2',
      label: 'Tech Roadmap',
      type: 'Document',
      properties: {
        type: 'Roadmap',
        year: 2024
      },
      x: 0,
      y: 0
    },

    // Concepts
    {
      id: 'c1',
      label: 'Graph Databases',
      type: 'Concept',
      properties: {
        category: 'Technology',
        maturity: 'Established'
      },
      x: 0,
      y: 0
    },
    {
      id: 'c2',
      label: 'AI/ML',
      type: 'Concept',
      properties: {
        category: 'Technology',
        trend: 'Growing'
      },
      x: 0,
      y: 0
    }
  ];

  const edges: GraphEdge[] = [
    // Leadership relationships
    { source: 'p1', target: 'o1', type: 'LEADS', weight: 2.5 },
    { source: 'p2', target: 'o1', type: 'WORKS_AT', weight: 2.0 },
    { source: 'p3', target: 'o1', type: 'WORKS_AT', weight: 2.0 },
    { source: 'p4', target: 'o1', type: 'WORKS_AT', weight: 1.5 },

    // Reporting structure
    { source: 'p2', target: 'p1', type: 'REPORTS_TO', weight: 1.8 },
    { source: 'p3', target: 'p1', type: 'REPORTS_TO', weight: 1.8 },
    { source: 'p4', target: 'p3', type: 'REPORTS_TO', weight: 1.5 },

    // Product relationships
    { source: 'o1', target: 'pr1', type: 'DEVELOPS', weight: 2.0 },
    { source: 'o2', target: 'pr2', type: 'DEVELOPS', weight: 2.0 },
    { source: 'p2', target: 'pr1', type: 'MANAGES', weight: 1.7 },
    { source: 'p4', target: 'pr1', type: 'CONTRIBUTES', weight: 1.5 },

    // Location relationships
    { source: 'o1', target: 'l1', type: 'LOCATED_AT', weight: 1.5 },
    { source: 'o1', target: 'l2', type: 'HAS_OFFICE', weight: 1.2 },
    { source: 'p1', target: 'l1', type: 'BASED_IN', weight: 1.0 },
    { source: 'p2', target: 'l2', type: 'BASED_IN', weight: 1.0 },

    // Event relationships
    { source: 'e1', target: 'pr1', type: 'LAUNCHES', weight: 2.0 },
    { source: 'p1', target: 'e1', type: 'ORGANIZES', weight: 1.5 },
    { source: 'p2', target: 'e1', type: 'ATTENDS', weight: 1.2 },
    { source: 'e2', target: 'o1', type: 'HOSTED_BY', weight: 1.3 },

    // Document relationships
    { source: 'd1', target: 'o1', type: 'ABOUT', weight: 1.5 },
    { source: 'd2', target: 'pr1', type: 'DESCRIBES', weight: 1.5 },
    { source: 'p1', target: 'd1', type: 'AUTHORED', weight: 1.3 },
    { source: 'p2', target: 'd2', type: 'AUTHORED', weight: 1.3 },

    // Concept relationships
    { source: 'pr1', target: 'c1', type: 'IMPLEMENTS', weight: 1.8 },
    { source: 'pr2', target: 'c2', type: 'USES', weight: 1.6 },
    { source: 'c1', target: 'c2', type: 'RELATES_TO', weight: 1.0 },

    // Partnership
    { source: 'o1', target: 'o2', type: 'PARTNERS_WITH', weight: 1.5 },

    // Cross-functional
    { source: 'p3', target: 'pr2', type: 'COLLABORATES', weight: 1.2 },
    { source: 'p4', target: 'c1', type: 'EXPERT_IN', weight: 1.4 }
  ];

  return { nodes, edges };
}

/**
 * Generate a larger random graph for stress testing
 */
export function generateLargeGraph(nodeCount: number = 100): GraphData {
  const types = ['Person', 'Organization', 'Product', 'Location', 'Event', 'Document', 'Concept'];
  const nodes: GraphNode[] = [];

  for (let i = 0; i < nodeCount; i++) {
    const type = types[Math.floor(Math.random() * types.length)];
    nodes.push({
      id: `n${i}`,
      label: `${type} ${i}`,
      type,
      properties: {
        id: i,
        random: Math.random().toFixed(3),
        category: ['A', 'B', 'C'][Math.floor(Math.random() * 3)]
      },
      x: 0,
      y: 0,
      importance: Math.random()
    });
  }

  const edges: GraphEdge[] = [];
  const edgeCount = Math.floor(nodeCount * 1.5);

  for (let i = 0; i < edgeCount; i++) {
    const source = nodes[Math.floor(Math.random() * nodes.length)].id;
    const target = nodes[Math.floor(Math.random() * nodes.length)].id;

    if (source !== target) {
      edges.push({
        source,
        target,
        type: ['RELATES', 'CONNECTS', 'LINKS'][Math.floor(Math.random() * 3)],
        weight: 0.5 + Math.random() * 2
      });
    }
  }

  return { nodes, edges };
}
