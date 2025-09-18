default: run

# Install dependencies
install:
	poetry install

# Start Flask in development mode
dev:
	poetry run flask --debug run --host=0.0.0.0 --port=5000

# Run tests
test:
	poetry run pytest

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +

