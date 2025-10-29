from __future__ import annotations

from integrations.langchain.memory import MemoricMemory


def main() -> None:
    mem = MemoricMemory(user_id="u_lc", thread_id="support")
    mem.save_context({}, {"response": "Hello, how can I help you?"})
    vars = mem.load_memory_variables({})
    print(vars.get("history"))


if __name__ == "__main__":
    main()
