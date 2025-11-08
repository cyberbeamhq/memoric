"""
Simplest possible example - Memory in 10 lines
"""

from memoric import Memory

# Create memory for your AI agent
memory = Memory(user_id="chatbot")

# Save what user says
memory.add("I love Italian food, especially pizza")
memory.add("My birthday is March 15th")
memory.add("I prefer email over phone calls")

# Search by meaning (not exact keywords)
results = memory.search("What does the user like to eat?")
print(f"Found: {results[0]['content']}")
# Output: "I love Italian food, especially pizza"

# Get context for your AI
context = memory.get_context("User asked about their preferences")
print(context)
