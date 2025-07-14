#!/bin/bash

# Run tests for TryFi Home Assistant integration

echo "Running TryFi integration tests..."


# Install test requirements
echo "Installing test requirements..."
uv sync --dev

# Run tests with coverage
if [ "$1" == "--coverage" ]; then
    echo "Running tests with coverage..."
    uv run pytest --cov=custom_components.tryfi --cov-report=term-missing --cov-report=html
elif [ "$1" == "--quick" ]; then
    echo "Running quick test run..."
    uv run pytest -x
else
    echo "Running all tests..."
    uv run pytest -v
fi

echo "Tests complete!"