// ==========================================
// STEP 1: Basic React Imports and Setup
// ==========================================

import React, { useState, useEffect, useRef } from 'react';
// React: Main library
// useState: For managing changing data (like login status)
// useEffect: For running code when component loads
// useRef: For directly accessing DOM elements (like scrolling chat)

import { Upload, MessageCircle, FileText, /* ... other icons */ } from 'lucide-react';
// These are icon components for our UI

// ==========================================
// STEP 2: Component Definition and State
// ==========================================

const Dashboard = () => {
  // useState creates variables that can change and trigger re-renders
  
  // Authentication state
  const [user, setUser] = useState(null);                          // Current user info
  const [token, setToken] = useState(localStorage.getItem('authToken')); // Login token
  const [showAuth, setShowAuth] = useState(!token);               // Show login form?
  
  // UI state  
  const [activeTab, setActiveTab] = useState('chat');             // Which tab is open
  const [notifications, setNotifications] = useState([]);         // Alert messages
  
  // Data state
  const [documents, setDocuments] = useState([]);                 // User's uploaded files
  const [messages, setMessages] = useState([]);                   // Chat conversation
  const [queryHistory, setQueryHistory] = useState([]);           // Past questions
  
  // Form state
  const [inputMessage, setInputMessage] = useState('');           // Current message being typed
  const [authData, setAuthData] = useState({ email: '', password: '' }); // Login form
  
  // Loading states
  const [uploading, setUploading] = useState(false);              // File uploading?
  const [isStreaming, setIsStreaming] = useState(false);          // Getting streamed response?

// ==========================================
// STEP 3: useEffect - Code that runs when component loads
// ==========================================

  useEffect(() => {
    if (token) {
      // If user is logged in, load their data
      setShowAuth(false);
      loadUserData();
      loadDocuments();
      loadQueryHistory();
    } else {
      // If not logged in, show login form
      setShowAuth(true);
    }
  }, [token]); // Run this when 'token' changes

// ==========================================
// STEP 4: API Functions - Talk to your FastAPI backend
// ==========================================

  const loadDocuments = async () => {
    try {
      const response = await fetch(`/qa/documents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data); // Update the documents list
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault(); // Don't refresh the page
    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(authData) // Send email/password
      });
      
      const data = await response.json();
      
      if (response.ok && authMode === 'login') {
        setToken(data.access_token);
        localStorage.setItem('authToken', data.access_token);
      }
    } catch (error) {
      alert('Network error. Please try again.');
    }
  };

// ==========================================
// STEP 5: File Upload Handler
// ==========================================

  const handleFileUpload = async (files) => {
    if (files.length === 0) return;
    
    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    setUploading(true); // Show loading spinner
    
    try {
      const response = await fetch(`/qa/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (response.ok) {
        loadDocuments(); // Refresh the documents list
        addNotification('success', 'File uploaded successfully!');
      }
    } catch (error) {
      addNotification('error', 'Upload failed');
    } finally {
      setUploading(false); // Hide loading spinner
    }
  };

// ==========================================
// STEP 6: Chat Message Handler
// ==========================================

  const handleSendMessage = async (useStreaming = false) => {
    if (!inputMessage.trim()) return;
    
    // Add user message to chat
    const userMessage = { 
      type: 'user', 
      content: inputMessage, 
      timestamp: new Date() 
    };
    setMessages(prev => [...prev, userMessage]); // Add to existing messages
    
    const questionText = inputMessage;
    setInputMessage(''); // Clear the input
    
    if (useStreaming) {
      await handleStreamingResponse(questionText);
    } else {
      await handleRegularResponse(questionText);
    }
  };

  const handleRegularResponse = async (question) => {
    try {
      const response = await fetch(`/qa/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question })
      });
      
      const data = await response.json();
      
      // Add bot response to chat
      const botMessage = { 
        type: 'bot', 
        content: data.answer, 
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      const errorMessage = { 
        type: 'bot', 
        content: 'Error: Could not process your question.', 
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

// ==========================================
// STEP 7: Streaming Response Handler
// ==========================================

  const handleStreamingResponse = async (question) => {
    setIsStreaming(true);
    const messageId = Date.now();
    
    // Create empty bot message that we'll fill with streaming text
    const botMessage = { 
      id: messageId, 
      type: 'bot', 
      content: '', 
      timestamp: new Date(), 
      streaming: true 
    };
    setMessages(prev => [...prev, botMessage]);
    
    try {
      const response = await fetch(`/qa/ask/stream`, {
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
                // Add this text chunk to the bot message
                setMessages(prev => prev.map(msg => 
                  msg.id === messageId 
                    ? { ...msg, content: msg.content + data.content }
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
      console.error('Streaming error:', error);
    } finally {
      setIsStreaming(false);
    }
  };

// ==========================================
// STEP 8: UI Helper Functions
// ==========================================

  const addNotification = (type, message) => {
    const notification = {
      id: Date.now(),
      type,    // 'success', 'error', 'info'
      message,
      timestamp: new Date()
    };
    setNotifications(prev => [notification, ...prev].slice(0, 10));
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== notification.id));
    }, 5000);
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setMessages([]);
    setDocuments([]);
  };

// ==========================================
// STEP 9: Render Logic (What the user sees)
// ==========================================

  // If not logged in, show login form
  if (showAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center p-4">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 w-full max-w-md border border-white/20">
          <h1 className="text-2xl font-bold text-white mb-6 text-center">AI Q&A Service</h1>
          
          <form onSubmit={handleAuth} className="space-y-4">
            <input
              type="email"
              placeholder="Email"
              value={authData.email}
              onChange={(e) => setAuthData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-blue-200"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={authData.password}
              onChange={(e) => setAuthData(prev => ({ ...prev, password: e.target.value }))}
              className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-blue-200"
              required
            />
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700"
            >
              Sign In
            </button>
          </form>
        </div>
      </div>
    );
  }

  // If logged in, show the main dashboard
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 h-16 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-900">AI Q&A Dashboard</h1>
          <button onClick={logout} className="text-gray-600 hover:text-gray-900">
            Logout
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex gap-8">
          {/* Sidebar */}
          <div className="w-64">
            <nav className="bg-white rounded-xl shadow-sm border p-4">
              {[
                { id: 'chat', label: 'Chat', icon: MessageCircle },
                { id: 'upload', label: 'Upload', icon: Upload },
                { id: 'documents', label: 'Documents', icon: FileText }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                    activeTab === tab.id 
                      ? 'bg-blue-50 text-blue-700' 
                      : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <tab.icon size={18} />
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {/* Chat Tab */}
            {activeTab === 'chat' && (
              <div className="bg-white rounded-xl shadow-sm border h-[700px] flex flex-col">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold">AI Assistant</h2>
                </div>
                
                {/* Chat Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[70%] p-3 rounded-lg ${
                          message.type === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}
                      >
                        {message.content}
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Message Input */}
                <div className="p-4 border-t">
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                      placeholder="Ask a question..."
                      className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => handleSendMessage(false)}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Send
                    </button>
                    <button
                      onClick={() => handleSendMessage(true)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Stream
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Upload Tab */}
            {activeTab === 'upload' && (
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h2 className="text-lg font-semibold mb-4">Upload Documents</h2>
                
                <div
                  className="border-2 border-dashed rounded-xl p-8 text-center hover:border-gray-400 cursor-pointer"
                  onClick={() => document.getElementById('file-input').click()}
                >
                  <Upload size={48} className="mx-auto mb-4 text-gray-400" />
                  <p className="text-lg font-medium mb-2">Drop files here or click to select</p>
                  <p className="text-gray-600">Supported: PDF, TXT (Max 10MB)</p>
                  
                  <input
                    id="file-input"
                    type="file"
                    accept=".pdf,.txt"
                    onChange={(e) => handleFileUpload(Array.from(e.target.files))}
                    className="hidden"
                  />
                </div>
              </div>
            )}

            {/* Documents Tab */}
            {activeTab === 'documents' && (
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h2 className="text-lg font-semibold mb-4">My Documents</h2>
                
                <div className="space-y-3">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{doc.filename}</p>
                        <p className="text-sm text-gray-600">
                          {doc.chunk_count} chunks • {new Date(doc.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteDocument(doc.id)}
                        className="text-red-600 hover:bg-red-50 p-2 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  ))}
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