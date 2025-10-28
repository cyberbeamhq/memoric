"""
LangChain integration for Memoric.

Provides drop-in replacement for LangChain memory modules with Memoric backend.

Usage:
    from memoric.integrations.langchain_adapter import MemoricChatMemory
    from langchain.chains import ConversationChain
    from langchain.llms import OpenAI

    memory = MemoricChatMemory(user_id="user123")
    chain = ConversationChain(llm=OpenAI(), memory=memory)
    chain.run("Hello!")
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from langchain.schema import BaseMemory, AIMessage, HumanMessage, SystemMessage
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Graceful fallback if LangChain not installed
    BaseMemory = object  # type: ignore
    AIMessage = HumanMessage = SystemMessage = None  # type: ignore
    ConversationBufferMemory = None  # type: ignore
    LANGCHAIN_AVAILABLE = False

from ..core.memory_manager import Memoric


class MemoricChatMemory(BaseMemory if LANGCHAIN_AVAILABLE else object):
    """LangChain-compatible memory using Memoric as backend.

    Stores conversation history in Memoric with automatic:
    - Thread-based context isolation
    - Metadata enrichment
    - Policy-driven lifecycle management
    - Topic clustering

    Args:
        user_id: User identifier for memory isolation
        thread_id: Optional thread/conversation identifier
        memoric: Optional Memoric instance (creates new one if None)
        config_path: Optional path to Memoric config
        memory_key: Key to use for memory in chain (default: "history")
        return_messages: Whether to return messages as list or string
        top_k: Number of relevant memories to retrieve (default: 10)
        input_key: Key for input in chain (default: "input")
        output_key: Key for output in chain (default: "output")
    """

    def __init__(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        memoric: Optional[Memoric] = None,
        config_path: Optional[str] = None,
        memory_key: str = "history",
        return_messages: bool = False,
        top_k: int = 10,
        input_key: str = "input",
        output_key: str = "output",
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Please install with: "
                "pip install 'memoric[langchain]' or pip install langchain"
            )

        self.user_id = user_id
        self.thread_id = thread_id or f"langchain_{user_id}"
        self.memoric = memoric or Memoric(config_path=config_path)
        self.memory_key = memory_key
        self.return_messages = return_messages
        self.top_k = top_k
        self.input_key = input_key
        self.output_key = output_key

    @property
    def memory_variables(self) -> List[str]:
        """Return memory variables (required by LangChain)."""
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load relevant memories from Memoric.

        Args:
            inputs: Input dict from chain (may contain query for retrieval)

        Returns:
            Dict with memory_key mapped to conversation history
        """
        # Retrieve relevant memories from thread
        memories = self.memoric.retrieve(
            user_id=self.user_id,
            thread_id=self.thread_id,
            top_k=self.top_k,
            scope="thread",
        )

        if self.return_messages:
            # Convert to LangChain message format
            messages = []
            for mem in memories:
                content = mem.get("content", "")
                role = mem.get("metadata", {}).get("role", "human")

                if role == "ai" or role == "assistant":
                    messages.append(AIMessage(content=content))
                elif role == "system":
                    messages.append(SystemMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))

            return {self.memory_key: messages}
        else:
            # Return as string
            history_str = "\n".join([
                f"{mem.get('metadata', {}).get('role', 'Human')}: {mem.get('content', '')}"
                for mem in memories
            ])
            return {self.memory_key: history_str}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save conversation turn to Memoric.

        Args:
            inputs: Input dict from chain (contains user message)
            outputs: Output dict from chain (contains AI response)
        """
        # Save user input
        user_input = inputs.get(self.input_key, "")
        if user_input:
            self.memoric.save(
                user_id=self.user_id,
                thread_id=self.thread_id,
                content=str(user_input),
                metadata={"role": "human", "type": "message"},
            )

        # Save AI output
        ai_output = outputs.get(self.output_key, "")
        if ai_output:
            self.memoric.save(
                user_id=self.user_id,
                thread_id=self.thread_id,
                content=str(ai_output),
                metadata={"role": "ai", "type": "message"},
            )

    def clear(self) -> None:
        """Clear memory (no-op for Memoric - use policies instead)."""
        # Memoric uses policy-driven cleanup, not manual clearing
        # To "clear" memory, you would:
        # 1. Change thread_id to start fresh conversation
        # 2. Run policies to trim old memories
        # 3. Use tier management to archive memories
        pass


class MemoricConversationBufferMemory(ConversationBufferMemory if LANGCHAIN_AVAILABLE else object):
    """Enhanced ConversationBufferMemory with Memoric backend.

    Drop-in replacement for LangChain's ConversationBufferMemory that:
    - Persists conversation across sessions
    - Applies metadata enrichment
    - Enables policy-driven memory management

    Args:
        user_id: User identifier for memory isolation
        thread_id: Optional thread/conversation identifier
        memoric: Optional Memoric instance
        config_path: Optional path to Memoric config
        **kwargs: Additional arguments passed to ConversationBufferMemory
    """

    def __init__(
        self,
        user_id: str,
        thread_id: Optional[str] = None,
        memoric: Optional[Memoric] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Please install with: "
                "pip install 'memoric[langchain]' or pip install langchain"
            )

        # Initialize base ConversationBufferMemory
        super().__init__(**kwargs)

        # Add Memoric backend
        self.user_id = user_id
        self.thread_id = thread_id or f"langchain_{user_id}"
        self.memoric = memoric or Memoric(config_path=config_path)

        # Load existing conversation from Memoric
        self._load_from_memoric()

    def _load_from_memoric(self) -> None:
        """Load existing conversation from Memoric into buffer."""
        memories = self.memoric.retrieve(
            user_id=self.user_id,
            thread_id=self.thread_id,
            top_k=100,  # Load full conversation
            scope="thread",
        )

        # Convert to LangChain messages
        for mem in memories:
            content = mem.get("content", "")
            role = mem.get("metadata", {}).get("role", "human")

            if role == "ai" or role == "assistant":
                self.chat_memory.add_ai_message(content)
            else:
                self.chat_memory.add_user_message(content)

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save context to both buffer and Memoric."""
        # Save to buffer (in-memory)
        super().save_context(inputs, outputs)

        # Save to Memoric (persistent)
        user_input = inputs.get(self.input_key, "")
        if user_input:
            self.memoric.save(
                user_id=self.user_id,
                thread_id=self.thread_id,
                content=str(user_input),
                metadata={"role": "human", "type": "message"},
            )

        ai_output = outputs.get(self.output_key, "")
        if ai_output:
            self.memoric.save(
                user_id=self.user_id,
                thread_id=self.thread_id,
                content=str(ai_output),
                metadata={"role": "ai", "type": "message"},
            )


def create_langchain_memory(
    user_id: str,
    thread_id: Optional[str] = None,
    memory_type: str = "memoric",
    **kwargs: Any,
) -> BaseMemory:
    """Factory function to create LangChain-compatible memory.

    Args:
        user_id: User identifier
        thread_id: Optional thread identifier
        memory_type: Type of memory ("memoric" or "buffer")
        **kwargs: Additional arguments for memory constructor

    Returns:
        LangChain BaseMemory instance with Memoric backend
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "LangChain is not installed. Please install with: "
            "pip install 'memoric[langchain]' or pip install langchain"
        )

    if memory_type == "memoric":
        return MemoricChatMemory(user_id=user_id, thread_id=thread_id, **kwargs)
    elif memory_type == "buffer":
        return MemoricConversationBufferMemory(user_id=user_id, thread_id=thread_id, **kwargs)
    else:
        raise ValueError(f"Unknown memory_type: {memory_type}. Use 'memoric' or 'buffer'.")
