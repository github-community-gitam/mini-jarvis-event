import React, { useState, useEffect, useEffectEvent, useRef } from 'react';
import { MessageSquare, Plus, Mic, Send, CircleDot, Trash2, X, Activity, AudioLines, Settings, Check, XCircle } from 'lucide-react';
import { api, API_URL, requestError, recordingFormat, audioFilename } from './api';
import './App.css';

function App() {
  const [signedIn, setSignedIn] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [authLoading, setAuthLoading] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [continuousMode, setContinuousMode] = useState(false);
  const [showIntegrations, setShowIntegrations] = useState(false);
  const [integrationsStatus, setIntegrationsStatus] = useState({ google: false, github: false });
  const [integrationState, setIntegrationState] = useState('loading');
  const [historyState, setHistoryState] = useState('loading');
  const [messageState, setMessageState] = useState('ready');
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState('');
  const [pendingToolCall, setPendingToolCall] = useState(null);
  const [audioState, setAudioState] = useState('IDLE');
  const [audioLevels, setAudioLevels] = useState(new Array(30).fill(0.1));
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);
  const micSourceNodeRef = useRef(null);
  const ttsSourceNodeRef = useRef(null);
  const audioElRef = useRef(null);
  const streamRef = useRef(null);
  const busyRef = useRef(false);
  const recordingRef = useRef(false);
  const generation = useRef(0);
  const selected = useRef(null);
  const historyRequest = useRef(0);
  const audioGeneration = useRef(0);
  const mounted = useRef(true);
  const voiceSupported = !!((window.AudioContext || window.webkitAudioContext) && window.MediaRecorder && navigator.mediaDevices?.getUserMedia);

  const reportError = error => {
    setError(requestError(error));
    if (error.response?.status === 401) { setSignedIn(false); stopAudio(); }
  };
  const stopVisualizer = () => {
    if (animationFrameRef.current !== null) cancelAnimationFrame(animationFrameRef.current);
    animationFrameRef.current = null;
    if (mounted.current) setAudioLevels(new Array(30).fill(0.1));
  };
  const stopAudio = () => {
    audioGeneration.current++;
    recordingRef.current = false;
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      recorder.onstop = null;
      if (recorder.state !== 'inactive') recorder.stop();
    }
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    micSourceNodeRef.current?.disconnect();
    micSourceNodeRef.current = null;
    audioElRef.current?.pause();
    stopVisualizer();
    if (mounted.current) setAudioState('IDLE');
  };

  const signIn = async event => {
    event.preventDefault(); setAuthLoading(true); setError('');
    try { await api.post('/session/login', { access_code: accessCode }); setAccessCode(''); setSignedIn(true); fetchConversations(); checkIntegrations(); }
    catch (err) { reportError(err); }
    finally { setAuthLoading(false); }
  };
  const signOut = async () => {
    try {
      await api.post('/session/logout'); stopAudio(); generation.current++; historyRequest.current++; selected.current = null;
      setSignedIn(false); setMessages([]); setConversations([]); setPendingToolCall(null); setActiveConvId(null);
    } catch (err) { reportError(err); }
  };
  const fetchConversations = async (more = false) => {
    const request = ++historyRequest.current;
    setHistoryState('loading');
    try {
      const res = await api.get('/conversations', { params: { limit: 50, offset: more ? conversations.length : 0 } });
      if (!mounted.current || request !== historyRequest.current) return;
      setConversations(prev => more ? [...prev, ...res.data.filter(row => !prev.some(old => old.id === row.id))] : res.data);
      setHasMore(res.data.length === 50); setHistoryState('ready');
    } catch (err) { if (request === historyRequest.current) { setHistoryState('error'); reportError(err); } }
  };
  const fetchMessages = async (id, version = generation.current) => {
    setMessageState('loading');
    try {
      const res = await api.get(`/conversations/${id}`);
      if (mounted.current && version === generation.current && selected.current === id) {
        setMessages(res.data.messages || []); setMessageState('ready');
      }
    } catch (err) { if (version === generation.current) { setMessageState('error'); reportError(err); } }
  };
  const selectConversation = id => {
    generation.current++; selected.current = id; stopAudio();
    setActiveConvId(id); setMessages([]); setPendingToolCall(null); setError('');
    setMessageState('ready');
    if (id) fetchMessages(id);
  };
  const checkIntegrations = async () => {
    setIntegrationState('loading'); setIntegrationsStatus({ google: false, github: false });
    try {
      const [google, github] = await Promise.all([api.get('/auth/google/status'), api.get('/auth/github/status')]);
      if (!mounted.current) return;
      setIntegrationsStatus({ google: google.data.connected, github: github.data.connected }); setIntegrationState('ready');
    } catch (err) { setIntegrationState('error'); reportError(err); }
  };
  const handleConnectCalendar = () => { window.location.href = `${API_URL}/auth/google/login`; };
  const handleConnectGithub = () => { window.location.href = `${API_URL}/auth/github/login`; };
  const disconnect = async provider => {
    try { await api.delete(`/auth/${provider}/disconnect`); await checkIntegrations(); }
    catch (err) { setIntegrationsStatus({ google: false, github: false }); setIntegrationState('error'); reportError(err); }
  };
  const handleDisconnectCalendar = () => disconnect('google');
  const handleDisconnectGithub = () => disconnect('github');
  const handleNewChat = () => selectConversation(null);
  const handleDelete = async (id, event) => {
    event.stopPropagation();
    try { await api.delete(`/conversations/${id}`); if (selected.current === id) selectConversation(null); fetchConversations(); }
    catch (err) { reportError(err); }
  };
  const initAudioContext = () => {
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) return false;
    if (!audioContextRef.current) {
      audioContextRef.current = new Context();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
    }
    return true;
  };
  const updateVisualizer = () => {
    if (!analyserRef.current || !mounted.current) return;
    const data = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(data);
    setAudioLevels(Array.from({ length: 30 }, (_, i) => Math.max(0.1, data[Math.floor(i * data.length / 30)] / 255)));
    animationFrameRef.current = requestAnimationFrame(updateVisualizer);
  };
  const startListening = async () => {
    if (!voiceSupported) { setError('Voice is unavailable in this browser. You can still use text chat.'); setContinuousMode(false); return; }
    if (busyRef.current || recordingRef.current || audioState !== 'IDLE' || pendingToolCall) return;
    recordingRef.current = true;
    const version = generation.current, audioVersion = audioGeneration.current;
    try {
      initAudioContext(); await audioContextRef.current.resume();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      if (!mounted.current || version !== generation.current || audioVersion !== audioGeneration.current) { stream.getTracks().forEach(t => t.stop()); return; }
      streamRef.current = stream;
      micSourceNodeRef.current = audioContextRef.current.createMediaStreamSource(stream);
      micSourceNodeRef.current.connect(analyserRef.current);
      const recorder = new MediaRecorder(stream, recordingFormat());
      mediaRecorderRef.current = recorder;
      const chunks = [];
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onerror = () => { stopAudio(); setContinuousMode(false); setError('Recording failed. Please try again.'); };
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop()); streamRef.current = null;
        micSourceNodeRef.current?.disconnect(); micSourceNodeRef.current = null;
        stopVisualizer(); recordingRef.current = false;
        if (version !== generation.current || audioVersion !== audioGeneration.current) return;
        const mime = recorder.mimeType || chunks[0]?.type;
        if (!mime) { setError('The browser did not provide a supported audio format.'); setAudioState('IDLE'); return; }
        const blob = new Blob(chunks, { type: mime });
        if (!blob.size) { setAudioState('IDLE'); return; }
        busyRef.current = true; setAudioState('PROCESSING');
        const form = new FormData(); form.append('file', blob, audioFilename(mime));
        try {
          const res = await api.post('/jarvis/transcribe', form, { timeout: 45000 });
          if (version !== generation.current || audioVersion !== audioGeneration.current) return;
          busyRef.current = false;
          if (res.data.text) await sendMessage(res.data.text);
        } catch (err) { if (version === generation.current) { reportError(err); setContinuousMode(false); } }
        finally { busyRef.current = false; if (version === generation.current) setAudioState(prev => prev === 'PROCESSING' ? 'IDLE' : prev); }
      };
      recorder.start(); setAudioState('LISTENING'); stopVisualizer(); updateVisualizer();
    } catch {
      stopAudio(); setContinuousMode(false); setError('Microphone unavailable. Check browser permissions and try again.');
    }
  };
  const toggleListening = () => {
    if (mediaRecorderRef.current?.state === 'recording') { setAudioState('PROCESSING'); mediaRecorderRef.current.stop(); }
    else if (audioState === 'IDLE') startListening();
  };
  const sendMessage = async (text = input.trim(), toolExecution = null) => {
    if ((!text && !toolExecution) || busyRef.current || recordingRef.current || messageState === 'loading') return;
    busyRef.current = true;
    const version = generation.current, target = selected.current, voiceVersion = audioGeneration.current;
    setError(''); setInput(''); setAudioState('PROCESSING');
    if (text && !toolExecution) setMessages(prev => [...prev, { role: 'user', content: text, id: Date.now() }]);
    try {
      const res = await api.post('/jarvis/chat', { message: text, conversation_id: target, web_mode: true, tool_execution: toolExecution }, { timeout: 90000 });
      if (!mounted.current || version !== generation.current) return;
      const { conversation_id, response, audio, tool_call } = res.data;
      if (!target) { selected.current = conversation_id; setActiveConvId(conversation_id); }
      fetchConversations();
      if (response) setMessages(prev => [...prev, { role: 'assistant', content: response, id: Date.now() + 1 }]);
      setPendingToolCall(tool_call || null);
      if (audio && isVoiceMode && voiceVersion === audioGeneration.current) await playTTS(audio); else setAudioState('IDLE');
    } catch (err) {
      if (version === generation.current) {
        reportError(err); setContinuousMode(false); setInput(text); setAudioState('IDLE');
        // Do not offer a replay of a write whose provider outcome may be uncertain.
        if (toolExecution) setPendingToolCall(null);
      }
    } finally { busyRef.current = false; }
  };
  const handleToolConfirm = approved => {
    if (!pendingToolCall || busyRef.current) return;
    const call = pendingToolCall;
    setPendingToolCall(null);
    sendMessage('', { tool_name: call.tool_name, arguments: call.arguments, action_id: call.action_id, approved });
  };
  const playTTS = async audio => {
    const version = audioGeneration.current;
    try {
      if (!initAudioContext()) return;
      await audioContextRef.current.resume();
      if (version !== audioGeneration.current || !audioElRef.current) return;
      const element = audioElRef.current;
      element.src = `data:audio/mp3;base64,${audio}`;
      if (!ttsSourceNodeRef.current) {
        ttsSourceNodeRef.current = audioContextRef.current.createMediaElementSource(element);
        ttsSourceNodeRef.current.connect(analyserRef.current);
        ttsSourceNodeRef.current.connect(audioContextRef.current.destination);
      }
      element.onended = () => { stopVisualizer(); setAudioState('IDLE'); };
      element.onerror = () => { stopVisualizer(); setAudioState('IDLE'); setContinuousMode(false); setError('Audio playback failed.'); };
      setAudioState('SPEAKING'); await element.play();
      if (version !== audioGeneration.current) return;
      stopVisualizer(); updateVisualizer();
    } catch { stopVisualizer(); setAudioState('IDLE'); setContinuousMode(false); setError('Audio playback unavailable.'); }
  };
  const setVoiceMode = enabled => {
    stopAudio(); ttsSourceNodeRef.current?.disconnect(); ttsSourceNodeRef.current = null;
    setContinuousMode(false); setIsVoiceMode(enabled);
  };
  const handleKeyPress = event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); sendMessage(); }
  };
  const onSessionReady = useEffectEvent(() => { fetchConversations(); checkIntegrations(); });
  const onAutoListen = useEffectEvent(() => startListening());
  const onDispose = useEffectEvent(() => {
    mounted.current = false;
    generation.current++;
    historyRequest.current++;
    stopAudio();
    ttsSourceNodeRef.current?.disconnect();
    ttsSourceNodeRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
  });
  useEffect(() => {
    mounted.current = true;
    api.get('/session').then(() => { if (mounted.current) { setSignedIn(true); onSessionReady(); } }).catch(() => {}).finally(() => { if (mounted.current) setAuthLoading(false); });
    return () => onDispose();
  }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView?.({ behavior: 'smooth' }); }, [messages, audioState, pendingToolCall]);
  useEffect(() => {
    if (isVoiceMode && continuousMode && audioState === 'IDLE' && !pendingToolCall && !busyRef.current) {
      const timer = setTimeout(() => onAutoListen(), 500);
      return () => clearTimeout(timer);
    }
  }, [isVoiceMode, continuousMode, audioState, pendingToolCall]);

  const renderIntegrations = () => (
    <div className="integrations-modal-overlay" onClick={() => setShowIntegrations(false)}>
      <div className="integrations-modal" onClick={e => e.stopPropagation()}>
        <div className="integrations-header">
          <h2>Integrations</h2>
          <button className="close-btn" onClick={() => setShowIntegrations(false)}><X size={24}/></button>
        </div>
        <div className="integrations-list">
          {integrationState === 'loading' && <p role="status">Checking integrations…</p>}
          {integrationState === 'error' && <p role="alert">Unable to check integrations. <button onClick={checkIntegrations}>Retry</button></p>}
          <fieldset disabled={integrationState !== 'ready'}>
          <div className="integration-item">
            <div className="integration-info">
              <h3>Google Calendar</h3>
              <p>Schedule events, read calendar</p>
            </div>
            <div className="integration-action">
              {integrationsStatus.google ? (
                <button className="btn-disconnect" onClick={handleDisconnectCalendar}>Disconnect</button>
              ) : (
                <button className="btn-connect" onClick={handleConnectCalendar}>Connect</button>
              )}
            </div>
          </div>

          <div className="integration-item">
            <div className="integration-info">
              <h3>Gmail</h3>
              <p>Search, read, and summarize emails</p>
            </div>
            <div className="integration-action">
              {integrationsStatus.google ? (
                <button className="btn-disconnect" onClick={handleDisconnectCalendar}>Disconnect</button>
              ) : (
                <button className="btn-connect" onClick={handleConnectCalendar}>Connect</button>
              )}
            </div>
          </div>

          <div className="integration-item">
            <div className="integration-info">
              <h3>Google Drive</h3>
              <p>Search and read documents</p>
            </div>
            <div className="integration-action">
              {integrationsStatus.google ? (
                <button className="btn-disconnect" onClick={handleDisconnectCalendar}>Disconnect</button>
              ) : (
                <button className="btn-connect" onClick={handleConnectCalendar}>Connect</button>
              )}
            </div>
          </div>

          <div className="integration-item">
            <div className="integration-info">
              <h3>GitHub</h3>
              <p>Read issues, repositories</p>
            </div>
            <div className="integration-action">
              {integrationsStatus.github ? (
                <button className="btn-disconnect" onClick={handleDisconnectGithub}>Disconnect</button>
              ) : (
                <button className="btn-connect" onClick={handleConnectGithub}>Connect</button>
              )}
            </div>
          </div>
        </fieldset></div>
      </div>
    </div>
  );

  const renderConfirmationCard = () => {
    if (!pendingToolCall) return null;
    return (
      <div className="confirmation-card">
        <h3>Action Required</h3>
        <p className="confirmation-msg">{pendingToolCall.message}</p>
        <div className="confirmation-details">
            <strong>Tool:</strong> {pendingToolCall.tool_name}
            <pre>{JSON.stringify(pendingToolCall.arguments, null, 2)}</pre>
        </div>
        <div className="confirmation-actions">
            <button className="btn-confirm" onClick={() => handleToolConfirm(true)}>
                <Check size={16} /> Confirm
            </button>
            <button className="btn-cancel" onClick={() => handleToolConfirm(false)}>
                <XCircle size={16} /> Cancel
            </button>
        </div>
      </div>
    );
  };

  if (!signedIn) return <main className="login-screen"><form onSubmit={signIn}>
    <h1>JARVIS</h1><p>Sign in with your personal access code.</p>
    <label htmlFor="access-code">Access code</label>
    <input id="access-code" type="password" autoComplete="current-password" value={accessCode} onChange={event => setAccessCode(event.target.value)} required />
    <button disabled={authLoading}>{authLoading ? 'Checking…' : 'Sign in'}</button>
    {error && <p role="alert">{error}</p>}
  </form></main>;

  if (isVoiceMode) {
    return (
      <div className="voice-mode-container">
        <button className="exit-voice-btn" onClick={() => setVoiceMode(false)}>
          <X size={24} />
        </button>

        {error && <p role="alert">{error}</p>}
        <div className="voice-header">
          <div className="voice-brand">JARVIS</div>
        </div>

        <div className="visualizer-section">
          <div className="bars-container">
            {audioLevels.map((level, i) => {
              return (
                <div
                  key={i}
                  className="vis-bar"
                  style={{ transform: `scaleY(${level * 2.5})` }}
                />
              )
            })}
          </div>

          <div className="voice-status">
            {audioState === 'IDLE' && "IDLE"}
            {audioState === 'LISTENING' && "LISTENING..."}
            {audioState === 'PROCESSING' && "THINKING..."}
            {audioState === 'SPEAKING' && "SPEAKING"}
          </div>
        </div>

        {pendingToolCall && (
            <div className="voice-confirmation-wrapper">
                {renderConfirmationCard()}
            </div>
        )}

        <div className="voice-controls">
          <div className="continuous-toggle">
            <input
              type="checkbox"
              id="continuous"
              checked={continuousMode}
              onChange={e => setContinuousMode(e.target.checked)}
            />
            <label htmlFor="continuous">Continuous Conversation</label>
          </div>

          <button
            className={`voice-main-btn ${audioState}`}
            onClick={toggleListening}
            disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null || messageState === 'loading'}
          >
            {audioState === 'LISTENING' ? <Activity size={32}/> : <Mic size={32}/>}
          </button>
        </div>

        <audio ref={audioElRef} style={{ display: 'none' }} />
      </div>
    );
  }

  // CHAT MODE
  return (
    <div className="app-container">
      {showIntegrations && renderIntegrations()}

      <header className="topbar">
        <div className="brand">J A R V I S</div><button onClick={signOut}>Sign out</button>
        <div className="top-controls">
          <button className="settings-btn" onClick={() => setShowIntegrations(true)}>
            <Settings size={16} /> Integrations
          </button>
          <button className="enter-voice-btn" onClick={() => setVoiceMode(true)} disabled={!voiceSupported}>
            <Mic size={16} /> Voice Chat
          </button>
          <div className="status">
            <CircleDot size={14} color="#00e676" />
            <span>ONLINE</span>
          </div>
        </div>
      </header>

      {error && <p className="notice" role="alert">{error}</p>}
      {!voiceSupported && <p className="notice">Voice is unavailable in this browser. Text chat is available.</p>}
      <div className="main-layout">
        <aside className="sidebar">
          <div className="sidebar-header">Conversations</div>
          <button className="new-chat-btn" onClick={handleNewChat}>
            <Plus size={16} /> New Chat
          </button>

          <div className="conv-list">
            {historyState === 'loading' && <p role="status">Loading conversations…</p>}
            {historyState === 'error' && <p role="alert">Unable to load history. <button onClick={() => fetchConversations()}>Retry</button></p>}
            {historyState === 'ready' && !conversations.length && <p>No conversations yet.</p>}
            {conversations.map(conv => (
              <div
                key={conv.id}
                className={`conv-item ${activeConvId === conv.id ? 'active' : ''}`}
                onClick={() => selectConversation(conv.id)}
              >
                <MessageSquare size={16} className="conv-icon" />
                <span className="conv-title">{conv.title}</span>
                <button aria-label="Delete conversation" className="delete-btn" onClick={(e) => handleDelete(conv.id, e)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {hasMore && <button disabled={historyState === "loading"} onClick={() => fetchConversations(true)}>Load more</button>}
          </div>
        </aside>

        <main className="chat-area">
          {messageState === 'loading' && <p role="status">Loading messages…</p>}
          {messageState === 'error' && <p role="alert">Unable to load messages. <button onClick={() => fetchMessages(activeConvId)}>Retry</button></p>}
          {messages.length === 0 && audioState === 'IDLE' ? (
            <div className="empty-state">
              <h1 className="empty-brand">J A R V I S</h1>
              <p>"How can I assist you today, sir?"</p>
            </div>
          ) : (
            <div className="messages-container">
              {messages.map((msg, i) => (
                <div key={msg.id || i} className={`message-row ${msg.role}`}>
                  <div className="message-bubble">
                    <div className="message-role">{msg.role === 'user' ? 'USER' : 'JARVIS'}</div>
                    <div className="message-content">{msg.content}</div>
                  </div>
                </div>
              ))}
              {audioState === 'PROCESSING' && (
                <div className="message-row assistant">
                  <div className="message-bubble">
                    <div className="message-role">JARVIS</div>
                    <div className="message-content typing-indicator bars">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                </div>
              )}
              {renderConfirmationCard()}
              <div ref={messagesEndRef} />
            </div>
          )}

          <div className="input-area">
            <div className="input-status-hint">
              {audioState === 'IDLE' && !pendingToolCall && "● IDLE"}
              {audioState === 'LISTENING' && "● LISTENING..."}
              {audioState === 'PROCESSING' && "● THINKING"}
              {audioState === 'SPEAKING' && "● SPEAKING"}
              {pendingToolCall && "● AWAITING CONFIRMATION"}
            </div>
            <div className="input-box">
              <button
                className={`mic-btn ${audioState === 'LISTENING' ? 'recording' : ''}`}
                onClick={toggleListening}
                disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null || messageState === 'loading'}
              >
                <Mic size={20} color={audioState === 'LISTENING' ? "#ff4444" : "var(--text-muted)"} />
              </button>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask JARVIS..."
                rows={1}
                disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null || messageState === 'loading'}
              />
              <button
                aria-label="Send message" className="send-btn"
                onClick={() => sendMessage()}
                disabled={!input.trim() || audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null}
              >
                <Send size={20} />
              </button>
              <button
                className="chatgpt-voice-btn"
                onClick={() => setVoiceMode(true)} disabled={!voiceSupported}
                title="Voice Chat"
              >
                <AudioLines size={18} color={pendingToolCall !== null ? "gray" : "#ffffff"} />
              </button>
            </div>
          </div>
        </main>
      </div>
      <audio ref={audioElRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;
