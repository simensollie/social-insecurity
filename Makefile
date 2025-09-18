default: run

# Install dependencies
install:
	poetry install

# Update dependencies
update:
	poetry update

# Start application
run:
	peotry run flask run

# Start application in development mode and serving to NAT
dev:
	poetry run flask --debug run --host=0.0.0.0 --port=5000

# Reset application back to initial state (delete instance/ dir)
reset:
	poetry run flask reset

# Run tests
test:
	poetry run pytest

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +

