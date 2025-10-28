from pathlib import Path
from setuptools import find_packages, setup

ROOT = Path(__file__).parent

readme_path = ROOT / "README.md"
long_description = (
    readme_path.read_text(encoding="utf-8")
    if readme_path.exists()
    else "Memoric: Deterministic, policy-driven memory management for AI agents."
)

requirements_path = ROOT / "requirements.txt"
install_requires = (
    [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if requirements_path.exists()
    else []
)

setup(
    name="memoric",
    version="0.0.1",
    description="Deterministic, policy-driven memory management for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Muthanna Alfaris",
    url="https://github.com/cyberbeamhq/memoric",
    license="Apache-2.0",
    packages=find_packages(exclude=("tests", "examples")),
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=install_requires,
    extras_require={
        "dev": ["pytest", "pytest-cov", "black", "flake8", "mypy", "build"],
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
            "memoric=memoric_cli:main",
        ]
    },    
)


