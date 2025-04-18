from setuptools import setup, find_packages

setup(
    name="crawler",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.95.0",
        "openai>=1.0.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.28.0",
        "crawl4ai>=0.1.0", 
        "python-dotenv>=1.0.0",
        "uvicorn>=0.21.0",
        "asyncio>=3.4.3",
    ],
    author="Abhishek Shetty",
    author_email="ashetty21@berkeley.edu",
    description="An AI-powered web crawler for RAG systems",
    keywords="web crawler, ai, rag",
    url="https://github.com/ab-shetty/Crawler",
    classifiers=[
        "Development Status :: Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.9",
)