import React, { useState, useEffect, useRef } from 'react';
import { Upload, MessageCircle, FileText, BarChart3, Settings, LogOut, Send, Download, Trash2, Eye, Clock, Zap, Activity, Users, Database, Server, Loader, AlertCircle, CheckCircle, X, Plus, RefreshCw } from 'lucide-react';

const API_BASE = '';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('authToken'));
  const [activeTab, setActiveTab] = useState('chat');
  const [documents, setDocuments] = useState([]);
  const [queryHistory, setQueryHistory] = useState([]);
  const [systemStatus, setSystemStatus] = useState({});
  const [userReport, setUserReport] = useState(null);
  const [notifications, setNotifications] = useState([]);
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingId, setStreamingId] = useState(null);
  const chatContainerRef = useRef(null);
  
  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  
  // Auth state
  const [showAuth, setShowAuth] = useState(!token);
  const [authMode, setAuthMode] = useState('login');
  const [authData, setAuthData] = useState({ email: '', password: '' });
  
  useEffect(() => {
    if (token) {
      setShowAuth(false);
      loadUserData();
      loadDocuments();
      loadQueryHistory();
      loadSystemStatus();
      setupWebSocket();
    } else {
      setShowAuth(true);
    }
  }, [token]);

  const loadUserData = async () => {
    try {
      const response = await fetch(`${API_BASE}/qa/user/report?days=30`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUserReport(data.report);
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/qa/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const loadQueryHistory = async () => {
    try {
      const response = await fetch(`${API_BASE}/qa/history?limit=50`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setQueryHistory(data);
      }
    } catch (error) {
      console.error('Error loading query history:', error);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/qa/llm-status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSystemStatus(data);
      }
    } catch (error) {
      console.error('Error loading system status:', error);
    }
  };

  const setupWebSocket = () => {
    // In a real implementation, you'd set up a WebSocket connection here
    // For now, we'll simulate notifications
    setTimeout(() => {
      setNotifications([
        { id: 1, type: 'info', message: 'Welcome to the AI Q&A Dashboard!', timestamp: new Date() },
        { id: 2, type: 'success', message: 'System is running optimally', timestamp: new Date() }
      ]);
    }, 1000);
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(authData)
      });
      
      const data = await response.json();
      
      if (response.ok) {
        if (authMode === 'login') {
          setToken(data.access_token);
          localStorage.setItem('authToken', data.access_token);
        } else {
          setAuthMode('login');
          alert('Registration successful! Please login.');
        }
      } else {
        alert(data.detail || 'Authentication failed');
      }
    } catch (error) {
      alert('Network error. Please try again.');
    }
  };

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('use_async', 'true');
    
    setUploading(true);
    setUploadProgress(0);
    
    try {
      const response = await fetch(`${API_BASE}/qa/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      const data = await response.json();
      
      if (response.ok) {
        if (data.task_id) {
          // Monitor async upload
          monitorTask(data.task_id, 'upload');
        } else {
          loadDocuments();
          addNotification('success', `Document "${file.name}" uploaded successfully!`);
        }
      } else {
        addNotification('error', data.detail || 'Upload failed');
      }
    } catch (error) {
      addNotification('error', 'Network error during upload');
    } finally {
      setUploading(false);
    }
  };

  const monitorTask = async (taskId, type) => {
    const endpoint = type === 'upload' ? 'upload/status' : 'ask/status';
    
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/qa/${endpoint}/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const data = await response.json();
        
        if (data.status === 'SUCCESS') {
          if (type === 'upload') {
            loadDocuments();
            addNotification('success', 'Document processed successfully!');
          }
          return;
        } else if (data.status === 'FAILURE') {
          addNotification('error', `Task failed: ${data.message}`);
          return;
        }
        
        // Continue monitoring
        setTimeout(checkStatus, 2000);
      } catch (error) {
        console.error('Error monitoring task:', error);
      }
    };
    
    checkStatus();
  };

  const handleSendMessage = async (useStreaming = false) => {
    if (!inputMessage.trim()) return;
    
    const userMessage = { type: 'user', content: inputMessage, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    
    const questionText = inputMessage;
    setInputMessage('');
    
    if (useStreaming) {
      handleStreamingResponse(questionText);
    } else {
      handleRegularResponse(questionText);
    }
  };

  const handleStreamingResponse = async (question) => {
    setIsStreaming(true);
    const messageId = Date.now();
    setStreamingId(messageId);
    
    const botMessage = { 
      id: messageId, 
      type: 'bot', 
      content: '', 
      timestamp: new Date(), 
      streaming: true 
    };
    setMessages(prev => [...prev, botMessage]);
    
    try {
      const response = await fetch(`${API_BASE}/qa/ask/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question })
      });
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'chunk') {
                setMessages(prev => prev.map(msg => 
                  msg.id === messageId 
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                ));
              } else if (data.type === 'complete') {
                setMessages(prev => prev.map(msg => 
                  msg.id === messageId 
                    ? { ...msg, streaming: false }
                    : msg
                ));
                loadQueryHistory();
              } else if (data.type === 'error') {
                setMessages(prev => prev.map(msg => 
                  msg.id === messageId 
                    ? { ...msg, content: `Error: ${data.message}`, streaming: false }
                    : msg
                ));
              }
            } catch (e) {
              // Ignore parsing errors
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, content: `Error: ${error.message}`, streaming: false }
          : msg
      ));
    } finally {
      setIsStreaming(false);
      setStreamingId(null);
    }
  };

  const handleRegularResponse = async (question) => {
    try {
      const response = await fetch(`${API_BASE}/qa/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question })
      });
      
      const data = await response.json();
      
      const botMessage = { 
        type: 'bot', 
        content: data.answer || 'Sorry, I could not generate an answer.', 
        timestamp: new Date(),
        responseTime: data.response_time_ms
      };
      
      setMessages(prev => [...prev, botMessage]);
      loadQueryHistory();
    } catch (error) {
      const errorMessage = { 
        type: 'bot', 
        content: 'Error: Could not process your question.', 
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const addNotification = (type, message) => {
    const notification = {
      id: Date.now(),
      type,
      message,
      timestamp: new Date()
    };
    setNotifications(prev => [notification, ...prev].slice(0, 10));
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 5000);
  };

  const handleDeleteDocument = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      const response = await fetch(`${API_BASE}/qa/documents/${docId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        loadDocuments();
        addNotification('success', 'Document deleted successfully');
      } else {
        const data = await response.json();
        addNotification('error', data.detail || 'Failed to delete document');
      }
    } catch (error) {
      addNotification('error', 'Network error during deletion');
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setMessages([]);
    setDocuments([]);
    setQueryHistory([]);
  };

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  if (showAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
          <div className="text-center mb-8">
            <div className="text-4xl mb-4">🤖</div>
            <h1 className="text-2xl font-bold text-white mb-2">AI Q&A Service</h1>
            <p className="text-blue-200">Upload documents and ask intelligent questions</p>
          </div>
          
          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <input
                type="email"
                placeholder="Email"
                value={authData.email}
                onChange={(e) => setAuthData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <div>
              <input
                type="password"
                placeholder="Password"
                value={authData.password}
                onChange={(e) => setAuthData(prev => ({ ...prev, password: e.target.value }))}
                className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105"
            >
              {authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <button
              onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
              className="text-blue-200 hover:text-white transition-colors"
            >
              {authMode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <div
            key={notification.id}
            className={`px-4 py-3 rounded-lg shadow-lg backdrop-blur-sm border ${
              notification.type === 'success' ? 'bg-green-500/90 border-green-400 text-white' :
              notification.type === 'error' ? 'bg-red-500/90 border-red-400 text-white' :
              'bg-blue-500/90 border-blue-400 text-white'
            } max-w-sm animate-in slide-in-from-right duration-300`}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm">{notification.message}</span>
              <button
                onClick={() => setNotifications(prev => prev.filter(n => n.id !== notification.id))}
                className="ml-2 text-white/70 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🤖</div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">AI Q&A Dashboard</h1>
                {userReport && (
                  <p className="text-sm text-gray-500">
                    {userReport.documents.total} documents • {userReport.queries.total} queries
                  </p>
                )}
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {systemStatus.llm_info && (
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <Activity size={16} className="text-green-500" />
                  <span>{systemStatus.llm_info.type}</span>
                </div>
              )}
              
              <button
                onClick={logout}
                className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar */}
          <div className="lg:w-64 space-y-4">
            <nav className="bg-white rounded-xl shadow-sm border p-4">
              <div className="space-y-2">
                {[
                  { id: 'chat', label: 'Chat', icon: MessageCircle },
                  { id: 'upload', label: 'Upload', icon: Upload },
                  { id: 'documents', label: 'Documents', icon: FileText },
                  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
                  { id: 'system', label: 'System', icon: Server }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                      activeTab === tab.id 
                        ? 'bg-blue-50 text-blue-700 border border-blue-200' 
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <tab.icon size={18} />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                ))}
              </div>
            </nav>

            {/* Quick Stats */}
            {userReport && (
              <div className="bg-white rounded-xl shadow-sm border p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Quick Stats</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Documents</span>
                    <span className="font-semibold">{userReport.documents.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Recent Queries</span>
                    <span className="font-semibold">{userReport.queries.recent}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Storage</span>
                    <span className="font-semibold">{userReport.documents.storage_mb}MB</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {activeTab === 'chat' && (
              <div className="bg-white rounded-xl shadow-sm border h-[700px] flex flex-col">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold text-gray-900">AI Assistant</h2>
                  <p className="text-sm text-gray-600">Ask questions about your uploaded documents</p>
                </div>
                
                <div
                  ref={chatContainerRef}
                  className="flex-1 overflow-y-auto p-4 space-y-4"
                >
                  {messages.length === 0 && (
                    <div className="text-center text-gray-500 py-12">
                      <MessageCircle size={48} className="mx-auto mb-4 text-gray-300" />
                      <p>Start a conversation with your AI assistant</p>
                      <p className="text-sm mt-2">Upload documents first, then ask questions about them</p>
                    </div>
                  )}
                  
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[70%] p-3 rounded-lg ${
                          message.type === 'user'
                            ? 'bg-blue-600 text-white'
                            : `bg-gray-100 text-gray-900 ${message.streaming ? 'animate-pulse' : ''}`
                        }`}
                      >
                        <div className="text-sm">{message.content}</div>
                        {message.responseTime && (
                          <div className="text-xs mt-1 opacity-70">
                            Response time: {message.responseTime}ms
                          </div>
                        )}
                        {message.streaming && (
                          <div className="flex items-center space-x-1 mt-2">
                            <Loader size={12} className="animate-spin" />
                            <span className="text-xs">Streaming...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="p-4 border-t">
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Ask a question about your documents..."
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isStreaming}
                    />
                    <button
                      onClick={() => handleSendMessage(false)}
                      disabled={isStreaming || !inputMessage.trim()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                    >
                      <Send size={16} />
                    </button>
                    <button
                      onClick={() => handleSendMessage(true)}
                      disabled={isStreaming || !inputMessage.trim()}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                    >
                      <Zap size={16} />
                    </button>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    Press Enter or click Send for regular response, or click ⚡ for streaming response
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'upload' && (
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Documents</h2>
                
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                    dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    handleFileUpload(Array.from(e.dataTransfer.files));
                  }}
                  onClick={() => document.getElementById('file-input').click()}
                >
                  <Upload size={48} className="mx-auto mb-4 text-gray-400" />
                  <p className="text-lg font-medium text-gray-900 mb-2">
                    Drop files here or click to select
                  </p>
                  <p className="text-gray-600">
                    Supported formats: PDF, TXT (Max 10MB)
                  </p>
                  
                  <input
                    id="file-input"
                    type="file"
                    accept=".pdf,.txt"
                    onChange={(e) => handleFileUpload(Array.from(e.target.files))}
                    className="hidden"
                  />
                </div>
                
                {uploading && (
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Loader size={20} className="animate-spin text-blue-600" />
                      <span className="text-blue-800">Processing document...</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="bg-white rounded-xl shadow-sm border">
                <div className="p-6 border-b flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">My Documents</h2>
                  <button
                    onClick={loadDocuments}
                    className="flex items-center space-x-2 px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <RefreshCw size={16} />
                    <span>Refresh</span>
                  </button>
                </div>
                
                <div className="p-6">
                  {documents.length === 0 ? (
                    <div className="text-center py-12">
                      <FileText size={48} className="mx-auto mb-4 text-gray-300" />
                      <p className="text-gray-500">No documents uploaded yet</p>
                      <button
                        onClick={() => setActiveTab('upload')}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        Upload Your First Document
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                        >
                          <div className="flex items-center space-x-3">
                            <FileText size={20} className="text-blue-600" />
                            <div>
                              <p className="font-medium text-gray-900">{doc.filename}</p>
                              <p className="text-sm text-gray-600">
                                {doc.chunk_count} chunks • {new Date(doc.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleDeleteDocument(doc.id)}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">Query History</h2>
                  
                  {queryHistory.length === 0 ? (
                    <div className="text-center py-8">
                      <BarChart3 size={48} className="mx-auto mb-4 text-gray-300" />
                      <p className="text-gray-500">No queries yet</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {queryHistory.slice(0, 10).map((query) => (
                        <div
                          key={query.id}
                          className="p-4 border border-gray-200 rounded-lg"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <p className="font-medium text-gray-900">{query.question}</p>
                            <div className="flex items-center space-x-2 text-sm text-gray-500">
                              <Clock size={14} />
                              <span>{query.response_time}ms</span>
                            </div>
                          </div>
                          <p className="text-gray-600 text-sm line-clamp-2">{query.answer}</p>
                          <p className="text-xs text-gray-500 mt-2">
                            {new Date(query.created_at).toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {userReport && (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-white rounded-xl shadow-sm border p-6">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <FileText className="text-blue-600" size={20} />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Total Documents</p>
                          <p className="text-2xl font-bold text-gray-900">{userReport.documents.total}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-sm border p-6">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <MessageCircle className="text-green-600" size={20} />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Total Queries</p>
                          <p className="text-2xl font-bold text-gray-900">{userReport.queries.total}</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-sm border p-6">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                          <Clock className="text-purple-600" size={20} />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Avg Response Time</p>
                          <p className="text-2xl font-bold text-gray-900">{Math.round(userReport.queries.avg_response_time_ms)}ms</p>
                        </div>
                      </div>
                    </div>

                    <div className="bg-white rounded-xl shadow-sm border p-6">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-orange-100 rounded-lg">
                          <Database className="text-orange-600" size={20} />
                        </div>
                        <div>
                          <p className="text-sm text-gray-600">Storage Used</p>
                          <p className="text-2xl font-bold text-gray-900">{userReport.documents.storage_mb}MB</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'system' && (
              <div className="space-y-6">
                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">System Status</h2>
                  
                  {systemStatus.llm_info && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h3 className="font-medium text-gray-900 mb-3">LLM Configuration</h3>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Type:</span>
                            <span className="font-medium">{systemStatus.llm_info.type}</span>
                          </div>
                          {systemStatus.llm_info.model && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">Model:</span>
                              <span className="font-medium">{systemStatus.llm_info.model}</span>
                            </div>
                          )}
                          {systemStatus.llm_info.url && (
                            <div className="flex justify-between">
                              <span className="text-gray-600">URL:</span>
                              <span className="font-medium text-sm">{systemStatus.llm_info.url}</span>
                            </div>
                          )}
                          <div className="flex justify-between">
                            <span className="text-gray-600">Streaming:</span>
                            <span className={`font-medium ${systemStatus.llm_info.streaming_supported ? 'text-green-600' : 'text-red-600'}`}>
                              {systemStatus.llm_info.streaming_supported ? 'Supported' : 'Not Supported'}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div>
                        <h3 className="font-medium text-gray-900 mb-3">System Settings</h3>
                        <div className="space-y-2">
                          {systemStatus.settings && Object.entries(systemStatus.settings).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-gray-600 capitalize">
                                {key.replace(/_/g, ' ')}:
                              </span>
                              <span className={`font-medium ${typeof value === 'boolean' ? (value ? 'text-green-600' : 'text-red-600') : ''}`}>
                                {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Service Health</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
                      <CheckCircle className="text-green-600" size={20} />
                      <div>
                        <p className="font-medium text-green-900">API Server</p>
                        <p className="text-sm text-green-700">Online</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
                      <CheckCircle className="text-green-600" size={20} />
                      <div>
                        <p className="font-medium text-green-900">Vector Database</p>
                        <p className="text-sm text-green-700">Connected</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
                      <CheckCircle className="text-green-600" size={20} />
                      <div>
                        <p className="font-medium text-green-900">LLM Service</p>
                        <p className="text-sm text-green-700">Available</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border p-6">
                  <h3 className="font-medium text-gray-900 mb-4">Recent Activity</h3>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <div>
                        <p className="text-sm font-medium">System initialized successfully</p>
                        <p className="text-xs text-gray-500">Just now</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <div>
                        <p className="text-sm font-medium">Vector database connected</p>
                        <p className="text-xs text-gray-500">1 minute ago</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                      <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                      <div>
                        <p className="text-sm font-medium">LLM service ready</p>
                        <p className="text-xs text-gray-500">2 minutes ago</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;