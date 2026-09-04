import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Search, Shield, AlertTriangle, FileText, CheckCircle2, 
  Clock, MapPin, Phone, User, Building, Car, GitCommit,
  ZoomIn, ZoomOut, Maximize, Filter, Download, Activity,
  ChevronRight, MoreVertical, X, Check, Eye, Database,
  FileCheck, ShieldAlert, Layers
} from 'lucide-react';

// --- STYLING CONSTANTS (Strict adherence to provided system) ---
const COLORS = {
  bgApp: '#181B21',
  bgPanel: '#22262E',
  bgElevated: '#2C313A',
  primary: '#3B82F6',
  critical: '#EF4444',
  warning: '#F59E0B',
  safe: '#10B981',
  border: '#374151',
  textMain: '#F9FAFB',
  textSec: '#9CA3AF',
  textTech: '#6B7280'
};

// --- MOCK DATA (Structured, analytical, realistic) ---
const MOCK_CASE = {
  id: 'CASE-2026-NCRB-8842',
  name: 'Op: Shadow Node (Inter-State Smuggling)',
  status: 'Active',
  priority: 'High',
  lastUpdated: '2026-09-03T10:30:00Z'
};

const ENTITY_TYPES = {
  PERSON: { icon: User, color: '#9CA3AF' },
  PHONE: { icon: Phone, color: '#9CA3AF' },
  ORGANIZATION: { icon: Building, color: '#9CA3AF' },
  LOCATION: { icon: MapPin, color: '#9CA3AF' },
  VEHICLE: { icon: Car, color: '#9CA3AF' }
};

const INITIAL_NODES = [
  { id: 'n1', type: 'PERSON', label: 'Vikram "Vicky" Sharma', influence: 85, x: 400, y: 300, data: { dob: '1985-04-12', nationality: 'Indian', status: 'Primary Suspect', identifiers: ['AADHAAR: **** **** 4821'] } },
  { id: 'n2', type: 'PHONE', label: '+91 98765 43210', influence: 40, x: 250, y: 200, data: { carrier: 'Airtel', status: 'Active' } },
  { id: 'n3', type: 'PHONE', label: '+91 91234 56789', influence: 30, x: 250, y: 400, data: { carrier: 'Jio', status: 'Burner' } },
  { id: 'n4', type: 'ORGANIZATION', label: 'Sunrise Imports Ltd.', influence: 60, x: 600, y: 150, data: { reg: 'CIN-U51909MH2018PTC301234', address: 'Navi Mumbai' } },
  { id: 'n5', type: 'PERSON', label: 'Rahul Desai', influence: 65, x: 600, y: 450, data: { dob: '1990-11-22', role: 'Logistics Coordinator' } },
  { id: 'n6', type: 'LOCATION', label: 'Warehouse B, Nhava Sheva', influence: 50, x: 800, y: 300, data: { type: 'Commercial', surveillance: 'Yes' } },
  { id: 'n7', type: 'VEHICLE', label: 'MH-04-AB-1234 (Truck)', influence: 45, x: 750, y: 550, data: { owner: 'Sunrise Imports Ltd.', type: 'Heavy Commercial' } },
  { id: 'n8', type: 'PERSON', label: 'Amit Singh', influence: 70, x: 100, y: 300, data: { dob: '1982-01-05', role: 'Financier' } },
];

const INITIAL_EDGES = [
  { id: 'e1', source: 'n1', target: 'n2', type: 'OWNERSHIP', status: 'VERIFIED', date: '2025-10-01', sourceDoc: 'CDR-2025-10' },
  { id: 'e2', source: 'n1', target: 'n3', type: 'COMMUNICATION', status: 'VERIFIED', date: '2026-02-14', sourceDoc: 'CDR-2026-02' },
  { id: 'e3', source: 'n1', target: 'n4', type: 'DIRECTOR', status: 'SUGGESTED', confidence: 0.92, reasoning: 'Entity signature matches ROC filing DOC-882 found on seized hard drive.', sourceDoc: 'Extracted ROC JSON', date: '2023-05-10' },
  { id: 'e4', source: 'n1', target: 'n5', type: 'ASSOCIATE', status: 'VERIFIED', date: '2025-11-20', sourceDoc: 'Surveillance Report 44' },
  { id: 'e5', source: 'n5', target: 'n6', type: 'FREQUENTS', status: 'VERIFIED', date: '2026-08-01', sourceDoc: 'Location Data (Cell Tower)' },
  { id: 'e6', source: 'n6', target: 'n7', type: 'SEEN_AT', status: 'SUGGESTED', confidence: 0.78, reasoning: 'ANPR camera logs indicate vehicle presence during anomalous late-night hours.', sourceDoc: 'ANPR-Log-08-2026', date: '2026-08-15' },
  { id: 'e7', source: 'n8', target: 'n1', type: 'FINANCIAL', status: 'SUGGESTED', confidence: 0.88, reasoning: 'Multiple suspected hawala transactions correlate with node n1 movements.', sourceDoc: 'FIU-IND Report 2026-A', date: '2026-07-22' },
];

// --- REUSABLE UI COMPONENTS (Strict design system) ---

const Panel = ({ children, className = '', elevated = false }) => (
  <div className={`rounded-lg border border-[#374151] ${elevated ? 'bg-[#2C313A] shadow-lg' : 'bg-[#22262E]'} ${className}`}>
    {children}
  </div>
);

const Button = ({ children, variant = 'primary', size = 'md', icon: Icon, onClick, disabled, className = '' }) => {
  const baseStyle = "inline-flex items-center justify-center font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed rounded";
  const sizes = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    icon: "p-1.5"
  };
  const variants = {
    primary: "bg-[#3B82F6] text-white hover:bg-blue-600 border border-transparent",
    secondary: "bg-transparent text-[#F9FAFB] border border-[#374151] hover:bg-[#374151]",
    danger: "bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/30 hover:bg-[#EF4444]/20",
    success: "bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 hover:bg-[#10B981]/20",
    ghost: "bg-transparent text-[#9CA3AF] hover:text-[#F9FAFB] hover:bg-[#374151]/50 border border-transparent"
  };

  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={`${baseStyle} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {Icon && <Icon className={`${children ? 'mr-1.5' : ''} w-4 h-4`} />}
      {children}
    </button>
  );
};

const Badge = ({ children, variant = 'neutral', className = '' }) => {
  const variants = {
    neutral: "bg-[#374151] text-[#F9FAFB]",
    critical: "bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/30",
    warning: "bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/30",
    safe: "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30",
    primary: "bg-[#3B82F6]/20 text-[#3B82F6] border border-[#3B82F6]/30",
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded border border-transparent ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
};

// --- MAIN APPLICATION CONTENT ---

export default function App() {
  const [currentView, setCurrentView] = useState('workspace'); // dashboard, workspace, alerts, review
  const [role, setRole] = useState('OFFICER'); // OFFICER, VIEWER
  
  // Graph State
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [edges, setEdges] = useState(INITIAL_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  
  // Handlers
  const handleApproveEdge = (edgeId) => {
    if (role !== 'OFFICER') return;
    setEdges(edges.map(e => e.id === edgeId ? { ...e, status: 'VERIFIED' } : e));
  };

  const handleRejectEdge = (edgeId) => {
    if (role !== 'OFFICER') return;
    setEdges(edges.map(e => e.id === edgeId ? { ...e, status: 'REJECTED' } : e));
  };

  const selectedNode = nodes.find(n => n.id === selectedNodeId);
  const connectedEdges = edges.filter(e => e.source === selectedNodeId || e.target === selectedNodeId);

  return (
    <div className="flex h-screen w-full bg-[#181B21] text-[#F9FAFB] font-sans overflow-hidden selection:bg-[#3B82F6]/30">
      
      {/* Sidebar - Compact & Operational */}
      <div className="w-16 md:w-56 border-r border-[#374151] bg-[#181B21] flex flex-col justify-between shrink-0">
        <div>
          <div className="h-14 flex items-center justify-center md:justify-start md:px-4 border-b border-[#374151]">
            <Shield className="w-6 h-6 text-[#3B82F6] md:mr-2 shrink-0" />
            <span className="font-semibold text-sm hidden md:block tracking-wide">NCRB WSD</span>
          </div>
          <nav className="p-2 space-y-1 mt-2">
            {[
              { id: 'dashboard', icon: Activity, label: 'Dashboard' },
              { id: 'workspace', icon: GitCommit, label: 'Workspace' },
              { id: 'alerts', icon: ShieldAlert, label: 'Alerts' },
              { id: 'review', icon: FileCheck, label: 'Pending Review' },
              { id: 'documents', icon: Database, label: 'Source DB' },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`w-full flex items-center p-2 rounded text-sm transition-colors ${
                  currentView === item.id 
                    ? 'bg-[#3B82F6]/10 text-[#3B82F6]' 
                    : 'text-[#9CA3AF] hover:bg-[#22262E] hover:text-[#F9FAFB]'
                }`}
                title={item.label}
              >
                <item.icon className="w-5 h-5 md:mr-3 shrink-0" />
                <span className="hidden md:block">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
        
        {/* User Context */}
        <div className="p-4 border-t border-[#374151]">
          <div className="flex items-center cursor-pointer" onClick={() => setRole(role === 'OFFICER' ? 'VIEWER' : 'OFFICER')} title="Toggle Role (Demo)">
            <div className="w-8 h-8 rounded bg-[#2C313A] flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-[#9CA3AF]" />
            </div>
            <div className="ml-3 hidden md:block">
              <div className="text-xs font-medium">I. Sharma</div>
              <div className="text-[10px] text-[#6B7280] uppercase tracking-wider font-mono">{role}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Header - Case Context */}
        <header className="h-14 border-b border-[#374151] bg-[#181B21] flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center">
            <Badge variant="primary" className="font-mono mr-3 hidden sm:inline-block">{MOCK_CASE.id}</Badge>
            <h1 className="text-sm font-semibold truncate">{MOCK_CASE.name}</h1>
          </div>
          <div className="flex items-center space-x-2">
            <div className="relative hidden md:block">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#6B7280]" />
              <input 
                type="text" 
                placeholder="Search entities, IDs..." 
                className="bg-[#22262E] border border-[#374151] rounded pl-9 pr-3 py-1.5 text-sm focus:outline-none focus:border-[#3B82F6] text-[#F9FAFB] placeholder-[#6B7280] w-64 transition-colors"
              />
            </div>
            <Button variant="ghost" size="icon"><AlertTriangle className="w-4 h-4 text-[#F59E0B]" /></Button>
          </div>
        </header>

        {/* View Routing */}
        <main className="flex-1 overflow-hidden relative bg-[#181B21]">
          {currentView === 'workspace' && (
            <WorkspaceView 
              nodes={nodes} 
              edges={edges} 
              selectedNode={selectedNode} 
              connectedEdges={connectedEdges}
              setSelectedNodeId={setSelectedNodeId}
              handleApproveEdge={handleApproveEdge}
              handleRejectEdge={handleRejectEdge}
              role={role}
            />
          )}
          {currentView === 'dashboard' && <DashboardView />}
          {currentView === 'alerts' && <AlertsView />}
          {currentView === 'review' && <ReviewView />}
          {currentView === 'documents' && <PlaceholderView title="Source Database" desc="Document upload and OCR pipeline visualization goes here." />}
        </main>
      </div>
    </div>
  );
}

// --- VIEWS ---

function WorkspaceView({ nodes, edges, selectedNode, connectedEdges, setSelectedNodeId, handleApproveEdge, handleRejectEdge, role }) {
  // Graph Canvas State
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef(null);

  // Pan & Zoom Implementation
  const handleWheel = (e) => {
    e.preventDefault();
    const zoomSensitivity = 0.001;
    const delta = -e.deltaY * zoomSensitivity;
    const newK = Math.max(0.2, Math.min(transform.k + delta, 4)); // clamp zoom
    
    // Zoom towards mouse pointer logic (simplified for single file)
    setTransform(prev => ({ ...prev, k: newK })); 
  };

  const handleMouseDown = (e) => {
    if (e.target.tagName !== 'svg') return; // Only pan on background
    setIsDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setTransform(prev => ({
      ...prev,
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    }));
  };

  const handleMouseUp = () => setIsDragging(false);

  return (
    <div className="w-full h-full flex flex-col md:flex-row">
      
      {/* Graph Area */}
      <div className="flex-1 relative overflow-hidden bg-[#181B21]"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        {/* Subtle grid background */}
        <div className="absolute inset-0 pointer-events-none opacity-[0.03]" 
             style={{ backgroundImage: 'linear-gradient(#F9FAFB 1px, transparent 1px), linear-gradient(90deg, #F9FAFB 1px, transparent 1px)', backgroundSize: '20px 20px' }}>
        </div>

        {/* Graph Controls Toolbar */}
        <div className="absolute top-4 left-4 flex flex-col gap-2 z-10">
          <Panel className="p-1 flex flex-col gap-1">
            <Button variant="ghost" size="icon" onClick={() => setTransform(prev => ({ ...prev, k: prev.k * 1.2 }))}><ZoomIn /></Button>
            <Button variant="ghost" size="icon" onClick={() => setTransform(prev => ({ ...prev, k: prev.k / 1.2 }))}><ZoomOut /></Button>
            <Button variant="ghost" size="icon" onClick={() => setTransform({ x: 0, y: 0, k: 1 })}><Maximize /></Button>
          </Panel>
          <Panel className="p-1 flex flex-col gap-1">
            <Button variant="ghost" size="icon" title="Filter"><Filter /></Button>
            <Button variant="ghost" size="icon" title="Layout Mode"><Layers /></Button>
          </Panel>
        </div>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
          <Panel className="p-3 text-xs flex flex-col gap-2 opacity-80 backdrop-blur">
            <div className="flex items-center gap-2"><div className="w-4 h-0.5 bg-[#374151]"></div><span>Verified Connection</span></div>
            <div className="flex items-center gap-2"><div className="w-4 h-0.5 border-t border-dashed border-[#F59E0B]"></div><span>AI Suggested (Pending)</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full border border-[#3B82F6] bg-transparent"></div><span>Selected Entity</span></div>
          </Panel>
        </div>

        {/* SVG Canvas */}
        <svg 
          ref={svgRef}
          className={`w-full h-full ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
        >
          <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
            
            {/* Edges */}
            {edges.filter(e => e.status !== 'REJECTED').map(edge => {
              const source = nodes.find(n => n.id === edge.source);
              const target = nodes.find(n => n.id === edge.target);
              if (!source || !target) return null;
              
              const isSelected = selectedNode?.id === source.id || selectedNode?.id === target.id;
              const isSuggested = edge.status === 'SUGGESTED';
              
              return (
                <g key={edge.id} className="transition-opacity duration-200" style={{ opacity: selectedNode && !isSelected ? 0.2 : 1 }}>
                  <line
                    x1={source.x} y1={source.y}
                    x2={target.x} y2={target.y}
                    stroke={isSuggested ? '#F59E0B' : '#374151'}
                    strokeWidth={isSelected ? 2 : 1.5}
                    strokeDasharray={isSuggested ? "4,4" : "none"}
                    fill="none"
                  />
                  {/* Label on path - simple midpoint calculation */}
                  {isSelected && (
                    <text 
                      x={(source.x + target.x) / 2} 
                      y={((source.y + target.y) / 2) - 5}
                      fill={isSuggested ? '#F59E0B' : '#9CA3AF'}
                      fontSize="10"
                      fontFamily="monospace"
                      textAnchor="middle"
                      className="select-none pointer-events-none"
                    >
                      {edge.type}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(node => {
              const isSelected = selectedNode?.id === node.id;
              const isDimmed = selectedNode && !isSelected && !edges.some(e => (e.source === selectedNode.id && e.target === node.id) || (e.target === selectedNode.id && e.source === node.id));
              
              // Calculate radius based on influence (clamped for UI sanity)
              const r = 12 + (node.influence / 100) * 15; 
              const Icon = ENTITY_TYPES[node.type]?.icon || User;
              
              return (
                <g 
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => setSelectedNodeId(isSelected ? null : node.id)}
                  className="cursor-pointer transition-opacity duration-200"
                  style={{ opacity: isDimmed ? 0.2 : 1 }}
                >
                  {/* Selection Halo */}
                  {isSelected && <circle r={r + 6} fill="none" stroke="#3B82F6" strokeWidth="2" strokeDasharray="4,4" className="animate-[spin_10s_linear_infinite]" />}
                  
                  {/* Node Base */}
                  <circle 
                    r={r} 
                    fill="#22262E" 
                    stroke={isSelected ? '#3B82F6' : '#374151'} 
                    strokeWidth={isSelected ? 2 : 1} 
                  />
                  
                  {/* Icon */}
                  <foreignObject x={-r} y={-r} width={r*2} height={r*2} className="pointer-events-none flex items-center justify-center">
                    <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
                       <Icon size={r} strokeWidth={1.5} />
                    </div>
                  </foreignObject>

                  {/* Label */}
                  <text 
                    y={r + 14} 
                    fill={isSelected ? '#F9FAFB' : '#9CA3AF'} 
                    fontSize="12" 
                    textAnchor="middle"
                    className="select-none pointer-events-none font-medium drop-shadow-md"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* Details Panel (Right Sidebar) */}
      <div className={`w-full md:w-80 bg-[#22262E] border-l border-[#374151] flex flex-col shrink-0 transition-transform duration-300 ${selectedNode ? 'translate-x-0' : 'translate-x-full absolute right-0 h-full hidden md:flex md:translate-x-0 md:static'}`}>
        {selectedNode ? (
          <>
            {/* Entity Header */}
            <div className="p-4 border-b border-[#374151] relative shrink-0">
              <button onClick={() => setSelectedNodeId(null)} className="absolute top-4 right-4 text-[#6B7280] hover:text-[#F9FAFB]"><X className="w-4 h-4" /></button>
              <div className="flex items-center gap-2 mb-2 text-xs font-mono text-[#9CA3AF] uppercase">
                {React.createElement(ENTITY_TYPES[selectedNode.type]?.icon || User, { className: "w-3 h-3" })}
                {selectedNode.type}
              </div>
              <h2 className="text-base font-semibold text-[#F9FAFB] leading-tight pr-6">{selectedNode.label}</h2>
              <div className="text-xs font-mono text-[#6B7280] mt-1">ID: {selectedNode.id}</div>
              
              <div className="mt-4 flex gap-2">
                 <Button variant="secondary" size="sm" className="flex-1" icon={ZoomIn}>Focus</Button>
                 <Button variant="secondary" size="sm" icon={MoreVertical} />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-6">
              
              {/* Properties */}
              <section>
                <h3 className="text-xs font-semibold text-[#F9FAFB] mb-3 uppercase tracking-wider">Properties</h3>
                <div className="space-y-2">
                  {Object.entries(selectedNode.data).map(([key, value]) => (
                    <div key={key} className="flex flex-col">
                      <span className="text-[10px] text-[#6B7280] uppercase font-mono">{key}</span>
                      <span className="text-sm text-[#F9FAFB] bg-[#181B21] px-2 py-1 rounded border border-[#374151] mt-1 break-words">
                        {Array.isArray(value) ? value.join(', ') : value}
                      </span>
                    </div>
                  ))}
                  <div className="flex flex-col">
                     <span className="text-[10px] text-[#6B7280] uppercase font-mono">System Influence</span>
                     <div className="flex items-center mt-1 gap-2">
                        <div className="h-2 flex-1 bg-[#181B21] rounded overflow-hidden border border-[#374151]">
                           <div className="h-full bg-[#3B82F6]" style={{ width: `${selectedNode.influence}%` }}></div>
                        </div>
                        <span className="text-xs font-mono text-[#9CA3AF]">{selectedNode.influence}</span>
                     </div>
                  </div>
                </div>
              </section>

              {/* Connections (The critical investigation part) */}
              <section>
                <h3 className="text-xs font-semibold text-[#F9FAFB] mb-3 uppercase tracking-wider flex items-center justify-between">
                  Connections
                  <Badge variant="neutral">{connectedEdges.filter(e => e.status !== 'REJECTED').length}</Badge>
                </h3>
                
                <div className="space-y-3">
                  {connectedEdges.filter(e => e.status !== 'REJECTED').map(edge => {
                    const isSource = edge.source === selectedNode.id;
                    const otherNodeId = isSource ? edge.target : edge.source;
                    const otherNode = nodes.find(n => n.id === otherNodeId);
                    const isSuggested = edge.status === 'SUGGESTED';

                    return (
                      <div key={edge.id} className={`p-3 rounded border text-sm flex flex-col gap-2 ${isSuggested ? 'bg-[#F59E0B]/5 border-[#F59E0B]/20' : 'bg-[#181B21] border-[#374151]'}`}>
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex flex-col min-w-0">
                            <span className="text-xs font-mono text-[#6B7280] uppercase">{edge.type}</span>
                            <span className="text-[#F9FAFB] font-medium truncate" title={otherNode?.label}>{otherNode?.label}</span>
                          </div>
                          {isSuggested ? (
                             <Badge variant="warning">AI Sug.</Badge>
                          ) : (
                             <Badge variant="safe" className="bg-transparent border-transparent px-0"><CheckCircle2 className="w-4 h-4" /></Badge>
                          )}
                        </div>

                        {/* Reasoning / Evidence Block */}
                        <div className="bg-[#22262E] p-2 rounded text-xs border border-[#374151]">
                           <div className="flex justify-between items-center mb-1">
                              <span className="text-[#9CA3AF] font-mono text-[10px]">EVIDENCE SOURCE</span>
                              <span className="text-[#3B82F6] font-mono hover:underline cursor-pointer flex items-center gap-1">
                                <FileText className="w-3 h-3" /> {edge.sourceDoc}
                              </span>
                           </div>
                           {isSuggested && (
                             <>
                                <div className="text-[#F9FAFB] mt-2 mb-2 leading-relaxed">
                                  {edge.reasoning}
                                </div>
                                <div className="flex justify-between items-center mt-2 pt-2 border-t border-[#374151]">
                                   <div className="text-[10px] font-mono text-[#F59E0B]">CONFIDENCE: {(edge.confidence * 100).toFixed(1)}%</div>
                                   {role === 'OFFICER' ? (
                                      <div className="flex gap-1">
                                        <Button variant="danger" size="icon" onClick={() => handleRejectEdge(edge.id)}><X /></Button>
                                        <Button variant="success" size="icon" onClick={() => handleApproveEdge(edge.id)}><Check /></Button>
                                      </div>
                                   ) : (
                                      <span className="text-[10px] text-[#6B7280]">Officer review required</span>
                                   )}
                                </div>
                             </>
                           )}
                           {!isSuggested && (
                              <div className="text-[#6B7280] mt-1 font-mono text-[10px]">Verified from records. Date: {edge.date}</div>
                           )}
                        </div>
                      </div>
                    );
                  })}
                  {connectedEdges.filter(e => e.status !== 'REJECTED').length === 0 && (
                    <div className="text-sm text-[#6B7280] italic text-center py-4">No active connections found.</div>
                  )}
                </div>
              </section>

            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-[#6B7280]">
            <Layers className="w-12 h-12 mb-4 opacity-20" />
            <p className="text-sm">Select an entity on the canvas to view details, connections, and evidence logic.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function DashboardView() {
  return (
    <div className="p-6 h-full overflow-y-auto">
      <h2 className="text-lg font-semibold mb-6">Operational Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Active Investigations', val: '24', icon: Activity },
          { label: 'Pending AI Reviews', val: '142', icon: GitCommit, alert: true },
          { label: 'High Priority Alerts', val: '3', icon: AlertTriangle, critical: true },
          { label: 'Entities Tracked', val: '8,492', icon: Database }
        ].map((stat, i) => (
          <Panel key={i} className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-[#9CA3AF] mb-1 font-mono uppercase tracking-wider">{stat.label}</div>
              <div className={`text-2xl font-semibold ${stat.critical ? 'text-[#EF4444]' : stat.alert ? 'text-[#F59E0B]' : 'text-[#F9FAFB]'}`}>
                {stat.val}
              </div>
            </div>
            <stat.icon className={`w-8 h-8 opacity-20 ${stat.critical ? 'text-[#EF4444]' : 'text-[#F9FAFB]'}`} />
          </Panel>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Panel className="flex flex-col h-80">
          <div className="p-4 border-b border-[#374151] flex justify-between items-center">
            <h3 className="text-sm font-semibold">Priority Cases</h3>
            <Button variant="ghost" size="sm">View All</Button>
          </div>
          <div className="p-2 overflow-y-auto">
            {[1,2,3].map(i => (
              <div key={i} className="flex items-center justify-between p-3 hover:bg-[#2C313A] rounded cursor-pointer border border-transparent hover:border-[#374151] mb-1">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${i===1 ? 'bg-[#EF4444]' : 'bg-[#F59E0B]'}`}></div>
                  <div>
                    <div className="text-sm font-medium">CASE-2026-NCRB-884{i}</div>
                    <div className="text-xs text-[#9CA3AF]">Last updated 2h ago</div>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-[#6B7280]" />
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="flex flex-col h-80">
          <div className="p-4 border-b border-[#374151]">
            <h3 className="text-sm font-semibold">Connection Growth Alert</h3>
          </div>
          <div className="p-6 flex flex-col justify-center flex-1">
            <div className="flex items-start gap-4 p-4 rounded bg-[#EF4444]/10 border border-[#EF4444]/30">
              <AlertTriangle className="w-6 h-6 text-[#EF4444] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-[#EF4444] font-semibold text-sm mb-1">Anomalous Network Expansion</h4>
                <p className="text-sm text-[#F9FAFB] leading-relaxed mb-3">
                  System detected <span className="font-mono font-bold">47 new connections</span> formed around entity "Sunrise Imports Ltd." within the last 72 hours following document batch upload [BATCH-09-02].
                </p>
                <Button variant="danger" size="sm">Investigate Sub-Graph</Button>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function AlertsView() {
  const alerts = [
    { id: 1, type: 'CRITICAL', msg: 'New relationship detected involving Priority Suspect (n1) in newly uploaded FIR-2026-99.', time: '10 mins ago' },
    { id: 2, type: 'WARNING', msg: 'Potential Entity Merge: "Rahul Sharma" and "R. Sharma" show 85% attribute overlap.', time: '2 hours ago' },
    { id: 3, type: 'WARNING', msg: 'Financial transaction pattern matches known typologies for shell company obfuscation.', time: '1 day ago' },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold">System Alerts</h2>
        <Button variant="secondary" size="sm" icon={Filter}>Filter Alerts</Button>
      </div>
      
      <div className="space-y-3">
        {alerts.map(alert => (
          <Panel key={alert.id} className="p-4 flex flex-col md:flex-row gap-4 md:items-center justify-between border-l-4" style={{ borderLeftColor: alert.type === 'CRITICAL' ? COLORS.critical : COLORS.warning }}>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant={alert.type.toLowerCase()}>{alert.type}</Badge>
                <span className="text-xs text-[#6B7280] font-mono">{alert.time}</span>
              </div>
              <p className="text-sm text-[#F9FAFB]">{alert.msg}</p>
            </div>
            <div className="flex gap-2 shrink-0">
               <Button variant="secondary" size="sm">Dismiss</Button>
               <Button variant="primary" size="sm">Investigate</Button>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}

function ReviewView() {
  return (
    <div className="p-6 h-full flex flex-col">
       <h2 className="text-lg font-semibold mb-2">Data Extraction Verification</h2>
       <p className="text-sm text-[#9CA3AF] mb-6">Review structured JSON extracted via LLM against source documents before committing to case database.</p>
       
       <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
          {/* Source Document View (Mock) */}
          <Panel className="flex flex-col h-full overflow-hidden">
             <div className="p-3 border-b border-[#374151] bg-[#181B21] flex justify-between items-center text-xs font-mono text-[#9CA3AF]">
                <span>SOURCE: INTERROGATION_TRANSCRIPT_04.pdf</span>
                <span className="px-2 py-0.5 bg-[#2C313A] rounded">PAGE 2/5</span>
             </div>
             <div className="p-6 flex-1 overflow-y-auto bg-[#D1D5DB] text-black font-serif text-sm leading-relaxed" style={{ backgroundImage: 'linear-gradient(rgba(0,0,0,0.05) 1px, transparent 1px)', backgroundSize: '100% 24px', lineHeight: '24px' }}>
                <p>... During questioning on the 14th, the subject mentioned a contact only known as "Bhaiya" who operates out of a warehouse near the old port area. Phone records later retrieved showed frequent calls to <span className="bg-yellow-300 px-1 font-bold">+91-98765-43210</span> late at night.</p>
                <p className="mt-4">The subject denied any affiliation with <span className="bg-yellow-300 px-1 font-bold">Sunrise Imports</span>, though a business card was found in his wallet...</p>
             </div>
          </Panel>

          {/* JSON Review */}
          <Panel className="flex flex-col h-full overflow-hidden">
            <div className="p-3 border-b border-[#374151] bg-[#181B21] flex justify-between items-center">
                <Badge variant="warning">AI Extraction (Confidence: 89%)</Badge>
                <div className="flex gap-2">
                   <Button variant="secondary" size="sm">Edit Raw</Button>
                </div>
             </div>
             <div className="p-4 flex-1 overflow-y-auto bg-[#181B21] font-mono text-sm">
<pre className="text-[#F9FAFB] whitespace-pre-wrap">
<span className="text-[#3B82F6]">{"{"}</span>
  <span className="text-[#10B981]">"entities_extracted"</span>: [
    {"{"}
      <span className="text-[#10B981]">"type"</span>: <span className="text-[#F59E0B]">"PHONE"</span>,
      <span className="text-[#10B981]">"value"</span>: <span className="text-[#F59E0B]">"+919876543210"</span>,
      <span className="text-[#10B981]">"context"</span>: <span className="text-[#F59E0B]">"Frequent late night calls mentioned by subject."</span>
    {"}"},
    {"{"}
      <span className="text-[#10B981]">"type"</span>: <span className="text-[#F59E0B]">"ORGANIZATION"</span>,
      <span className="text-[#10B981]">"value"</span>: <span className="text-[#F59E0B]">"Sunrise Imports"</span>,
      <span className="text-[#10B981]">"context"</span>: <span className="text-[#F59E0B]">"Business card found in wallet, subject denied affiliation."</span>
    {"}"}
  ],
  <span className="text-[#10B981]">"suggested_relationships"</span>: [
    {"{"}
      <span className="text-[#10B981]">"source"</span>: <span className="text-[#F59E0B]">"Subject (Implicit)"</span>,
      <span className="text-[#10B981]">"target"</span>: <span className="text-[#F59E0B]">"+919876543210"</span>,
      <span className="text-[#10B981]">"type"</span>: <span className="text-[#F59E0B]">"CALLS"</span>
    {"}"}
  ]
<span className="text-[#3B82F6]">{"}"}</span>
</pre>
             </div>
             <div className="p-4 border-t border-[#374151] flex justify-end gap-3 bg-[#22262E]">
                <Button variant="danger">Reject All</Button>
                <Button variant="primary" icon={Check}>Verify & Commit to Graph</Button>
             </div>
          </Panel>
       </div>
    </div>
  );
}

function PlaceholderView({ title, desc }) {
  return (
    <div className="w-full h-full flex items-center justify-center p-6 text-center">
      <div className="max-w-md">
        <Database className="w-12 h-12 text-[#374151] mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">{title}</h2>
        <p className="text-[#9CA3AF] text-sm leading-relaxed">{desc}</p>
        <p className="mt-4 text-xs font-mono text-[#6B7280]">Focus of prototype is on Graph Workspace & Review.</p>
      </div>
    </div>
  );
}