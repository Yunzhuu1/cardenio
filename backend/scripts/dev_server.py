"""Development server — run with: python -m scripts.dev_server"""

import uvicorn


def main() -> None:
    uvicorn.run(
        "cardenio.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()