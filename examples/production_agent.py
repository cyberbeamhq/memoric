"""
Production AI Agent Example - Full-featured customer support bot.

This example shows how to use all of Memoric's features for a production AI agent:
- Semantic search for intelligent context retrieval
- Smart summarization for long conversations
- Multi-strategy retrieval (balanced, semantic_heavy, etc.)
- Thread management and conversation continuity
- Importance-based memory prioritization

Perfect for:
- Customer support bots
- Enterprise AI assistants
- Long-running conversations
- Multi-turn dialogues
- Production deployments
"""

import os
from datetime import datetime
from typing import Optional

from memoric.agents.conversation_manager import ConversationManager


class ProductionSupportBot:
    """Production-ready customer support bot with advanced memory."""

    def __init__(self, bot_id: str = "support_bot_v1"):
        """Initialize the support bot."""
        # Optional: Set OpenAI API key for semantic search and summarization
        # os.environ["OPENAI_API_KEY"] = "sk-..."

        self.manager = ConversationManager(
            agent_id=bot_id,
            enable_semantic_search=True,  # Intelligent context retrieval
            enable_summarization=True,     # Compress long conversations
            default_strategy="balanced"    # Balanced retrieval strategy
        )

        self.bot_id = bot_id
        print(f"✅ {bot_id} initialized with advanced memory capabilities")

    def handle_user_message(
        self,
        message: str,
        user_id: str,
        thread_id: str,
        importance: str = "medium",
    ) -> dict:
        """
        Process a user message and get intelligent context for response.

        Args:
            message: User's message
            user_id: User identifier
            thread_id: Conversation thread ID
            importance: Message importance (low, medium, high, critical)

        Returns:
            Dict with context and metadata
        """
        # Save user message with metadata
        self.manager.add_message(
            content=message,
            role="user",
            thread_id=thread_id,
            importance=importance,
            metadata={
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Get intelligent context for AI response
        # Uses hybrid retrieval: semantic + keyword + recency + importance
        context = self.manager.get_context(
            query=message,
            thread_id=thread_id,
            max_tokens=2000,  # Fit in LLM context window
            strategy="semantic_heavy",  # Prioritize meaning over keywords
            include_summary=True,  # Compress old messages
        )

        return {
            "context_text": context["text"],
            "relevant_memories": context["memories"],
            "metadata": context["metadata"],
        }

    def save_assistant_response(
        self,
        response: str,
        thread_id: str,
        importance: str = "medium",
    ) -> None:
        """Save assistant's response to memory."""
        self.manager.add_message(
            content=response,
            role="assistant",
            thread_id=thread_id,
            importance=importance,
        )

    def get_conversation_summary(self, thread_id: str) -> list:
        """Get summarized conversation history."""
        return self.manager.get_thread_history(
            thread_id=thread_id,
            max_messages=20,
            summarize_old=True,  # Compress old parts
        )

    def search_knowledge_base(self, query: str, top_k: int = 5) -> list:
        """Search across all conversations for relevant knowledge."""
        return self.manager.search_across_threads(
            query=query,
            top_k=top_k,
            strategy="semantic_heavy",  # Find by meaning
        )


def demo_production_bot():
    """Demonstrate production bot capabilities."""
    print("🤖 Production Customer Support Bot Demo\n")
    print("=" * 60)

    # Initialize bot
    bot = ProductionSupportBot(bot_id="customer_support_prod")

    # Simulate customer support conversation
    thread_id = f"support_ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    user_id = "customer_12345"

    print(f"\n📞 New support ticket: {thread_id}")
    print(f"👤 Customer: {user_id}\n")

    # Conversation 1: Initial problem
    print("─" * 60)
    print("USER: I can't log into my account, it says 'invalid password'")
    context = bot.handle_user_message(
        message="I can't log into my account, it says 'invalid password'",
        user_id=user_id,
        thread_id=thread_id,
        importance="high",  # Login issues are important
    )
    print(f"\n💭 Bot retrieved {len(context['relevant_memories'])} relevant memories")
    print(f"⏱️  Retrieval took {context['metadata']['retrieval_time_ms']:.2f}ms")

    response = "I'll help you with your login issue. First, let's try resetting your password. Check your email for a reset link."
    bot.save_assistant_response(response, thread_id, importance="high")
    print(f"\nBOT: {response}")

    # Conversation 2: Follow-up
    print("\n" + "─" * 60)
    print("USER: I don't see the email. What email did you send it to?")
    context = bot.handle_user_message(
        message="I don't see the email. What email did you send it to?",
        user_id=user_id,
        thread_id=thread_id,
        importance="medium",
    )
    print(f"\n💭 Retrieved context includes previous messages about login issue")

    response = "The reset email was sent to the address on file. It should arrive within a few minutes. Check your spam folder too."
    bot.save_assistant_response(response, thread_id, importance="medium")
    print(f"\nBOT: {response}")

    # Conversation 3: Resolution
    print("\n" + "─" * 60)
    print("USER: Got it! The password reset worked. Thanks!")
    context = bot.handle_user_message(
        message="Got it! The password reset worked. Thanks!",
        user_id=user_id,
        thread_id=thread_id,
        importance="low",  # Resolution message
    )

    response = "Great! I'm glad we could resolve your login issue. Is there anything else I can help you with?"
    bot.save_assistant_response(response, thread_id, importance="low")
    print(f"\nBOT: {response}")

    # Show conversation summary
    print("\n" + "=" * 60)
    print("📝 Conversation Summary:")
    history = bot.get_conversation_summary(thread_id)
    print(f"Total messages: {len(history)}")
    for msg in history:
        role = msg.get('metadata', {}).get('role', 'unknown')
        content = msg.get('content', '')[:80]
        print(f"  [{role}] {content}...")

    # Demonstrate knowledge base search
    print("\n" + "=" * 60)
    print("🔍 Searching knowledge base for 'password reset':")
    knowledge = bot.search_knowledge_base("password reset", top_k=3)
    print(f"Found {len(knowledge)} relevant memories:")
    for mem in knowledge:
        relevance = mem.get('_hybrid_score', 0)
        content = mem.get('content', '')[:80]
        print(f"  [{relevance:.2f}] {content}...")

    # Show bot statistics
    print("\n" + "=" * 60)
    print("📊 Bot Statistics:")
    stats = bot.manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ Production bot demo complete!")


if __name__ == "__main__":
    # Optional: Set OpenAI API key for semantic search
    # Uncomment if you have an OpenAI key
    # os.environ["OPENAI_API_KEY"] = "sk-..."

    demo_production_bot()
