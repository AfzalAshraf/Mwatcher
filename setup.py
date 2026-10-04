#!/usr/bin/env python3
"""
Setup script for Mwatcher
Install with: pip install .
"""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="mwatcher",
    version="1.0.0",
    description="Universal Movie Watcher - Watch movies from any device with just one command",
    author="Afzal Ashraf",
    author_email="afzal@example.com",
    url="https://github.com/AfzalAshraf/Mwatcher",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mwatcher=mwatcher:mwatcher_cli",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Video",
    ],
    keywords="movie stream video player vlc mpv termux stremio",
    project_urls={
        "Bug Reports": "https://github.com/AfzalAshraf/Mwatcher/issues",
        "Source": "https://github.com/AfzalAshraf/Mwatcher",
    },
)
