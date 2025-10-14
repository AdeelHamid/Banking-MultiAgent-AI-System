"""
Base Agent Class for Banking Agentic AI System

WHY THIS FILE:
- Common functionality shared by all agents
- Avoids code duplication (DRY principle)
- Enforces consistent agent structure
- Makes it easy to create new agents

LEARNING POINTS:
- Object-Oriented Programming (OOP)
- Inheritance (child classes inherit from parent)
- Abstract base classes
- Template Method pattern
"""

import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

from src.llm.gemini_client import get_gemini_client
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    
    WHY ABSTRACT BASE CLASS (ABC):
    - Defines the "contract" that all agents must follow
    - Cannot be instantiated directly (must be subclassed)
    - Forces child classes to implement required methods
    - Provides shared functionality
    
    REAL-WORLD ANALOGY:
    - BaseAgent is like a "job description"
    - Each specific agent is an "employee" who follows that description
    - All employees must do certain tasks (abstract methods)
    - But can do them in their own way (implementation)
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_role: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Initialize base agent
        
        Args:
            agent_name: Unique identifier for this agent (e.g., "customer_support")
            agent_role: Description of agent's role (used in system prompt)
            temperature: Creativity level (None = use config default)
            max_tokens: Max response length (None = use config default)
        """
        self.agent_name = agent_name
        self.agent_role = agent_role
        
        # Load shared resources
        self.config = get_config()
        self.llm_client = get_gemini_client()
        
        # Generation parameters
        # WHY: Each agent might need different creativity levels
        # Customer support: lower temperature (consistent answers)
        # Creative writing: higher temperature (varied responses)
        self.temperature = temperature or self.config.model.temperature
        self.max_tokens = max_tokens or self.config.model.max_tokens
        
        # Conversation history
        # WHY: Agents need to remember what user said
        # Example: User asks about fees, then says "What about savings accounts?"
        # Agent needs context to know what "What about" refers to
        self.conversation_history: List[Dict[str, str]] = []
        
        logger.info(f"Initialized {self.agent_name} agent")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent
        
        WHY ABSTRACT:
        - Each agent has different expertise/role
        - MUST be implemented by child classes
        - If you forget to implement it, Python will throw an error
        
        Returns:
            System prompt string that defines agent's behavior
            
        Example implementation in child class:
            def get_system_prompt(self) -> str:
                return "You are a helpful banking customer service agent..."
        """
        pass
    
    def _build_full_prompt(self, user_message: str) -> str:
        """
        Build complete prompt with system instruction and history
        
        WHY PRIVATE METHOD (underscore prefix):
        - Internal helper method
        - Not meant to be called from outside
        - Keeps implementation details hidden
        
        Args:
            user_message: Current user input
            
        Returns:
            Complete prompt ready for LLM
        """
        # Start with system prompt
        full_prompt = self.get_system_prompt() + "\n\n"
        
        # Add conversation history if exists
        if self.conversation_history:
            full_prompt += "Previous conversation:\n"
            for msg in self.conversation_history:
                role = msg['role'].capitalize()
                content = msg['content']
                full_prompt += f"{role}: {content}\n"
            full_prompt += "\n"
        
        # Add current user message
        full_prompt += f"User: {user_message}\n\nAssistant:"
        
        return full_prompt
    
    def process_message(
        self,
        user_message: str,
        add_to_history: bool = True
    ) -> str:
        """
        Process a user message and generate response
        
        WHY THIS METHOD:
        - Main interface for interacting with agent
        - Handles all complexity (prompting, history, logging)
        - Simple for caller: just send message, get response
        
        Args:
            user_message: User's question or input
            add_to_history: Whether to save this in conversation history
            
        Returns:
            Agent's response
            
        Example:
            agent = CustomerSupportAgent()
            response = agent.process_message("What is a checking account?")
            print(response)
        """
        logger.info(f"[{self.agent_name}] Processing message: {user_message[:50]}...")
        
        try:
            # Build complete prompt
            full_prompt = self._build_full_prompt(user_message)
            
            # Generate response from LLM
            response = self.llm_client.generate_response(
                prompt=full_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Add to conversation history
            if add_to_history:
                self.conversation_history.append({
                    'role': 'user',
                    'content': user_message
                })
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': response
                })
            
            logger.info(f"[{self.agent_name}] Generated response ({len(response)} chars)")
            
            return response
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error processing message: {str(e)}")
            return (
                "I apologize, but I'm having trouble processing your request right now. "
                "Please try again in a moment."
            )
    
    def clear_history(self):
        """
        Clear conversation history
        
        WHY:
        - Start fresh conversation
        - Free up memory for long conversations
        - Testing purposes
        """
        self.conversation_history = []
        logger.info(f"[{self.agent_name}] Cleared conversation history")
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation
        
        WHY:
        - Debugging
        - Logging
        - Analytics (track what users ask about)
        
        Returns:
            Human-readable conversation summary
        """
        if not self.conversation_history:
            return "No conversation history"
        
        summary = f"Conversation with {self.agent_name}:\n"
        summary += f"Total messages: {len(self.conversation_history)}\n\n"
        
        for i, msg in enumerate(self.conversation_history, 1):
            role = msg['role'].upper()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            summary += f"{i}. {role}: {content}\n"
        
        return summary
    
    def __repr__(self) -> str:
        """
        String representation of agent
        
        WHY:
        - Useful for debugging
        - Shows agent info when you print(agent)
        """
        return (
            f"{self.__class__.__name__}("
            f"name='{self.agent_name}', "
            f"messages={len(self.conversation_history)})"
        )