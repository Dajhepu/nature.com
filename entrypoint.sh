#!/bin/sh

# This script runs database migrations and then starts the Gunicorn server.
# It's used as the entrypoint for the Docker container in production.

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
echo "Applying database migrations..."
flask db upgrade -d migrations
echo "Database migrations applied successfully."

# Start the Gunicorn server
echo "Starting Gunicorn server..."
exec gunicorn -w 4 -b "0.0.0.0:$PORT" wsgi:app
