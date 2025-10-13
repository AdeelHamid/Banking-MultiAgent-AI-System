"""
Gemini LLM Client for Banking Agentic AI System

WHY THIS FILE:
- Wraps Google's Gemini API in a clean interface
- Handles errors gracefully
- Provides consistent API for rest of application
- Easy to add caching, retry logic, etc.

LEARNING POINTS:
- API client pattern (wrapper around external service)
- Error handling with try/except
- Type hints for better code quality
- Singleton pattern for efficiency
"""

import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai

from src.utils.config import get_config

# Setup logging
logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for interacting with Google's Gemini API
    
    WHY A CLASS:
    - Encapsulates API configuration
    - Reusable across the application
    - Easy to test (can mock this class)
    - Maintains state (API key, model settings)
    
    SINGLETON PATTERN:
    - Only one instance needed (saves memory, API connections)
    - Loaded once at startup
    """
    
    def __init__(self):
        """
        Initialize Gemini client
        
        WHY IN __init__:
        - Load configuration once
        - Setup API authentication
        - Configure default parameters
        """
        self.config = get_config()
        
        # Configure Gemini API with your key
        # This is like "logging in" to use Gemini
        genai.configure(api_key=self.config.gemini.api_key)
        
        # Create the model instance
        # WHY: This is the actual AI "brain" we'll talk to
        self.model = genai.GenerativeModel(
            model_name=self.config.gemini.model
        )
        
        logger.info(
            f"GeminiClient initialized with model: {self.config.gemini.model}"
        )
    
    def generate_response(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Generate a response from Gemini
        
        WHY THIS METHOD:
        - Main interface for getting AI responses
        - Handles all API complexity
        - Provides sensible defaults
        - Includes error handling
        
        Args:
            prompt: The user's question/input
            temperature: Creativity level (0.0-1.0). Uses config default if None
            max_tokens: Max response length. Uses config default if None
            system_instruction: System-level instructions (like "You are a banker")
            
        Returns:
            Generated text response
            
        Example:
            client = GeminiClient()
            response = client.generate_response(
                prompt="What is a checking account?",
                system_instruction="You are a helpful bank assistant"
            )
            print(response)
        """
        # Use config defaults if not provided
        # WHY: Don't make caller specify everything every time
        temperature = temperature or self.config.model.temperature
        max_tokens = max_tokens or self.config.model.max_tokens
        
        try:
            # Create generation config
            # WHY: Controls how the AI generates responses
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=self.config.model.top_p,
            )
            
            # Build the full prompt
            # If we have system instruction, prepend it
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\nUser: {prompt}\n\nAssistant:"
            
            logger.debug(f"Sending request to Gemini with prompt length: {len(prompt)}")
            
            # Make the API call
            # WHY: This is where the magic happens - AI generates text!
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            # Extract text from response
            response_text = response.text
            
            logger.info(f"Received response from Gemini (length: {len(response_text)})")
            
            return response_text
            
        except Exception as e:
            # Error handling - CRITICAL for production!
            # WHY: API can fail (network issues, rate limits, etc.)
            logger.error(f"Error generating response from Gemini: {str(e)}")
            
            # Return a graceful error message instead of crashing
            return f"I apologize, but I'm experiencing technical difficulties. Please try again. (Error: {str(e)})"
    
    def generate_with_history(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate response with conversation history (for chat)
        
        WHY THIS METHOD:
        - Enables multi-turn conversations
        - AI remembers context from previous messages
        - Essential for chat-based agents
        
        Args:
            messages: List of message dicts with 'role' and 'content'
                      Example: [
                          {"role": "user", "content": "Hello"},
                          {"role": "assistant", "content": "Hi!"},
                          {"role": "user", "content": "What's your name?"}
                      ]
            temperature: Creativity level
            max_tokens: Max response length
            
        Returns:
            Generated response text
        """
        temperature = temperature or self.config.model.temperature
        max_tokens = max_tokens or self.config.model.max_tokens
        
        try:
            # Start a chat session
            # WHY: Chat sessions maintain conversation context
            chat = self.model.start_chat(history=[])
            
            # Build history in Gemini's format
            for msg in messages[:-1]:  # All except last message
                if msg['role'] == 'user':
                    chat.send_message(msg['content'])
            
            # Send final message and get response
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                top_p=self.config.model.top_p,
            )
            
            response = chat.send_message(
                messages[-1]['content'],
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error in chat generation: {str(e)}")
            return f"I apologize, but I'm experiencing technical difficulties. Please try again."
    
    def test_connection(self) -> bool:
        """
        Test if Gemini API is working
        
        WHY THIS METHOD:
        - Quick health check
        - Useful for debugging
        - Can use in startup checks
        
        Returns:
            True if API is working, False otherwise
        """
        try:
            response = self.generate_response(
                prompt="Respond with OK if you can read this.",
                max_tokens=10
            )
            
            success = "OK" in response or "ok" in response.lower()
            
            if success:
                logger.info("✅ Gemini API connection test: SUCCESS")
            else:
                logger.warning(f"⚠️  Gemini API connection test: Unexpected response - {response}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Gemini API connection test: FAILED - {str(e)}")
            return False


# Global instance - loaded once when module is imported
# WHY GLOBAL: Avoids recreating client (wastes resources)
# All code imports this same instance
_gemini_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    """
    Get the global Gemini client instance (Singleton pattern)
    
    WHY THIS FUNCTION:
    - Lazy loading (only creates client when first used)
    - Ensures only one instance exists
    - Easy to use: just call get_gemini_client()
    
    Returns:
        Global GeminiClient instance
        
    Example:
        from src.llm.gemini_client import get_gemini_client
        
        client = get_gemini_client()
        response = client.generate_response("Hello!")
    """
    global _gemini_client
    
    if _gemini_client is None:
        _gemini_client = GeminiClient()
        logger.info("Created new GeminiClient instance")
    
    return _gemini_client


# Test code - runs when you execute this file directly
# python -m src.llm.gemini_client
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🤖 Testing Gemini Client")
    print("="*60 + "\n")
    
    # Test 1: Connection Test
    print("Test 1: Connection Test")
    print("-" * 60)
    client = get_gemini_client()
    
    if client.test_connection():
        print("✅ Connection successful!\n")
    else:
        print("❌ Connection failed! Check your API key in .env\n")
        exit(1)
    
    # Test 2: Simple Question
    print("\nTest 2: Banking Question")
    print("-" * 60)
    question = "What is a savings account?"
    print(f"Question: {question}\n")
    
    response = client.generate_response(
        prompt=question,
        system_instruction="You are a helpful banking assistant. Give concise answers."
    )
    
    print(f"Response:\n{response}\n")
    
    # Test 3: Multi-turn Conversation
    print("\nTest 3: Conversation with History")
    print("-" * 60)
    
    messages = [
        {"role": "user", "content": "Hi, I'm interested in opening an account"},
        {"role": "assistant", "content": "Hello! I'd be happy to help. What type of account are you interested in?"},
        {"role": "user", "content": "What's the difference between checking and savings?"}
    ]
    
    print("Conversation:")
    for msg in messages:
        print(f"  {msg['role'].upper()}: {msg['content']}")
    
    print("\nResponse:")
    response = client.generate_with_history(messages)
    print(f"{response}\n")
    
    print("="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")