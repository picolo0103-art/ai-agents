#!/bin/bash
cd "$(dirname "$0")"
/usr/bin/python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
