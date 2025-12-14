"""
DubSync - Szinkronfordítói Editor
Setup configuration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dubsync",
    version="1.0.0",
    author="Levente Kulacsy",
    author_email="levi0725gamer@gmail.com",
    description="Professzionális szinkronfordítói editor Windows-ra",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Levi0725/DubSync",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
        "Natural Language :: Hungarian",
    ],
    python_requires=">=3.10",
    install_requires=[
        "PySide6>=6.6.0",
        "reportlab>=4.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dubsync=dubsync.main:main",
        ],
        "gui_scripts": [
            "dubsync-gui=dubsync.main:main",
        ],
    },
)
