"""Setup configuration for satdatabrickstest01."""

from setuptools import setup, find_packages

setup(
    name="satdatabrickstest01",
    version="0.1.0",
    description="Databricks DLT pipeline for product analytics",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "dlt>=0.3.0",
        "pyspark>=3.4.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "chispa>=0.9.0",
            "black>=23.0.0",
            "ruff>=0.0.280",
            "mypy>=1.4.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
