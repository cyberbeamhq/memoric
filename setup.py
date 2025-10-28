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
    license="MIT",
    packages=find_packages(exclude=("tests", "examples")),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=install_requires,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
    ],
    project_urls={
        "Source": "https://github.com/cyberbeamhq/memoric",
        "Tracker": "https://github.com/cyberbeamhq/memoric/issues",
    },
)


