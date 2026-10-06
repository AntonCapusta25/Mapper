import { useState, useEffect, useRef } from 'react';

const API = window.location.origin;

interface SearchSession {
  id: string;
  intent: string;
  status: string;
  created_at: string;
}

interface Lead {
  id: number;
  name: string;
  email: string;
  website: string;
  phone: string;
  location: string;
  query: string;
  is_opened: number;
  last_interaction: string | null;
}

interface Message {
  id: string;
  lead_id: number;
  direction: 'sent' | 'received';
  subject: string;
  body: string;
  created_at: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'run' | 'live' | 'history'>('run');

  // Generator State
  const [intent, setIntent] = useState("");
  const [queryCount, setQueryCount] = useState(20);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQueries, setGeneratedQueries] = useState<{label: string, query: string, selected: boolean}[]>([]);
  
  // Run State
  const [isRunning, setIsRunning] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);
  
  // History State
  const [sessions, setSessions] = useState<SearchSession[]>([]);
  const [selectedSessionLeads, setSelectedSessionLeads] = useState<Lead[]>([]);
  const [viewingSessionId, setViewingSessionId] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // GAS State
  const [webhookUrl, setWebhookUrl] = useState("https://script.google.com/macros/s/AKfycbyw19qTJv3O3qrs-ZUdbfYBuHXEUx4YO5Fg0PfoQlzxBb-5nnPOBGi4DTyQ_k-SF_-2/exec");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [isSendingGas, setIsSendingGas] = useState(false);

  // Campaign Synthesis State
  const [isReferral, setIsReferral] = useState(false);
  const [meetingLink, setMeetingLink] = useState("");
  const [campaignTemplate, setCampaignTemplate] = useState<{subject: string, html_body: string} | null>(null);
  const [isGeneratingCampaign, setIsGeneratingCampaign] = useState(false);
  const [showCampaignPreview, setShowCampaignPreview] = useState(false);

  // CRM State
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [leadHistory, setLeadHistory] = useState<Message[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [replyText, setReplyText] = useState("");

  // SSE for Logs & Autonomous Handshake
  useEffect(() => {
    if (!isRunning) return;
    const eventSource = new EventSource(`${API}/api/logs`);
    eventSource.onmessage = (event) => {
      const line = event.data;
      setLogs(prev => [...prev.slice(-100), line]);
      
      // Completion Detection
      if (line.includes("✨ [AI] Campaign synthesis complete")) {
        handleFetchAutomatedCampaign();
      }
      
      if (line.includes("🏁 entire sequence finished.") || line.includes('[TASK_DONE]')) {
        setIsRunning(false);
        eventSource.close();
      }
    };
    eventSource.onerror = () => eventSource.close();
    return () => eventSource.close();
  }, [isRunning, taskId]);

  // Auto-Sync Responses Polling
  useEffect(() => {
    const interval = setInterval(() => {
      if (webhookUrl) syncResponses();
    }, 60000); // Every 60s
    return () => clearInterval(interval);
  }, [webhookUrl, viewingSessionId]);

  // Omnichannel Sync: Poll for active tasks started via Bot
  useEffect(() => {
    const pollActiveTask = async () => {
      // Don't poll if we're already running a local task as it might conflict
      if (isRunning) return; 
      
      try {
        const res = await fetch(`${API}/api/active-task`);
        const info = await res.json();
        if (info.id) {
          setTaskId(info.id);
          setIntent(info.intent || "");
          setIsRunning(true);
          setActiveTab('live'); // Auto-switch to live tab to show logs
        }
      } catch (err) {
        console.error("Failed to poll active task:", err);
      }
    };

    const interval = setInterval(pollActiveTask, 3000);
    return () => clearInterval(interval);
  }, [taskId, isRunning]);

  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Load History
  const fetchHistory = async () => {
    try {
      setConnectionError(null);
      const res = await fetch(`${API}/api/history`);
      if(res.ok) {
        setSessions(await res.json());
      } else {
        setConnectionError(`Server responded with status ${res.status}`);
      }
    } catch(e) {
      setConnectionError("SSL Connection Blocked. Your browser does not trust the self-signed certificate yet.");
      console.error("History fetch error:", e);
    }
  };

  const trustBackend = () => {
    // Open the backend URL in a new tab so the browser can show the "Proceed anyway" screen
    window.open(`${API}/api/history`, '_blank');
  };

  useEffect(() => {
    if (activeTab === 'history') fetchHistory();
  }, [activeTab]);

  const viewSession = async (id: string) => {
    try {
      const res = await fetch(`${API}/api/history/${id}/leads`);
      if(res.ok) {
        setSelectedSessionLeads(await res.json());
        setViewingSessionId(id);
      }
    } catch(e) {}
  };

  const syncResponses = async () => {
    setIsSyncing(true);
    try {
      await fetch(`${API}/api/sync-responses?webhook_url=${encodeURIComponent(webhookUrl)}`, { method: "POST" });
      if (viewingSessionId) viewSession(viewingSessionId); // Refresh current view
    } catch(e) {}
    setIsSyncing(false);
  };

  const fetchLeadHistory = async (lead: Lead) => {
    setSelectedLead(lead);
    try {
      const res = await fetch(`${API}/api/history/${lead.id}/messages`);
      if(res.ok) setLeadHistory(await res.json());
    } catch(e) {}
  };

  const deleteSession = async (id: string) => {
    try {
      await fetch(`${API}/api/history/${id}`, { method: 'DELETE' });
      if (viewingSessionId === id) setViewingSessionId(null);
      fetchHistory();
    } catch(e) {}
  };

  const handleExportCSV = () => {
    if (selectedSessionLeads.length === 0) return;
    const header = "Name,Email,Phone,Location,Website,Query";
    const rows = selectedSessionLeads.map(l => 
      [l.name, l.email, l.phone, l.location, l.website, l.query]
      .map(v => `"${(v || '').replace(/"/g, '""')}"`)
      .join(',')
    ).join('\n');
    const blob = new Blob([header + '\n' + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexus_leads_${viewingSessionId}.csv`;
    a.click();
  };

  const handleSendReply = async () => {
    if (!selectedLead || !replyText) return;
    try {
      const res = await fetch(`${API}/api/send-gas`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({
          webhook_url: webhookUrl,
          subject: `Re: ${leadHistory[0]?.subject || 'Partnership Inquiry'}`,
          body: replyText,
          leads: [selectedLead]
        })
      });
      if (res.ok) {
        setReplyText("");
        fetchLeadHistory(selectedLead); // Refresh chat
      }
    } catch(e) {}
  };

  const handleGasCampaign = async () => {
    if (!webhookUrl || !emailSubject || !emailBody) {
      alert("Please fill all GAS Extension fields!");
      return;
    }
    setIsSendingGas(true);
    try {
      const res = await fetch(`${API}/api/send-gas`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({
          webhook_url: webhookUrl,
          subject: emailSubject,
          body: emailBody,
          search_id: viewingSessionId
        })
      });
      const data = await res.json();
      if(res.ok) alert(data.message || "Campaign sent successfully via Native Google Workspace!");
      else alert("Error: " + data.detail);
    } catch(e) {
       alert("Network error talking to backend proxy.");
    }
    setIsSendingGas(false);
  };

  const handleGenerate = async () => {
    if (!intent) return;
    setIsGenerating(true);
    setGeneratedQueries([]);
    try {
      const res = await fetch(`${API}/api/generate-queries`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({ intent, count: queryCount })
      });
      const data = await res.json();
      if(data && data.queries) {
        setGeneratedQueries(data.queries.map((q: any) => ({ ...q, selected: true })));
      }
    } catch(e) {}
    setIsGeneratingCampaign(false);
  }

  const generateCampaign = async () => {
    setIsGeneratingCampaign(true);
    // Detect city from current intent/search
    const detectedCity = intent.toLowerCase().includes("amsterdam") ? "Amsterdam" : 
                         intent.toLowerCase().includes("enschede") ? "Enschede" : "";
    
    try {
      const res = await fetch(`${API}/api/generate-campaign`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({ 
          search_id: viewingSessionId,
          intent, 
          meeting_link: meetingLink || "https://calendly.com/nederland-homemademeals/events", 
          is_referral: isReferral,
          city: detectedCity
        })
      });
      const data = await res.json();
      if(res.ok) {
        setCampaignTemplate(data);
        setEmailSubject(data.subject);
        setEmailBody(data.html_body);
        setShowCampaignPreview(true);
        // Update primary GAS deployment (always use primary URL — new deployments require manual re-auth)
        await redeployGas('update');
        await sendTestEmail(data.subject, data.html_body);
      }
    } catch(e) {
      console.error("Campaign synthesis failed", e);
    }
    setIsGeneratingCampaign(false);
  };

  const redeployGas = async (mode: 'new' | 'update' = 'update') => {
    setLogs(prev => [...prev, `[GAS] ${mode === 'new' ? 'Creating fresh session deployment...' : 'Updating primary deployment...'}`]);
    try {
      const res = await fetch(`${API}/api/redeploy-gas`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({ mode })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.webhook_url) setWebhookUrl(data.webhook_url);
        setLogs(prev => [...prev, `✓ [GAS] ${mode === 'new' ? 'New session URL: ' + data.webhook_url : 'Primary deployment updated. URL unchanged.'}`]);
      } else {
        setLogs(prev => [...prev, `⚠ [GAS] Deploy error: ${data.detail}`]);
      }
    } catch(e: any) {
      setLogs(prev => [...prev, `⚠ [GAS] Deploy failed: ${e?.message}`]);
    }
  };

  const sendTestEmail = async (subject: string, body: string) => {
    try {
       const res = await fetch(`${API}/api/send-gas`, {
         method: "POST",
         headers: {"Content-type": "application/json"},
         body: JSON.stringify({
           webhook_url: webhookUrl,
           subject,
           body,
           leads: [{ email: "bangalexf@gmail.com", name: "Alex (Test Recipient)" }]
         })
       });
       const data = await res.json();
       if (res.ok) {
         setLogs(prev => [...prev, `✓ [AUTO-TEST] Sample dispatched to bangalexf@gmail.com: ${JSON.stringify(data)}`]);
       } else {
         setLogs(prev => [...prev, `⚠ [AUTO-TEST] GAS Error: ${data.detail || JSON.stringify(data)}`]);
       }
    } catch(e: any) {
      setLogs(prev => [...prev, `⚠ [AUTO-TEST] Network error: ${e?.message}`]);
    }
  }

  const fetchCampaign = async (id: string) => {
    setIsGeneratingCampaign(true);
    try {
      const res = await fetch(`${API}/api/history/${id}/campaign`);
      if (res.ok) {
        const data = await res.json();
        setCampaignTemplate(data);
        setEmailSubject(data.subject);
        setEmailBody(data.html_body);
        setShowCampaignPreview(true);
      }
    } catch (e) {
      console.error("Failed to fetch campaign draft:", e);
    } finally {
      setIsGeneratingCampaign(false);
    }
  };

  const toggleQuery = (index: number) => {
    setGeneratedQueries(curr => curr.map((q, i) => i === index ? { ...q, selected: !q.selected } : q));
  }

  const handleLaunch = async () => {
    const selected = generatedQueries.filter(q => q.selected).map(q => ({ label: q.label, query: q.query }));
    if (selected.length === 0) return;
    setIsRunning(true);
    setLogs(["[SYSTEM] Initializing background mass scraper...", "[SYSTEM] Passing intent to Python engine..."]);
    setActiveTab('live');

    try {
      const res = await fetch(`${API}/api/launch`, {
        method: "POST",
        headers: {"Content-type": "application/json"},
        body: JSON.stringify({
          intent,
          queries: selected,
          duration: 60,
          platforms: ["google-maps", "google-search"],
          deep_discovery: true
        })
      });
      const data = await res.json();
      if (data.task_id) setTaskId(data.task_id);
    } catch (e) {
      console.error(e);
      setIsRunning(false);
    }
  }

  const stopRun = async () => {
    if (!taskId) { setIsRunning(false); return; }
    try {
      await fetch(`${API}/api/cancel/${taskId}`, { method: "POST" });
      setIsRunning(false);
      setLogs(prev => [...prev, "[SYSTEM] Shutdown signal sent."]);
    } catch(e) {}
    // Trigger campaign synthesis on manual stop too
    generateCampaign();
  };

  // Autonomous Lifecycle Handshake (handled via SSE now)

  const handleFetchAutomatedCampaign = async () => {
    if (!taskId) return;
    try {
      const res = await fetch(`${API}/api/campaign/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        setCampaignTemplate(data);
        setEmailSubject(data.subject);
        setEmailBody(data.html_body);
        setShowCampaignPreview(true);
        // Trigger test email for the new autonomous draft
        await sendTestEmail(data.subject, data.html_body);
      }
    } catch(e) {}
  };

  return (
    <div className="app-container">
      <div className="glass-panel" style={{ alignSelf: 'start', position: 'sticky', top: '3rem' }}>
        <h1 style={{ marginTop: '0.5rem' }}>NexusScrape</h1>
        <p>Automated mass lead intelligence</p>
        
        <div className="tabs" style={{ marginTop: '2rem' }}>
          <button className={`tab ${activeTab === 'run' ? 'active' : ''}`} onClick={() => setActiveTab('run')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
            Discover
          </button>
          <button className={`tab ${activeTab === 'live' ? 'active' : ''}`} onClick={() => setActiveTab('live')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
            Terminal
          </button>
          <button className={`tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/><path d="M12 2v2"/><path d="M12 18v2"/></svg>
            Library
          </button>
        </div>
        
        {isRunning && (
          <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(50, 215, 75, 0.05)', borderRadius: 'var(--radius-lg)', border: '0.5px solid var(--success)' }}>
            <p className="pulse" style={{ color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '10px', height: '10px', background: 'var(--success)', borderRadius: '50%', display: 'inline-block' }}></span>
              Scraper Active
            </p>
            <button className="btn btn-secondary" onClick={stopRun} style={{ color: 'var(--danger)', marginTop: '0.5rem' }}>Stop Execution</button>
          </div>
        )}
      </div>

      <div className="glass-panel" style={{ minHeight: '85vh' }}>
        {activeTab === 'run' && (
          <div>
            <h2>Target Audience Intent</h2>
            <p>Powered by Google Gemini. Specify industries and precise geolocation.</p>
            <textarea 
              value={intent}
              onChange={e => setIntent(e.target.value)}
              placeholder="e.g. 'I want to find IT agencies and app developers specifically located in Amsterdam and Utrecht'"
            />
            
            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-end', marginBottom: '1.5rem' }}>
              <div style={{ flex: 1 }}>
                <label>Number of Queries</label>
                <select value={queryCount} onChange={e => setQueryCount(Number(e.target.value))} style={{ marginBottom: 0 }}>
                  <option value={1}>1 Single Test Query</option>
                  <option value={10}>10 Highly Specific</option>
                  <option value={20}>20 Broad Variants</option>
                  <option value={50}>50 Massive Coverage</option>
                </select>
              </div>
              <button 
                className="btn btn-primary" 
                style={{ flex: 1, marginBottom: 0 }}
                onClick={handleGenerate} 
                disabled={isGenerating || !intent}
              >
                {isGenerating ? <span className="pulse">Synthesizing...</span> : "Analyze Intent (Gemini)"}
              </button>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '1.5rem', borderRadius: 'var(--radius-lg)', border: '0.5px solid var(--glass-border)', marginBottom: '1.5rem' }}>
               <h3 style={{ marginBottom: '1rem' }}>Campaign Outreach Prep</h3>
               <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                  <label className="query-item" style={{ flex: 1, margin: 0, cursor: 'pointer' }}>
                    <input type="checkbox" checked={isReferral} onChange={e => setIsReferral(e.target.checked)} />
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 600 }}>Referral Scheme</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Include coupons/revenue sharing in drafts</span>
                    </div>
                  </label>
               </div>
               <label>Meeting / Calendly Link</label>
               <input type="text" placeholder="https://calendly.com/homemade-bv" value={meetingLink} onChange={e => setMeetingLink(e.target.value)} style={{ marginBottom: 0 }} />
            </div>

            {generatedQueries.length > 0 && (
              <div style={{ marginTop: '3rem', paddingTop: '2rem', borderTop: '0.5px solid var(--glass-border)' }}>
                <h2>Approve Setup ({generatedQueries.filter(q => q.selected).length} variants)</h2>
                <div className="query-list">
                  {generatedQueries.map((q, idx) => (
                    <label key={idx} className={`query-item ${!q.selected ? 'unselected' : ''}`} style={{ margin: 0 }}>
                      <input type="checkbox" checked={q.selected} onChange={() => toggleQuery(idx)} />
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontWeight: 600, color: '#fff' }}>{q.label}</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>{q.query}</span>
                      </div>
                    </label>
                  ))}
                </div>
                <button className="btn btn-success" onClick={handleLaunch} style={{ marginTop: '1rem', padding: '1rem' }}>
                  Launch Background Scraper
                </button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'live' && (
          <div>
            <h2>Terminal Stream</h2>
            <p>Real-time execution stdout stream. Leads are continuously saved to SQLite.</p>
            <div className="terminal">
              {logs.length === 0 ? <div>Awaiting launch sequence...</div> : logs.map((l, i) => (
                <div key={i} style={{ color: l.includes('✓') || l.includes('✅') ? 'var(--success)' : (l.includes('⚠') || l.includes('Error') ? 'var(--danger)' : 'inherit') }}>
                  {l}
                </div>
              ))}
              <div ref={logEndRef} />
            </div>

            {isGeneratingCampaign && (
              <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(10, 132, 255, 0.05)', borderRadius: 'var(--radius-lg)', border: '0.5px solid var(--primary)' }}>
                <p className="pulse" style={{ color: 'var(--primary)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                   Synthesizing Branded Campaign...
                </p>
              </div>
            )}

            {showCampaignPreview && campaignTemplate && (
              <div style={{ marginTop: '3rem', padding: '2rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <h2 style={{ margin: 0 }}>Campaign Synthesis (Alex Approval)</h2>
                  <span style={{ fontSize: '0.8rem', background: 'rgba(50, 215, 75, 0.2)', color: 'var(--success)', padding: '4px 12px', borderRadius: '12px', fontWeight: 600 }}>Sample Sent to bangalexf@gmail.com</span>
                </div>
                
                <label>Subject</label>
                <input type="text" value={emailSubject} onChange={e => setEmailSubject(e.target.value)} />
                
                <label>Branded Live Preview (HTML)</label>
                <iframe
                  sandbox="allow-same-origin"
                  srcDoc={`<!DOCTYPE html><html><head><style>body{font-family:sans-serif;line-height:1.6;color:#111;padding:1.5rem;margin:0;background:#fff;}p{margin:0 0 1rem;}</style></head><body>${emailBody}</body></html>`}
                  style={{
                    width: '100%',
                    height: '380px',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    marginBottom: '1.5rem',
                    background: '#fff',
                    display: 'block'
                  }}
                />

                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                   <button className="btn btn-primary" onClick={() => setActiveTab('history')}>
                      Review Leads & Send Mass Campaign
                   </button>
                   <button className="btn btn-secondary" onClick={() => generateCampaign()}>
                      Regenerate Variant
                   </button>
                   <button
                     className="btn"
                     style={{ background: 'rgba(255,149,0,0.15)', color: '#FF9500', border: '0.5px solid #FF9500' }}
                     onClick={() => redeployGas('update')}
                   >
                      Redeploy GAS (Update Primary)
                   </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            {!viewingSessionId ? (
              <>
                <h2>Search Library</h2>
                <p>Browse previously archived sessions and accumulated leads.</p>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr><th>Audience Intent</th><th>Status</th><th>Timestamp</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {sessions.map(s => (
                        <tr key={s.id}>
                          <td style={{ maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {s.intent}
                          </td>
                          <td>
                            <span style={{ padding: '4px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600, background: s.status === 'completed' ? 'rgba(50, 215, 75, 0.1)' : 'rgba(255, 69, 58, 0.1)', color: s.status === 'completed' ? 'var(--success)' : 'var(--danger)' }}>
                              {(s.status || 'unknown').toUpperCase()}
                            </span>
                          </td>
                          <td style={{ color: 'var(--text-muted)' }}>{s.created_at ? new Date(s.created_at).toLocaleString() : 'N/A'}</td>
                          <td style={{ display: 'flex', gap: '0.5rem' }}>
                            <button className="btn btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem', width: 'auto' }} onClick={() => viewSession(s.id)}>View</button>
                            <button className="btn btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem', width: 'auto', color: 'var(--danger)' }} onClick={() => deleteSession(s.id)}>Delete</button>
                          </td>
                        </tr>
                      ))}
                      {connectionError && (
                        <tr>
                          <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>
                            <p style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{connectionError}</p>
                            <button className="btn btn-primary" style={{ width: 'auto' }} onClick={trustBackend}>
                              Authenticate & Trust Backend
                            </button>
                          </td>
                        </tr>
                      )}
                      {sessions.length === 0 && !connectionError && <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>No historical runs found.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <button className="btn btn-secondary" style={{ width: 'auto', marginBottom: 0, padding: '0.6rem 1.2rem', gap: '8px' }} onClick={() => setViewingSessionId(null)}>
                    <span style={{ fontSize: '1.2rem' }}>‹</span> Back
                  </button>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn btn-secondary" style={{ width: 'auto', marginBottom: 0 }} onClick={() => viewingSessionId && viewSession(viewingSessionId)}>
                      🔄 Refresh Leads
                    </button>
                    <button className="btn btn-success" style={{ width: 'auto', marginBottom: 0 }} onClick={handleExportCSV}>Export CSV</button>
                  </div>
                </div>
                
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '0.5px solid var(--glass-border)', padding: '1.5rem', borderRadius: 'var(--radius-lg)', marginBottom: '2rem' }}>
                  <h3 style={{ margin: 0, color: 'var(--primary)', marginBottom: '0.5rem' }}>Workspace Automations</h3>
                  <p style={{ fontSize: '0.85rem' }}>Dispatch Native Google Campaigns sequentially mapped from this specific pool of leads.</p>
                  
                  <label style={{ marginTop: '1.5rem' }}>Google Webhook Endpoint</label>
                  <input type="text" placeholder="https://script.google.com/macros/s/.../exec" value={webhookUrl} onChange={e=>setWebhookUrl(e.target.value)} />
                  
                  <label>Subject Payload</label>
                  <input type="text" placeholder="Custom Software Partnership" value={emailSubject} onChange={e=>setEmailSubject(e.target.value)} />
                  
                  <label>Email Body (HTML Supported, Use {'{{name}}'})</label>
                  <textarea placeholder="Hi {{name}}, I noticed your company was..." value={emailBody} onChange={e=>setEmailBody(e.target.value)} />
                  
                  <button className="btn btn-primary" onClick={handleGasCampaign} disabled={isSendingGas}>
                     {isSendingGas ? "Dispatching via Google Cloud..." : `Send Action to ${selectedSessionLeads.length} Leads`}
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h3>Lead Target Array</h3>
                    {isSyncing && <span className="pulse" style={{ color: 'var(--primary)', fontSize: '0.8rem' }}>Syncing Responses...</span>}
                  </div>
                  <span style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '4px 12px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 600 }}>{selectedSessionLeads.length} total</span>
                </div>

                <div className="table-container">
                  <table>
                    <thead><tr><th>Status</th><th>Name</th><th>Email</th><th>Last Active</th><th>Source</th><th>History</th></tr></thead>
                    <tbody>
                      {selectedSessionLeads.map(lead => {
                         const hasResponse = !!(lead.last_interaction && !leadHistory.some(m => m.lead_id === lead.id && m.direction === 'sent' && (m.created_at > (lead.last_interaction || ''))));
                         
                         return (
                          <tr key={lead.id} className={lead.is_opened ? 'opened-row' : ''} style={hasResponse ? { borderLeft: '4px solid var(--success)', background: 'rgba(50, 215, 75, 0.03)' } : {}}>
                            <td>
                              {lead.is_opened ? 
                                <span className="badge-success">OPENED</span> : 
                                <span className="badge-muted">SENT</span>
                              }
                            </td>
                            <td style={{ fontWeight: 500 }}>{lead.name}</td>
                            <td style={{ fontWeight: 600, color: 'var(--success)' }}>{lead.email}</td>
                            <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {lead.last_interaction ? new Date(lead.last_interaction).toLocaleDateString() : '—'}
                            </td>
                            <td><a href={lead.website} target="_blank" rel="noreferrer">{lead.website.substring(0, 20)}...</a></td>
                            <td>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: '4px 10px', fontSize: '0.75rem', width: 'auto' }}
                                onClick={() => fetchLeadHistory(lead)}
                              >
                                {lead.last_interaction ? "💬 Chat" : "Timeline"}
                              </button>
                            </td>
                          </tr>
                         );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Lead Interaction Sidebar/Modal */}
                {selectedLead && (
                  <div className="modal-overlay" onClick={() => setSelectedLead(null)}>
                    <div className="modal-content glass-panel" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px', height: '80vh', display: 'flex', flexDirection: 'column' }}>
                       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                          <h2 style={{ margin: 0 }}>Conversation: {selectedLead.name}</h2>
                          <button onClick={() => setSelectedLead(null)} style={{ background: 'none', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer' }}>×</button>
                       </div>
                       
                       <div style={{ flex: 1, overflowY: 'auto', marginBottom: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', padding: '0.5rem' }}>
                          {leadHistory.map(m => (
                            <div key={m.id} style={{ 
                                alignSelf: m.direction === 'sent' ? 'flex-end' : 'flex-start',
                                maxWidth: '80%',
                                padding: '1rem',
                                borderRadius: '12px',
                                background: m.direction === 'sent' ? 'rgba(10, 132, 255, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                                border: m.direction === 'sent' ? '0.5px solid var(--primary)' : '0.5px solid var(--glass-border)'
                            }}>
                               <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                                  <span>{m.direction.toUpperCase()}</span>
                                  <span>{new Date(m.created_at).toLocaleString()}</span>
                               </div>
                               <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '4px' }}>{m.subject}</div>
                               <div style={{ fontSize: '0.85rem' }} dangerouslySetInnerHTML={{ __html: m.body }}></div>
                            </div>
                          ))}
                          {leadHistory.length === 0 && <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '20%' }}>No message history yet.</div>}
                       </div>

                       <div style={{ borderTop: '0.5px solid var(--glass-border)', paddingTop: '1.5rem' }}>
                          <textarea 
                            placeholder="Type a quick reply..." 
                            value={replyText} 
                            onChange={e => setReplyText(e.target.value)}
                            style={{ minHeight: '100px' }}
                          />
                          <button className="btn btn-primary" disabled={!replyText} onClick={handleSendReply}>
                             Send Reply via Google Workspace
                          </button>
                       </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
