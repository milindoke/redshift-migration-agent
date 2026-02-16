#!/bin/bash
# Setup script for Redshift Migration Tool

set -e

echo "=========================================="
echo "Redshift Migration Tool - Setup"
echo "=========================================="

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install package in development mode
echo ""
echo "Installing redshift-migrate..."
pip install -e ".[dev]"

# Verify installation
echo ""
echo "Verifying installation..."
redshift-migrate --version

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To get started:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Configure AWS credentials:"
echo "     aws configure"
echo ""
echo "  3. Run your first migration:"
echo "     redshift-migrate --help"
echo ""
echo "Documentation:"
echo "  - Quick Start: docs/QUICKSTART.md"
echo "  - Parameter Groups: docs/PARAMETER_GROUPS.md"
echo "  - Scheduled Queries: docs/SCHEDULED_QUERIES.md"
echo ""
