"""
Setup script for Universal Cloud Refactor Agent
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="cloud-refactor-agent",
    version="1.0.0",
    description="Universal Cloud Refactor Agent - Automated migration from AWS/Azure to GCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cloud Refactor Agent Team",
    author_email="",
    url="https://github.com/asmeyatsky/refactor",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
        "llm": [
            "openai>=1.3.0",
            "anthropic>=0.7.0",
        ],
    },
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
    entry_points={
        "console_scripts": [
            "cloud-refactor=main:main",
        ],
    },
)
