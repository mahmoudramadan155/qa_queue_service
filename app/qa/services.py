import time
import requests
import json
from typing import List, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from app.qa.vector_store import vector_store
from app.database.models import QueryLog
from app.config import settings
import asyncio

# Simple fallback LLM (you can replace with OpenAI or other LLMs)
class SimpleLLM:
    def generate_answer(self, question: str, context: List[str]) -> str:
        """Generate answer based on context (simple implementation)"""
        if not context:
            return "I don't have enough information to answer this question. Please upload relevant documents first."
        
        # Simple context-based answer generation
        combined_context = "\n\n".join(context[:3])  # Use top 3 chunks
        
        # Basic keyword matching and response generation
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['what', 'define', 'definition']):
            return f"Based on the provided context:\n\n{combined_context[:800]}..."
        elif any(word in question_lower for word in ['how', 'explain', 'process']):
            return f"Here's how it works according to the documents:\n\n{combined_context[:800]}..."
        elif any(word in question_lower for word in ['when', 'time', 'date']):
            return f"According to the information available:\n\n{combined_context[:800]}..."
        else:
            return f"Based on the relevant information I found:\n\n{combined_context[:800]}..."
    
    async def generate_answer_stream(self, question: str, context: List[str]) -> AsyncGenerator[str, None]:
        """Generate streaming answer based on context"""
        answer = self.generate_answer(question, context)
        
        # Simulate streaming by yielding chunks of the answer
        words = answer.split()
        chunk_size = 3  # Words per chunk
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            yield chunk
            await asyncio.sleep(0.1)  # Simulate processing time

class OllamaLLM:
    def __init__(self):
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
    
    def generate_answer(self, question: str, context: List[str]) -> str:
        """Generate answer using Ollama"""
        if not context:
            return "I don't have enough information to answer this question. Please upload relevant documents first."
        
        # Prepare context - use top 5 chunks
        combined_context = "\n\n".join(context[:5])
        
        # Create prompt for the model
        prompt = f"""Based on the following context, please answer the question. If the context doesn't contain enough information to answer the question, please say so clearly. Be concise and accurate.

Context:
{combined_context}

Question: {question}

Answer:"""
        
        try:
            # Prepare request payload for Ollama
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 500,
                    "stop": ["Question:", "Context:"]
                }
            }
            
            # Make request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "").strip()
                
                if answer:
                    return answer
                else:
                    return "I couldn't generate a proper answer. Please try rephrasing your question."
            else:
                print(f"Ollama API error: {response.status_code} - {response.text}")
                return SimpleLLM().generate_answer(question, context)
                
        except requests.exceptions.Timeout:
            print("Ollama request timed out")
            return SimpleLLM().generate_answer(question, context)
        except requests.exceptions.ConnectionError:
            print("Could not connect to Ollama. Make sure it's running.")
            return SimpleLLM().generate_answer(question, context)
        except Exception as e:
            print(f"Ollama error: {e}")
            return SimpleLLM().generate_answer(question, context)
    
    async def generate_answer_stream(self, question: str, context: List[str]) -> AsyncGenerator[str, None]:
        """Generate streaming answer using Ollama"""
        if not context:
            yield "I don't have enough information to answer this question. Please upload relevant documents first."
            return
        
        # Prepare context
        combined_context = "\n\n".join(context[:5])
        
        prompt = f"""Based on the following context, please answer the question. If the context doesn't contain enough information to answer the question, please say so clearly. Be concise and accurate.

Context:
{combined_context}

Question: {question}

Answer:"""
        
        try:
            # Prepare request payload for Ollama streaming
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 500,
                    "stop": ["Question:", "Context:"]
                }
            }
            
            # Make streaming request to Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                chunk = data['response']
                                if chunk:
                                    yield chunk
                            
                            # Check if done
                            if data.get('done', False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
            else:
                # Fallback to simple LLM
                async for chunk in SimpleLLM().generate_answer_stream(question, context):
                    yield chunk
                    
        except Exception as e:
            print(f"Ollama streaming error: {e}")
            # Fallback to simple LLM
            async for chunk in SimpleLLM().generate_answer_stream(question, context):
                yield chunk
    
    def is_available(self) -> bool:
        """Check if Ollama is available and the model is loaded"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return any(model.get("name", "").startswith(self.model) for model in models)
        except:
            pass
        return False

class OpenAILLM:
    def __init__(self):
        if settings.openai_api_key:
            import openai
            openai.api_key = settings.openai_api_key
            self.client = openai.OpenAI()
        else:
            self.client = None
    
    def generate_answer(self, question: str, context: List[str]) -> str:
        """Generate answer using OpenAI GPT"""
        if not self.client:
            return SimpleLLM().generate_answer(question, context)
        
        if not context:
            return "I don't have enough information to answer this question. Please upload relevant documents first."
        
        # Prepare context
        combined_context = "\n\n".join(context[:5])  # Use top 5 chunks
        
        prompt = f"""Based on the following context, please answer the question. If the context doesn't contain enough information to answer the question, please say so.

Context:
{combined_context}

Question: {question}

Answer:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Be concise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return SimpleLLM().generate_answer(question, context)
    
    async def generate_answer_stream(self, question: str, context: List[str]) -> AsyncGenerator[str, None]:
        """Generate streaming answer using OpenAI GPT"""
        if not self.client:
            async for chunk in SimpleLLM().generate_answer_stream(question, context):
                yield chunk
            return
        
        if not context:
            yield "I don't have enough information to answer this question. Please upload relevant documents first."
            return
        
        # Prepare context
        combined_context = "\n\n".join(context[:5])
        
        prompt = f"""Based on the following context, please answer the question. If the context doesn't contain enough information to answer the question, please say so.

Context:
{combined_context}

Question: {question}

Answer:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Be concise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"OpenAI streaming error: {e}")
            # Fallback to simple LLM
            async for chunk in SimpleLLM().generate_answer_stream(question, context):
                yield chunk

class QAService:
    def __init__(self):
        # Choose LLM based on configuration priority:
        # 1. Ollama (if available and configured)
        # 2. OpenAI (if API key provided)
        # 3. SimpleLLM (fallback)
        
        self.llm = None
        
        # Try Ollama first if configured
        if settings.ollama_enabled:
            ollama_llm = OllamaLLM()
            if ollama_llm.is_available():
                self.llm = ollama_llm
                print(f"Using Ollama LLM with model: {settings.ollama_model}")
            else:
                print(f"Ollama not available. Model '{settings.ollama_model}' may not be loaded.")
        
        # Fallback to OpenAI if Ollama not available
        if not self.llm and settings.openai_api_key:
            self.llm = OpenAILLM()
            print("Using OpenAI LLM")
        
        # Final fallback to simple LLM
        if not self.llm:
            self.llm = SimpleLLM()
            print("Using Simple LLM (fallback)")
    
    def answer_question(self, question: str, user_id: int, db: Session) -> str:
        """Answer question using RAG (Retrieval-Augmented Generation)"""
        start_time = time.time()
        
        # 1. Retrieve relevant chunks from vector store
        similar_chunks = vector_store.search_similar_chunks(
            query=question,
            user_id=user_id,
            top_k=5
        )
        
        # 2. Extract context from chunks
        context = [chunk['content'] for chunk in similar_chunks]
        
        # 3. Generate answer using LLM
        answer = self.llm.generate_answer(question, context)
        
        # 4. Log the query
        response_time = int((time.time() - start_time) * 1000)
        query_log = QueryLog(
            user_id=user_id,
            question=question,
            answer=answer,
            response_time=response_time,
            chunks_used=len(similar_chunks)
        )
        db.add(query_log)
        db.commit()
        
        return answer
    
    async def answer_question_stream(self, question: str, context: List[str], user_id: int) -> AsyncGenerator[str, None]:
        """Answer question using streaming RAG"""
        # Generate streaming answer using LLM
        async for chunk in self.llm.generate_answer_stream(question, context):
            yield chunk
    
    def get_llm_info(self) -> dict:
        """Get information about the current LLM being used"""
        llm_type = type(self.llm).__name__
        info = {"type": llm_type}
        
        if isinstance(self.llm, OllamaLLM):
            info.update({
                "model": settings.ollama_model,
                "url": settings.ollama_url,
                "available": self.llm.is_available(),
                "streaming_supported": True
            })
        elif isinstance(self.llm, OpenAILLM):
            info.update({
                "model": "gpt-3.5-turbo",
                "has_api_key": bool(settings.openai_api_key),
                "streaming_supported": True
            })
        else:
            info.update({
                "streaming_supported": True
            })
        
        return info

# Global QA service instance
qa_service = QAService()