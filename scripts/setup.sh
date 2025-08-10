#!/bin/bash

# Setup script for AI Question-Answering Service
set -e

echo "🚀 Setting up AI Question-Answering Service..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static
mkdir -p chroma_db
mkdir -p data
mkdir -p tests

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your configuration!"
else
    echo "✅ .env file already exists"
fi

# Run database migrations
echo "🗄️  Creating database tables..."
python -c "
from app.database.connection import engine
from app.database.models import Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully!')
"

# Run tests
echo "🧪 Running tests..."
python -m pytest tests/ -v

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file with your OpenAI API key (optional)"
echo "2. Run the server: python -m uvicorn app.main:app --reload"
echo "3. Visit http://localhost:8000 in your browser"
echo ""
echo "🐳 Or use Docker:"
echo "docker-compose up --build"