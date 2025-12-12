#!/bin/sh
set -e

# Set environment variables
export FLASK_APP=wsgi:app
export PYTHONPATH=$PYTHONPATH:./backend
export GEMINI_API_KEY=${GEMINI_API_KEY:-} # Set placeholder if not provided

# Wait for the database to be ready (optional, but good practice)
# Add a database check here if needed in the future

# Run database migrations
echo "Applying database migrations..."
flask db upgrade
echo "Database migrations applied."

# Start the application server
echo "Starting Gunicorn server..."
exec gunicorn -w 4 -b 0.0.0.0:$PORT "wsgi:app"
