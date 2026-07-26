#!/usr/bin/env bash
# build.sh
set -o errexit

# Dependencies are usually installed by Railway automatically, but it's safe to keep.
pip install -r requirements.txt

# We ONLY process static files during build. No database access!
python manage.py collectstatic --no-input
