#!/usr/bin/env python3
"""Entry point — starts the HTTP server on port 8080."""

from app.server import start

if __name__ == "__main__":
    start(port=8080)
