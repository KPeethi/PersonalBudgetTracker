#!/usr/bin/env python3
"""
Helper script to run the application on port 5001
"""

from main import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)