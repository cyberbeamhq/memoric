from pathlib import Path
from setuptools import find_packages, setup

ROOT = Path(__file__).parent

readme_path = ROOT / "README.md"
long_description = (
    readme_path.read_text(encoding="utf-8")
    if readme_path.exists()
    else "Memoric: Deterministic, policy-driven memory management for AI agents."
)

# Core dependencies (matching pyproject.toml)
install_requires = [
    "pyyaml>=6.0.1",
    "pydantic>=2.8.0",
    "click>=8.1.7",
    "rich>=13.7.1",
    "sqlalchemy>=2.0",
    "fastapi>=0.112.0",
    "uvicorn>=0.30.0",
]

setup(
    name="memoric",
    version="0.1.0",
    description="Deterministic, policy-driven memory management for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Muthanna Alfaris",
    url="https://github.com/cyberbeamhq/memoric",
    license="Apache-2.0",
    packages=find_packages(exclude=("tests", "examples")),
    include_package_data=True,
    package_data={
        "memoric": ["config/*.yaml", "py.typed"],
    },
    python_requires=">=3.9",
    install_requires=install_requires,
    extras_require={
        "llm": ["openai>=1.0.0"],
        "metrics": ["prometheus-client>=0.19.0"],
        "dev": ["pytest", "pytest-cov", "black", "flake8", "mypy", "build"],
        "all": [
            "openai>=1.0.0",
            "prometheus-client>=0.19.0",
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
            "build",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries",
    ],
    project_urls={
        "Source": "https://github.com/cyberbeamhq/memoric",
        "Tracker": "https://github.com/cyberbeamhq/memoric/issues",
    },
    entry_points={
        "console_scripts": [
            "memoric=memoric.cli:main",
        ]
    },
)
