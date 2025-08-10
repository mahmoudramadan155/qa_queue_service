from setuptools import setup, find_packages

setup(
    name="qa-api-service",
    version="1.0.0",
    description="AI-powered question-answering API service",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]>=0.24.0",
        "python-multipart==0.0.6",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "sqlalchemy==2.0.23",
        "chromadb==0.4.15",
        "sentence-transformers==2.2.2",
        "openai==1.3.3",
        "PyPDF2==3.0.1",
        "python-dotenv==1.0.0",
        "pydantic==2.5.0",
        "pydantic-settings==2.0.3",
        "elasticsearch>=8.11.0",
        "email-validator>=2.1.0",
        "httpx>=0.25.2",
    ],
    python_requires=">=3.8",
    author="Mahmoud Elshahapy",
    author_email="mahmoudelshahapy97@gmail.com",
    url="https://github.com/yourusername/qa-api-service",
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "mypy>=1.7.1",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
