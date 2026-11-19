import React, { useState, useEffect } from 'react';

/**
 * SarembokDashboard Component
 * Renders native architectural telemetry assets directly inside the web client layer.
 */
export default function SarembokDashboard() {
  const [systemMetrics, setSystemMetrics] = useState({
    driftDetected: false,
    entropyIndex: 0.14,
    lastChecked: null,
    loading: true,
    error: null
  });

  // Dynamic public path pointer matching our CI output target
  const visualMapUrl = `/generated/visuals/live_drift_map.svg?fresh=${Date.now()}`;

  useEffect(() => {
    async function fetchLocalHealthState() {
      try {
        // Query the local server runtime instance for state parameters
        const response = await fetch('/status');
        if (!response.ok) throw new Error(`HTTP Error: status returned ${response.status}`);
        
        const data = await response.json();
        setSystemMetrics({
          driftDetected: data.drift_detected || false,
          entropyIndex: typeof data.shannon_entropy === 'number' ? data.shannon_entropy : 0.14,
          lastChecked: data.timestamp || new Date().toLocaleTimeString(),
          loading: false,
          error: null
        });
      } catch (err) {
        setSystemMetrics(prev => ({
          ...prev,
          loading: false,
          error: "Could not sync local runtime metadata. Displaying static canvas loop."
        }));
      }
    }

    fetchLocalHealthState();
  }, []);

  return (
    <div style={{ backgroundColor: '#0b0f19', color: '#f8fafc', padding: '24px', fontFamily: 'monospace', minHeight: '100vh' }}>
      {/* Top Banner Status Interface */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #1e293b', paddingBottom: '16px', marginBottom: '24px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '20px', color: '#38bdf8', letterSpacing: '1px' }}>SAREMBOKVE // CORE WORKSPACE</h1>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#64748b' }}>ENGINE INTEGRATION: GEMINI-4-ARGON (ACTIVE)</p>
        </div>
        
        <div style={{ textAlign: 'right' }}>
          <span style={{
            display: 'inline-block',
            padding: '6px 12px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 'bold',
            backgroundColor: systemMetrics.driftDetected ? '#2d161b' : '#062f22',
            color: systemMetrics.driftDetected ? '#f43f5e' : '#34d399',
            border: `1px solid ${systemMetrics.driftDetected ? '#f43f5e' : '#34d399'}`
          }}>
            {systemMetrics.driftDetected ? "⚠️ CONTRACT DRIFT DETECTED" : "● SYSTEM STABLE // NO DRIFT"}
          </span>
        </div>
      </div>

      {/* Primary Visual Matrix Container */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px' }}>
        {/* Left Side: Native Vector Map Area */}
        <div style={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '11px', color: '#475569' }}>[NATIVE_VECTOR_CANVAS]</span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>SCALE: 100% (NON-STREAMED)</span>
          </div>
          
          <div style={{ width: '100%', height: 'auto', minHeight: '360px', overflow: 'hidden', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            {/* Direct projection of the crisp vector graphic compiled by Argon */}
            <object 
              type="image/svg+xml" 
              data={visualMapUrl} 
              style={{ width: '100%', height: '100%', borderRadius: '4px' }}
            >
              <p style={{ color: '#64748b' }}>Parsing vector array stream...</p>
            </object>
          </div>
        </div>

        {/* Right Side: Analytical Control Dashboard Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Metadata Frame */}
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#94a3b8' }}>TELEMETRY SPECS</h3>
            <div style={{ fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>SHANNON ENTROPY:</span>
                <span style={{ color: '#a855f7', fontWeight: 'bold' }}>{systemMetrics.entropyIndex}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>LAST EXTRACTION:</span>
                <span style={{ color: '#cbd5e1' }}>{systemMetrics.lastChecked || "Syncing..."}</span>
              </div>
              {systemMetrics.error && (
                <div style={{ color: '#f59e0b', fontSize: '10px', marginTop: '8px', borderTop: '1px dashed #334155', paddingTop: '8px' }}>
                  {systemMetrics.error}
                </div>
              )}
            </div>
          </div>

          {/* Quick-Action Pipeline Controls */}
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#94a3b8' }}>PLATFORM OVERRIDES</h3>
            <button 
              onClick={() => alert("Re-allocating sandboxed Chromium targets...")}
              style={{ width: '100%', padding: '10px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#cbd5e1', fontSize: '11px', cursor: 'pointer', fontFamily: 'monospace', transition: 'all 0.2s' }}
              onMouseOver={(e) => e.target.style.backgroundColor = '#334155'}
              onMouseOut={(e) => e.target.style.backgroundColor = '#1e293b'}
            >
              EXECUTE NEW EXTRACTION
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
