#!/usr/bin/env python3
"""Setup script for bangladeshi-parcel-tracker package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="bangladeshi-parcel-tracker",
    version="0.1.0",
    author="Minhaz",
    author_email="your.email@example.com",
    description="A Python package for tracking parcels from Bangladeshi courier services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mdminhazulhaque/bangladeshi-parcel-tracker",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "bangladeshi-parcel-tracker=bangladeshi_parcel_tracker.cli:main",
        ],
    },
    keywords="bangladesh parcel tracking courier redx steadfast pathao rokomari",
    project_urls={
        "Bug Reports": "https://github.com/mdminhazulhaque/bangladeshi-parcel-tracker/issues",
        "Source": "https://github.com/mdminhazulhaque/bangladeshi-parcel-tracker",
    },
)
