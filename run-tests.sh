#!/bin/bash

# Run tests for TryFi Home Assistant integration

echo "Running TryFi integration tests..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test requirements
echo "Installing test requirements..."
pip install -r requirements_test.txt -q

# Run tests with coverage
if [ "$1" == "--coverage" ]; then
    echo "Running tests with coverage..."
    pytest --cov=custom_components.tryfi --cov-report=term-missing --cov-report=html
elif [ "$1" == "--quick" ]; then
    echo "Running quick test run..."
    pytest -x
else
    echo "Running all tests..."
    pytest -v
fi

# Deactivate virtual environment
deactivate

echo "Tests complete!"