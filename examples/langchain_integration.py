"""
LangChain Integration Example

Demonstrates how to use Memoric as a memory backend for LangChain.

Prerequisites:
    pip install langchain openai
"""

from memoric.integrations.langchain_adapter import MemoricChatMemory, create_langchain_memory


def example_basic_memory():
    """Example 1: Basic LangChain memory with Memoric backend."""
    print("=== Example 1: Basic Memoric Memory ===\n")

    try:
        from langchain.chains import ConversationChain
        from langchain.llms import OpenAI
    except ImportError:
        print("Error: LangChain not installed. Install with: pip install langchain openai")
        return

    # Create Memoric-backed memory
    memory = MemoricChatMemory(
        user_id="langchain_user_1",
        thread_id="conversation_1",
        top_k=5,  # Retrieve last 5 memories
        return_messages=False,  # Return as string
    )

    # Create LangChain conversation chain
    llm = OpenAI(temperature=0.7)
    chain = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=True,
    )

    # Have a conversation
    print("Starting conversation with LangChain + Memoric...\n")

    # These will be saved to Memoric and retrieved in subsequent turns
    response1 = chain.run("My name is Alice and I love Python programming.")
    print(f"AI: {response1}\n")

    response2 = chain.run("What's my name and what do I love?")
    print(f"AI: {response2}\n")

    print("Conversation memories are now stored in Memoric!")
    print("They can be retrieved, filtered, and managed using Memoric policies.\n")


def example_persistent_memory():
    """Example 2: Persistent conversation across sessions."""
    print("=== Example 2: Persistent Conversation ===\n")

    try:
        from langchain.chains import ConversationChain
        from langchain.llms import OpenAI
    except ImportError:
        print("Error: LangChain not installed")
        return

    # Same user_id and thread_id will load previous conversation
    memory = MemoricChatMemory(
        user_id="langchain_user_1",
        thread_id="conversation_1",
        top_k=10,
    )

    llm = OpenAI(temperature=0.7)
    chain = ConversationChain(llm=llm, memory=memory)

    print("Loading previous conversation from Memoric...")
    print("All past context is automatically retrieved!\n")

    # Continue the conversation from where we left off
    response = chain.run("Can you remind me what we talked about?")
    print(f"AI: {response}\n")


def example_with_metadata_filtering():
    """Example 3: Retrieve specific memories using metadata filters."""
    print("=== Example 3: Metadata Filtering ===\n")

    from memoric import Memoric

    # Use Memoric directly for advanced features
    mem = Memoric()

    # Save memories with rich metadata
    mem.save(
        user_id="langchain_user_1",
        thread_id="conversation_1",
        content="I need help with Python decorators",
        metadata={"topic": "python", "difficulty": "intermediate"},
    )

    mem.save(
        user_id="langchain_user_1",
        thread_id="conversation_1",
        content="Can you explain async/await in Python?",
        metadata={"topic": "python", "difficulty": "advanced"},
    )

    # Retrieve only Python-related memories
    python_memories = mem.retrieve(
        user_id="langchain_user_1",
        metadata_filter={"topic": "python"},
        top_k=10,
    )

    print(f"Found {len(python_memories)} Python-related memories:")
    for m in python_memories:
        print(f"  - {m['content']}")
        print(f"    Difficulty: {m['metadata'].get('difficulty')}\n")


def example_multi_user():
    """Example 4: Multi-user conversations with user isolation."""
    print("=== Example 4: Multi-User Memory ===\n")

    try:
        from langchain.chains import ConversationChain
        from langchain.llms import OpenAI
    except ImportError:
        print("Error: LangChain not installed")
        return

    # User 1's conversation
    memory_user1 = MemoricChatMemory(
        user_id="alice",
        thread_id="chat_123",
        top_k=5,
    )

    # User 2's conversation (completely isolated)
    memory_user2 = MemoricChatMemory(
        user_id="bob",
        thread_id="chat_456",
        top_k=5,
    )

    llm = OpenAI(temperature=0.7)

    # Alice's chain
    chain_alice = ConversationChain(llm=llm, memory=memory_user1)
    print("Alice: My favorite color is blue.")
    response = chain_alice.run("My favorite color is blue.")
    print(f"AI: {response}\n")

    # Bob's chain (won't know about Alice)
    chain_bob = ConversationChain(llm=llm, memory=memory_user2)
    print("Bob: My favorite color is red.")
    response = chain_bob.run("My favorite color is red.")
    print(f"AI: {response}\n")

    print("Each user's memories are isolated in Memoric!")


def main():
    print("=" * 60)
    print("  Memoric + LangChain Integration Examples")
    print("=" * 60 + "\n")

    try:
        import langchain

        print(f"LangChain version: {langchain.__version__}\n")

        example_basic_memory()
        print("\n" + "-" * 60 + "\n")

        example_with_metadata_filtering()
        print("\n" + "-" * 60 + "\n")

        example_multi_user()

        print("\n" + "=" * 60)
        print("  All examples complete!")
        print("=" * 60)

    except ImportError:
        print("LangChain is not installed.")
        print("Install with: pip install langchain openai")
        print("\nYou can still use Memoric without LangChain!")


if __name__ == "__main__":
    main()
