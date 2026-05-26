"""
SkinMaker 安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="skinmaker",
    version="1.0.0",
    author="SkinMaker Team",
    description="Python 皮肤制作工具 - 完整的架构重构",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/skinmaker",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=9.0.0",
        "numpy>=1.21.0",
        "scipy>=1.7.0",
    ],
    entry_points={
        "console_scripts": [
            "skinmaker=src.cli:main",
        ],
    },
)
