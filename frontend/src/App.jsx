import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { MessageSquare, Plus, Mic, Send, CircleDot, Trash2, X, Activity, AudioLines, Settings, Check, XCircle } from 'lucide-react';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function App() {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  
  // App Mode
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [continuousMode, setContinuousMode] = useState(false);
  const [showIntegrations, setShowIntegrations] = useState(false);
  const [integrationsStatus, setIntegrationsStatus] = useState({ google: false, github: false });
  const [pendingToolCall, setPendingToolCall] = useState(null);
  
  // Audio State
  // 'IDLE', 'LISTENING', 'PROCESSING', 'SPEAKING'
  const [audioState, setAudioState] = useState('IDLE');
  
  const messagesEndRef = useRef(null);
  
  // Refs for Web Audio API & MediaRecorder
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);
  const micSourceNodeRef = useRef(null);
  const ttsSourceNodeRef = useRef(null);
  const audioElRef = useRef(null);
  
  // Visualizer data
  const [audioLevels, setAudioLevels] = useState(new Array(30).fill(0.1));

  useEffect(() => {
    fetchConversations();
    checkIntegrations();
    initAudioContext();
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, []);

  useEffect(() => {
    if (activeConvId) {
      fetchMessages(activeConvId);
    } else {
      setMessages([]);
    }
  }, [activeConvId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, audioState, pendingToolCall]);
  
  // Continuous mode auto-listen trigger
  useEffect(() => {
    if (isVoiceMode && continuousMode && audioState === 'IDLE' && !pendingToolCall) {
      // Small delay before automatically listening again
      const timer = setTimeout(() => {
        if (audioState === 'IDLE' && !pendingToolCall) startListening();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [isVoiceMode, continuousMode, audioState, pendingToolCall]);

  const initAudioContext = () => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      analyserRef.current.smoothingTimeConstant = 0.8;
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await axios.get(`${API_URL}/conversations`);
      setConversations(res.data);
    } catch (e) {
      console.error("Failed to fetch conversations", e);
    }
  };

  const fetchMessages = async (id) => {
    try {
      const res = await axios.get(`${API_URL}/conversations/${id}`);
      setMessages(res.data.messages || []);
    } catch (e) {
      console.error("Failed to fetch messages", e);
    }
  };

  const checkIntegrations = async () => {
    try {
      const resGcal = await axios.get(`${API_URL}/auth/google/status`);
      const resGithub = await axios.get(`${API_URL}/auth/github/status`);
      setIntegrationsStatus({ 
        google: resGcal.data.connected,
        github: resGithub.data.connected
      });
    } catch (e) {
      console.error("Failed to fetch integration status", e);
    }
  };


  const handleConnectCalendar = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  const handleDisconnectCalendar = async () => {
    try {
      await axios.delete(`${API_URL}/auth/google/disconnect`);
      checkIntegrations();
    } catch (e) {
      console.error("Failed to disconnect calendar", e);
    }
  };
  
  const handleConnectGithub = () => {
    window.location.href = `${API_URL}/auth/github/login`;
  };

  const handleDisconnectGithub = async () => {
    try {
      await axios.delete(`${API_URL}/auth/github/disconnect`);
      checkIntegrations();
    } catch (e) {
      console.error("Failed to disconnect github", e);
    }
  };


  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setPendingToolCall(null);
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API_URL}/conversations/${id}`);
      if (activeConvId === id) setActiveConvId(null);
      fetchConversations();
    } catch (e) {
      console.error("Failed to delete", e);
    }
  };

  // -----------------------------------------------------
  // AUDIO VISUALIZER LOOP
  // -----------------------------------------------------
  const updateVisualizer = () => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    // Map frequency data to 30 bars
    const numBars = 30;
    const step = Math.floor(dataArray.length / numBars);
    const newLevels = [];
    
    for (let i = 0; i < numBars; i++) {
      let sum = 0;
      for (let j = 0; j < step; j++) {
        sum += dataArray[i * step + j];
      }
      const avg = sum / step;
      const normalized = Math.max(0.1, avg / 255);
      newLevels.push(normalized);
    }
    
    setAudioLevels(newLevels);
    animationFrameRef.current = requestAnimationFrame(updateVisualizer);
  };

  // -----------------------------------------------------
  // MICROPHONE (STT) LOGIC
  // -----------------------------------------------------
  const startListening = async () => {
    if (audioState === 'SPEAKING' || pendingToolCall) return;
    
    try {
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      if (micSourceNodeRef.current) micSourceNodeRef.current.disconnect();
      micSourceNodeRef.current = audioContextRef.current.createMediaStreamSource(stream);
      micSourceNodeRef.current.connect(analyserRef.current);
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (micSourceNodeRef.current) {
          micSourceNodeRef.current.disconnect();
          micSourceNodeRef.current = null;
        }
        stream.getTracks().forEach(track => track.stop());
        setAudioLevels(new Array(30).fill(0.1));
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        if (audioBlob.size < 1000) {
          setAudioState('IDLE');
          return; 
        }
        
        setAudioState('PROCESSING');
        
        const formData = new FormData();
        formData.append("file", audioBlob, "web_recording.webm");
        
        try {
          const res = await axios.post(`${API_URL}/jarvis/transcribe`, formData);
          if (res.data.text) {
             sendMessage(res.data.text);
          } else {
             setAudioState('IDLE');
          }
        } catch (e) {
          console.error("Transcription error", e);
          setAudioState('IDLE');
        }
      };

      mediaRecorder.start();
      setAudioState('LISTENING');
      
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      updateVisualizer();
      
    } catch (e) {
      console.error("Microphone permission denied or error", e);
      setAudioState('IDLE');
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && audioState === 'LISTENING') {
      mediaRecorderRef.current.stop();
    }
  };

  const toggleListening = () => {
    if (audioState === 'LISTENING') {
      stopListening();
    } else if (audioState === 'IDLE') {
      startListening();
    }
  };

  // -----------------------------------------------------
  // SEND MESSAGE & PLAY TTS
  // -----------------------------------------------------
  const sendMessage = async (text = input.trim(), toolExecution = null) => {
    if (!text && !toolExecution) return;
    setInput('');
    setAudioState('PROCESSING');
    
    if (text && !toolExecution) {
        setMessages(prev => [...prev, { role: 'user', content: text, id: Date.now() }]);
    }

    try {
      const res = await axios.post(`${API_URL}/jarvis/chat`, {
        message: text,
        conversation_id: activeConvId,
        web_mode: true,
        tool_execution: toolExecution
      });
      
      const { conversation_id, response, audio, tool_call } = res.data;
      
      if (!activeConvId && conversation_id) {
        setActiveConvId(conversation_id);
        fetchConversations();
      }
      
      if (response) {
        setMessages(prev => [...prev, { role: 'assistant', content: response, id: Date.now() + 1 }]);
      }
      
      if (tool_call) {
        setPendingToolCall(tool_call);
      } else {
        setPendingToolCall(null);
      }
      
      if (audio) {
        playTTS(audio);
      } else {
        setAudioState('IDLE');
      }
    } catch (e) {
      console.error("Failed to send message", e);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error.', id: Date.now() + 1 }]);
      setAudioState('IDLE');
    }
  };

  const handleToolConfirm = (approved) => {
    if (!pendingToolCall) return;
    const toolExec = {
        tool_name: pendingToolCall.tool_name,
        arguments: pendingToolCall.arguments,
        approved: approved
    };
    
    // Create a system message in the UI so user knows what happened
    setMessages(prev => [...prev, { role: 'user', content: approved ? `[Confirmed: ${pendingToolCall.tool_name}]` : `[Canceled: ${pendingToolCall.tool_name}]`, id: Date.now() }]);
    
    setPendingToolCall(null);
    sendMessage("", toolExec);
  };

  const playTTS = async (base64Audio) => {
    try {
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      
      setAudioState('SPEAKING');
      
      const audioStr = `data:audio/mp3;base64,${base64Audio}`;
      audioElRef.current.src = audioStr;
      
      try {
        if (!ttsSourceNodeRef.current) {
          ttsSourceNodeRef.current = audioContextRef.current.createMediaElementSource(audioElRef.current);
          ttsSourceNodeRef.current.connect(analyserRef.current);
          ttsSourceNodeRef.current.connect(audioContextRef.current.destination);
        }
      } catch (e) {
        console.warn("MediaElementSource already created", e);
      }
      
      audioElRef.current.onended = () => {
        setAudioLevels(new Array(30).fill(0.1));
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
        setAudioState('IDLE');
      };

      await audioElRef.current.play();
      
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      updateVisualizer();

    } catch (e) {
      console.error("Failed to play TTS audio", e);
      setAudioState('IDLE');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // -----------------------------------------------------
  // RENDER UI
  // -----------------------------------------------------
  
  const IntegrationsPanel = () => (
    <div className="integrations-modal-overlay" onClick={() => setShowIntegrations(false)}>
      <div className="integrations-modal" onClick={e => e.stopPropagation()}>
        <div className="integrations-header">
          <h2>Integrations</h2>
          <button className="close-btn" onClick={() => setShowIntegrations(false)}><X size={24}/></button>
        </div>
        <div className="integrations-list">
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
        </div>
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

  if (isVoiceMode) {
    return (
      <div className="voice-mode-container">
        <button className="exit-voice-btn" onClick={() => setIsVoiceMode(false)}>
          <X size={24} />
        </button>
        
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
            disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null}
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
      {showIntegrations && <IntegrationsPanel />}
      
      <header className="topbar">
        <div className="brand">J A R V I S</div>
        <div className="top-controls">
          <button className="settings-btn" onClick={() => setShowIntegrations(true)}>
            <Settings size={16} /> Integrations
          </button>
          <button className="enter-voice-btn" onClick={() => setIsVoiceMode(true)}>
            <Mic size={16} /> Voice Chat
          </button>
          <div className="status">
            <CircleDot size={14} color="#00e676" />
            <span>ONLINE</span>
          </div>
        </div>
      </header>

      <div className="main-layout">
        <aside className="sidebar">
          <div className="sidebar-header">Conversations</div>
          <button className="new-chat-btn" onClick={handleNewChat}>
            <Plus size={16} /> New Chat
          </button>
          
          <div className="conv-list">
            {conversations.map(conv => (
              <div 
                key={conv.id} 
                className={`conv-item ${activeConvId === conv.id ? 'active' : ''}`}
                onClick={() => setActiveConvId(conv.id)}
              >
                <MessageSquare size={16} className="conv-icon" />
                <span className="conv-title">{conv.title}</span>
                <button className="delete-btn" onClick={(e) => handleDelete(conv.id, e)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </aside>

        <main className="chat-area">
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
                disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null}
              >
                <Mic size={20} color={audioState === 'LISTENING' ? "#ff4444" : "var(--text-muted)"} />
              </button>
              <textarea 
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask JARVIS..."
                rows={1}
                disabled={audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null}
              />
              <button 
                className="send-btn" 
                onClick={() => sendMessage()} 
                disabled={!input.trim() || audioState === 'PROCESSING' || audioState === 'SPEAKING' || pendingToolCall !== null}
              >
                <Send size={20} />
              </button>
              <button 
                className="chatgpt-voice-btn"
                onClick={() => setIsVoiceMode(true)}
                title="Voice Chat"
                disabled={pendingToolCall !== null}
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
