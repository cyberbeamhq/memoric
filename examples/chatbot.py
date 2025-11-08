"""
Simple chatbot with memory
"""

from memoric import Memory

# Initialize memory for chatbot
memory = Memory(user_id="assistant")

def chat(user_message: str, thread_id: str = "default") -> str:
    """
    Simple chatbot function with memory.

    In real usage, replace the mock response with your LLM call.
    """
    # Save user message
    memory.add(
        user_message,
        thread_id=thread_id,
        metadata={"role": "user"}
    )

    # Get relevant context from past conversations
    context = memory.get_context(user_message, thread_id=thread_id)

    # TODO: Replace this with your actual LLM call
    # response = openai.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": context},
    #         {"role": "user", "content": user_message}
    #     ]
    # )

    # For demo purposes:
    response = f"[AI would respond here, using this context:\n{context}]"

    # Save assistant response
    memory.add(
        response,
        thread_id=thread_id,
        metadata={"role": "assistant"}
    )

    return response


# Example usage
if __name__ == "__main__":
    # Conversation 1
    chat("Hi! My name is Alice", thread_id="conv_1")
    chat("I love reading science fiction", thread_id="conv_1")

    # Later conversation...
    response = chat("What do you know about me?", thread_id="conv_1")
    print(response)
    # AI will have context: "My name is Alice", "I love reading science fiction"

    # Check conversation history
    history = memory.get_thread("conv_1")
    print(f"\nFull conversation ({len(history)} messages):")
    for msg in history:
        role = msg.get('metadata', {}).get('role', 'unknown')
        print(f"{role}: {msg['content'][:50]}...")
