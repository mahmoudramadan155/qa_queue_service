# React Frontend File Structure for AI Q&A Service

## 📁 Project Directory Structure

```
your-qa-project/
├── app/                          # Your existing FastAPI backend
│   ├── auth/
│   ├── qa/
│   ├── database/
│   └── main.py
├── frontend/                     # NEW: React frontend directory
│   ├── public/
│   │   ├── index.html           # Main HTML file
│   │   ├── favicon.ico          # Website icon
│   │   └── manifest.json        # App metadata
│   ├── src/
│   │   ├── components/          # Reusable UI pieces
│   │   │   ├── Auth/
│   │   │   │   ├── LoginForm.js
│   │   │   │   └── RegisterForm.js
│   │   │   ├── Chat/
│   │   │   │   ├── ChatContainer.js
│   │   │   │   ├── Message.js
│   │   │   │   └── MessageInput.js
│   │   │   ├── Documents/
│   │   │   │   ├── DocumentList.js
│   │   │   │   ├── DocumentItem.js
│   │   │   │   └── FileUpload.js
│   │   │   ├── Layout/
│   │   │   │   ├── Header.js
│   │   │   │   ├── Sidebar.js
│   │   │   │   └── Notifications.js
│   │   │   └── Common/
│   │   │       ├── Button.js
│   │   │       ├── Loading.js
│   │   │       └── Card.js
│   │   ├── pages/               # Full page components
│   │   │   ├── Dashboard.js
│   │   │   ├── ChatPage.js
│   │   │   ├── DocumentsPage.js
│   │   │   └── AnalyticsPage.js
│   │   ├── hooks/               # Custom React logic
│   │   │   ├── useAuth.js
│   │   │   ├── useAPI.js
│   │   │   └── useWebSocket.js
│   │   ├── services/            # API communication
│   │   │   ├── api.js
│   │   │   ├── auth.js
│   │   │   └── documents.js
│   │   ├── utils/               # Helper functions
│   │   │   ├── constants.js
│   │   │   └── helpers.js
│   │   ├── styles/              # CSS files
│   │   │   ├── globals.css
│   │   │   └── components.css
│   │   ├── App.js               # Main app component
│   │   ├── index.js             # Entry point
│   │   └── App.css              # Main styles
│   ├── package.json             # Dependencies list
│   ├── package-lock.json        # Exact dependency versions
│   └── README.md                # React documentation
├── requirements.txt             # Python dependencies (existing)
├── docker-compose.yml           # Docker config (existing)
└── README.md                    # Main project docs
```

## 🚀 **Setup Instructions**

### Step 1: Install Node.js
Download and install Node.js from: https://nodejs.org/
This gives you `npm` (Node Package Manager) to install React.

### Step 2: Create React App
```bash
# Navigate to your project directory
cd your-qa-project

# Create React frontend
npx create-react-app frontend
cd frontend

# Install additional dependencies we need
npm install lucide-react
```

### Step 3: Replace Default Files
Replace the contents of these files with our custom code.

## 📄 **Key Files Explained**

### 1. `package.json` - Project Configuration
```json
{
  "name": "qa-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.263.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  }
}
```

### 2. `public/index.html` - Main HTML Template
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Q&A Service</title>
</head>
<body>
  <div id="root"></div>
  <!-- React will inject your app here -->
</body>
</html>
```

### 3. `src/index.js` - Entry Point
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

### 4. `src/App.js` - Main Component
This is where our dashboard code goes (the big component I provided).

## 🧩 **React Concepts Explained**

### What are Components?
Components are like functions that return HTML. They're reusable pieces of UI.

```javascript
// Simple component example
function Welcome() {
  return <h1>Hello, World!</h1>;
}

// Component with data (props)
function UserGreeting({ name }) {
  return <h1>Hello, {name}!</h1>;
}
```

### What is JSX?
JSX lets you write HTML-like code in JavaScript:

```javascript
// This JSX...
const element = <h1>Hello, world!</h1>;

// ...becomes this JavaScript:
const element = React.createElement('h1', null, 'Hello, world!');
```

### What is State?
State is data that can change over time:

```javascript
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0); // count starts at 0
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Click me
      </button>
    </div>
  );
}
```

### What are useEffect hooks?
useEffect runs code when component loads or data changes:

```javascript
import { useEffect, useState } from 'react';

function UserProfile() {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // This runs when component loads
    fetchUserData().then(setUser);
  }, []); // Empty array means "run once"
  
  return <div>{user?.name}</div>;
}
```

## 🔧 **How to Connect to Your FastAPI Backend**

### API Service File (`src/services/api.js`)
```javascript
const API_BASE = 'http://localhost:8009'; // Your FastAPI server

export const apiCall = async (endpoint, options = {}) => {
  const token = localStorage.getItem('authToken');
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
    ...options,
  });
  
  return response.json();
};

export const login = (email, password) => 
  apiCall('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });

export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return apiCall('/qa/upload', {
    method: 'POST',
    body: formData,
    headers: {} // Let browser set Content-Type for FormData
  });
};
```

## 🎨 **Styling with Tailwind CSS**

The dashboard uses Tailwind CSS for styling. Install it:

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Add to `tailwind.config.js`:
```javascript
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

## 🏃‍♂️ **Running Your React App**

```bash
# In the frontend directory
npm start
```

This starts a development server at `http://localhost:3000`

## 🔄 **Development Workflow**

1. **Start your FastAPI backend**: `python -m uvicorn app.main:app --reload`
2. **Start your React frontend**: `npm start`
3. **Make changes**: Edit files in `src/`
4. **See changes**: Browser automatically refreshes

## 📦 **Building for Production**

```bash
# Create optimized build
npm run build

# This creates a 'build' folder with static files
# Copy these to your FastAPI static folder
cp -r build/* ../static/
```

## 🤝 **Integration with Your Backend**

Your FastAPI app can serve the React build:

```python
# In your main.py
from fastapi.staticfiles import StaticFiles

# Serve React build files
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

This way, both frontend and backend run from the same domain!
