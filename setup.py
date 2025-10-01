from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="reachgenie",
    version="0.1.0",
    author="Ali Shaheen",
    author_email="ashaheen@workhub.ai",
    description="AI-powered multi-channel sales automation platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alinaqi/reachgenie",
    project_urls={
        "Bug Tracker": "https://github.com/alinaqi/reachgenie/issues",
        "Documentation": "https://github.com/alinaqi/reachgenie#readme",
        "Source Code": "https://github.com/alinaqi/reachgenie",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Communications :: Email",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "reachgenie=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": [
            "web/*.png",
            "web/*.html",
            "templates/*.py",
            "prompts/*.py",
        ],
    },
    keywords="ai sales automation email phone linkedin sdr outbound campaigns",
    license="AGPL-3.0",
)
