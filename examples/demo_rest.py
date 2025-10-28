from __future__ import annotations

import uvicorn
from memoric.api.server import create_app


def main() -> None:
    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
