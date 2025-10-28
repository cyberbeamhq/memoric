from __future__ import annotations

import time
from memoric.core.memory_manager import Memoric


def main() -> None:
    m = Memoric()
    while True:
        result = m.run_policies()
        print("Policies run:", result)
        time.sleep(3600)


if __name__ == "__main__":
    main()
