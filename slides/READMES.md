# Streaming Response Feature

This AI Question-Answering Service now supports **real-time streaming responses**, providing a better user experience by showing the AI's response as it's being generated.

## 🌊 What is Streaming?

Instead of waiting for the complete response, the streaming feature:
- Shows the AI's response in real-time as it's being generated
- Provides status updates during processing
- Displays response time when complete
- Allows users to see progress and cancel if needed

## 🚀 Features

### Backend Features
- **Dual Endpoints**: Both regular (`/qa/ask`) and streaming (`/qa/ask/stream`) endpoints
- **LLM Support**: Works with Ollama, OpenAI, and fallback SimpleLLM
- **Server-Sent Events**: Uses SSE for efficient real-time communication
- **Error Handling**: Graceful fallback to regular responses on errors
- **Performance Tracking**: Tracks response times and chunks used

### Frontend Features
- **Two Response Modes**: Regular button and "🌊 Stream Response" button
- **Real-time Display**: Shows text appearing word by word
- **Status Updates**: Displays "Searching for relevant information..." and "Generating answer..."
- **Visual Indicators**: Animated dots show when streaming is active
- **Cancellation**: Users can cancel ongoing streams
- **Auto-scroll**: Chat automatically scrolls to show new content

## 📡 API Endpoints

### Streaming Endpoint
```http
POST /qa/ask/stream
Authorization: Bearer {token}
Content-Type: application/json

{
    "question": "What is this document about?"
}
```

**Response Format** (Server-Sent Events):
```
data: {"type": "status", "message": "Searching for relevant information..."}

data: {"type": "chunk", "content": "Based on the "}

data: {"type": "chunk", "content": "provided context, "}

data: {"type": "complete", "response_time": 1250}
```

### Response Types
- `status`: Status updates during processing
- `chunk`: Individual pieces of the response text
- `complete`: Indicates streaming is finished with response time
- `error`: Error messages

## 🔧 Implementation Details

### Backend Implementation

The streaming functionality is implemented across multiple layers:

1. **Services Layer** (`services.py`):
   - Each LLM class now has both `generate_answer()` and `generate_answer_stream()` methods
   - Ollama uses native streaming API
   - OpenAI uses streaming completions
   - SimpleLLM simulates streaming by chunking responses

2. **Routes Layer** (`routes.py`):
   - New `/qa/ask/stream` endpoint using `StreamingResponse`
   - Async generator function for SSE format
   - Proper error handling and logging

3. **Database Integration**:
   - Streaming responses are still logged in QueryLog
   - Response time tracking works for both modes

### Frontend Implementation

The frontend uses modern JavaScript APIs:

1. **Fetch API with Streaming**:
   - Uses `response.body.getReader()` for streaming
   - Parses Server-Sent Events format
   - Handles partial data and buffering

2. **Real-time UI Updates**:
   - Dynamic message creation and updates
   - Visual indicators for streaming state
   - Status message system

3. **User Experience**:
   - Non-blocking interface
   - Cancellation support
   - Graceful error handling

## 🎯 Usage Examples

### Web Interface

1. **Upload Documents**: Add some PDF or TXT files
2. **Navigate to Chat**: Go to the "💬 Ask Questions" tab
3. **Choose Response Type**:
   - **Regular**: Click "Send Question" for immediate complete response
   - **Streaming**: Click "🌊 Stream Response" for real-time streaming

### API Usage

```python
import asyncio
import aiohttp
import json

async def stream_question(token, question):
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/qa/ask/stream",
            headers=headers,
            json={"question": question}
        ) as response:
            
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    
                    if data['type'] == 'chunk':
                        print(data['content'], end='', flush=True)
                    elif data['type'] == 'complete':
                        print(f"\n\nDone in {data['response_time']}ms!")
```

## 🔨 Testing

### Manual Testing
1. Start the server: `uvicorn app.main:app --reload`
2. Open the web interface at `http://localhost:8000`
3. Upload a document and try both response modes

### Automated Testing
Use the provided test script:
```bash
python test_streaming.py
```

## ⚙️ Configuration

### LLM-Specific Settings

**Ollama Streaming**:
- Requires Ollama server running with streaming-capable model
- Uses native Ollama streaming API
- Configurable via `OLLAMA_URL` and `OLLAMA_MODEL`

**OpenAI Streaming**:
- Requires valid OpenAI API key
- Uses `stream=True` parameter
- Configurable via `OPENAI_API_KEY`

**SimpleLLM Fallback**:
- Always available as fallback
- Simulates streaming with word-by-word output
- No additional configuration needed

### Performance Tuning

```python
# In services.py, adjust these parameters:

# Ollama streaming options
"options": {
    "temperature": 0.3,
    "top_p": 0.9,
    "max_tokens": 500,
}

# Streaming chunk delay (SimpleLLM)
await asyncio.sleep(0.1)  # Adjust for faster/slower streaming
```

## 🐛 Troubleshooting

### Common Issues

1. **Streaming Not Working**:
   - Check if LLM supports streaming
   - Verify network connectivity
   - Check browser console for errors

2. **Response Too Fast/Slow**:
   - Adjust streaming delay in SimpleLLM
   - Check LLM model configuration
   - Verify server resources

3. **Browser Compatibility**:
   - Requires modern browser with Fetch API support
   - Test with Chrome, Firefox, Safari latest versions

### Debug Mode

Enable debug logging:
```python
# In config.py
LOG_LEVEL=DEBUG

# In services.py
print(f"Streaming chunk: {chunk}")  # Add debug prints
```

## 🔮 Future Enhancements

Planned improvements:
- **WebSocket Support**: For even better real-time performance
- **Progress Indicators**: Show percentage completion
- **Response Caching**: Cache streaming responses for replay
- **Custom Streaming Speed**: User-configurable streaming speed
- **Rich Text Streaming**: Support for markdown formatting during streaming
- **Multi-language Support**: Stream responses in different languages

## 📊 Performance Comparison

| Feature | Regular Response | Streaming Response |
|---------|------------------|-------------------|
| Time to First Word | ~2-5 seconds | ~0.5-1 seconds |
| User Experience | Wait for complete response | See progress in real-time |
| Cancellation | Not possible | Can cancel anytime |
| Bandwidth | Single large response | Small incremental chunks |
| Server Load | Peak at response completion | Distributed over time |

The streaming feature significantly improves perceived performance and user engagement while maintaining the same quality of responses.