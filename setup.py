#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="anthropic-proxy-cli",
    version="1.0.0",
    description="CLI tool for managing Anthropic Proxy servers and configurations",
    author="Kilo Code",
    packages=find_packages(),
    py_modules=["cli.main"],
    entry_points={
        "console_scripts": [
            "anthropic-proxy-cli=cli.main:main",
        ],
    },
    install_requires=[
        "click",
        "pyyaml",
        "requests",
        "rich",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)