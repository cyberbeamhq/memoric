"""
Minimal AI Agent Example - Get started in 5 lines of code.

This is the absolute simplest way to use Memoric for an AI agent.
No configuration files, no setup, just import and go.

Perfect for:
- Quick prototyping
- Learning how Memoric works
- Simple chatbots
- Testing ideas
"""

from memoric.agents.conversation_manager import ConversationManager

# That's it! You're ready to build an AI agent with memory.


def simple_chatbot_demo():
    """Demonstrate a simple chatbot with memory."""

    # Initialize conversation manager for your agent
    manager = ConversationManager(agent_id="my_chatbot")

    print("🤖 Simple Chatbot with Memoric Memory\n")

    # Simulate a conversation
    conversations = [
        ("user", "Hi, my name is Alice and I love Python programming."),
        ("assistant", "Nice to meet you, Alice! Python is great. What do you like about it?"),
        ("user", "I love how clean and readable it is."),
        ("assistant", "I agree! Python's readability is one of its best features."),
        ("user", "What was my name again?"),  # Test memory recall
    ]

    thread_id = "conv_001"

    for role, message in conversations:
        # Save messages
        manager.add_message(
            content=message,
            role=role,
            thread_id=thread_id
        )

        # If it's a user message, get context for assistant response
        if role == "user":
            print(f"User: {message}")

            # Get relevant context
            context = manager.get_context(
                query=message,
                thread_id=thread_id,
                max_tokens=1000
            )

            print(f"\n📝 Retrieved {context['metadata']['total_memories']} relevant memories")
            print(f"💭 Context preview:\n{context['text'][:200]}...\n")

        else:
            print(f"Assistant: {message}\n")

    # Demonstrate cross-conversation search
    print("\n🔍 Searching across all conversations:")
    results = manager.search_across_threads(
        query="What does the user like?",
        top_k=3
    )

    print(f"Found {len(results)} relevant memories:")
    for mem in results:
        print(f"  - {mem['content']}")

    # Show statistics
    print("\n📊 Agent Statistics:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    simple_chatbot_demo()
