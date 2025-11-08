"""
Production example with Pinecone (still simple!)
"""

from memoric import Memory
import os

# For production: use Pinecone for vector storage
memory = Memory(
    user_id="customer_support_bot",
    vector_store="pinecone",
    vector_store_config={
        "api_key": os.environ.get("PINECONE_API_KEY"),
        "environment": "us-east-1",
        "index_name": "customer-memories",
        "dimension": 1536,  # OpenAI ada-002
    }
)

# Save customer interactions
memory.add(
    "Customer reported login issue on mobile app",
    thread_id="ticket_12345",
    importance="high"
)

memory.add(
    "Customer mentioned they use Android version",
    thread_id="ticket_12345",
    importance="medium"
)

# Later, when customer comes back...
context = memory.get_context(
    "Customer is asking about their ticket",
    thread_id="ticket_12345"
)

print(context)
# AI now has full context of previous interaction!

# Get stats
stats = memory.stats()
print(f"Total memories: {stats['total_memories']}")
print(f"Using: {stats['vector_store']}")
