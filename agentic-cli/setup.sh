#!/bin/bash
# Setup script for agentic-cli

set -e

echo "🚀 Setting up Agentic CLI..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv installed successfully"
else
    echo "✅ uv is already installed"
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install package in development mode
echo "📥 Installing agentic-cli with dev dependencies..."
uv pip install -e ".[dev]"

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To test the CLI, run:"
echo "  agent --version"
echo "  agent --help"
echo ""
echo "To run integration tests:"
echo "  make integration"
echo ""
echo "For more commands, run:"
echo "  make help"
