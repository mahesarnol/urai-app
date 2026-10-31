"""Titik masuk untuk PyInstaller (Urai App.exe)."""
import multiprocessing
import sys

from urai.app import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
