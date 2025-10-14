"""
Customer Support Agent for Banking

WHY THIS AGENT:
- Handles general banking questions
- First point of contact for customers
- Friendly, helpful, knowledgeable about DemoBank products

CAPABILITIES:
- Answer questions about accounts, fees, services
- Provide branch information
- Explain banking terms
- Help with common issues
"""

import logging
from typing import Optional

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CustomerSupportAgent(BaseAgent):
    """
    Customer Support Agent - Your friendly banking assistant
    
    WHY INHERIT FROM BaseAgent:
    - Gets all common functionality for free (history, prompting, etc.)
    - Only need to define what makes this agent unique
    - Follows DRY principle
    
    INHERITANCE EXPLAINED:
    - BaseAgent = Parent class (defines structure)
    - CustomerSupportAgent = Child class (specific implementation)
    - Child inherits all parent methods and can override/extend them
    """
    
    def __init__(
        self,
        bank_name: Optional[str] = None,
        temperature: float = 0.7
    ):
        """
        Initialize Customer Support Agent
        
        Args:
            bank_name: Name of the bank (defaults to config value)
            temperature: Creativity level (0.7 = balanced, not too creative, not too rigid)
        
        WHY temperature=0.7:
        - Customer support needs consistency (not too creative)
        - But also needs to sound natural (not robotic)
        - 0.7 is the sweet spot for banking
        """
        # Get bank name from config if not provided
        if bank_name is None:
            from src.utils.config import get_config
            bank_name = get_config().bank_name
        
        self.bank_name = bank_name
        
        # Call parent class constructor
        # WHY: Sets up LLM client, conversation history, etc.
        super().__init__(
            agent_name="customer_support",
            agent_role=f"{bank_name} Customer Support Representative",
            temperature=temperature,
            max_tokens=1500  # Enough for detailed explanations
        )
        
        logger.info(f"CustomerSupportAgent initialized for {bank_name}")
    
    def get_system_prompt(self) -> str:
        """
        Define the agent's personality and expertise
        
        WHY THIS METHOD:
        - Required by BaseAgent (abstract method)
        - Defines WHO the agent is
        - Determines HOW the agent responds
        
        PROMPT ENGINEERING:
        - This is an art and science
        - Small changes here dramatically affect behavior
        - Always test different prompts!
        
        Returns:
            System prompt that shapes agent's behavior
        """
        return f"""You are a helpful and friendly customer support representative for {self.bank_name}.

Your role and responsibilities:
- Answer customer questions about banking products and services
- Provide information about accounts (checking, savings, business accounts)
- Explain fees, interest rates, and account features
- Help customers understand banking terms and processes
- Provide branch locations and contact information
- Assist with common issues like card locks, password resets, etc.

Guidelines for responses:
1. Be friendly, professional, and empathetic
2. Use simple language - avoid jargon when possible
3. If you don't know something specific, acknowledge it and offer to help find the information
4. Never make up specific numbers or details - only provide information you're confident about
5. For complex issues (fraud, disputes, technical problems), recommend contacting a specialist
6. Always prioritize customer security and privacy
7. Keep responses concise but complete (2-4 paragraphs maximum)

Banking products you support:
- Savings Accounts (Standard and Premium)
- Checking Accounts (Essential and Business)
- Personal Loans, Home Loans, Auto Loans, Student Loans
- Credit Cards
- Online and Mobile Banking

Remember: You represent {self.bank_name}. Be helpful, accurate, and customer-focused."""

    def handle_greeting(self) -> str:
        """
        Generate a friendly greeting
        
        WHY THIS METHOD:
        - Good UX to greet users
        - Sets friendly tone
        - Optional convenience method
        
        Returns:
            Greeting message
        """
        return self.process_message(
            "Greet the customer warmly and ask how you can help them today.",
            add_to_history=False  # Don't save greeting in history
        )
    
    def handle_farewell(self) -> str:
        """
        Generate a friendly goodbye
        
        Returns:
            Farewell message
        """
        return self.process_message(
            "Thank the customer and wish them well.",
            add_to_history=False
        )


# Convenience function for quick testing
def create_customer_support_agent() -> CustomerSupportAgent:
    """
    Factory function to create a customer support agent
    
    WHY FACTORY FUNCTION:
    - Clean, simple interface for creating agents
    - Can add initialization logic here
    - Easy to change implementation later
    
    Returns:
        Configured CustomerSupportAgent instance
        
    Example:
        agent = create_customer_support_agent()
        response = agent.process_message("What is a savings account?")
    """
    return CustomerSupportAgent()


# Test code - run with: python -m src.agents.customer_support_agent
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏦 Customer Support Agent - Interactive Test")
    print("="*70 + "\n")
    
    # Create agent
    agent = create_customer_support_agent()
    
    # Test 1: Greeting
    print("Test 1: Greeting")
    print("-" * 70)
    greeting = agent.handle_greeting()
    print(f"Agent: {greeting}\n")
    
    # Test 2: Banking Questions
    print("\nTest 2: Banking Knowledge")
    print("-" * 70)
    
    test_questions = [
        "What is the difference between a checking and savings account?",
        "What are your interest rates for savings accounts?",
        "Do you charge monthly fees?",
        "How can I open an account?",
        "What if I lose my debit card?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nQ{i}: {question}")
        response = agent.process_message(question)
        print(f"A{i}: {response}\n")
        print("-" * 70)
    
    # Test 3: Conversation with Context
    print("\nTest 3: Multi-turn Conversation (Testing Memory)")
    print("-" * 70)
    
    # Clear history for clean test
    agent.clear_history()
    
    conversation = [
        "I'm interested in opening a savings account",
        "What are the interest rates?",
        "And what about the fees?",
        "Okay, how do I open one?"
    ]
    
    for msg in conversation:
        print(f"\nUser: {msg}")
        response = agent.process_message(msg)
        print(f"Agent: {response}")
    
    # Show conversation summary
    print("\n" + "="*70)
    print("Conversation Summary:")
    print("="*70)
    print(agent.get_conversation_summary())
    
    # Test 4: Farewell
    print("\n" + "="*70)
    print("Test 4: Farewell")
    print("-" * 70)
    farewell = agent.handle_farewell()
    print(f"Agent: {farewell}\n")
    
    print("="*70)
    print("✅ All tests completed!")
    print("="*70 + "\n")