#!/usr/bin/env python3
"""Video Audio Denoiser — 启动入口"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import main

if __name__ == "__main__":
    main()
