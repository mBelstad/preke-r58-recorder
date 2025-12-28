#!/bin/bash
# Generate TypeScript client from OpenAPI schema

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Generating OpenAPI schema..."

cd "$PROJECT_ROOT/packages/backend"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Generate OpenAPI schema
python -c "
import json
import sys
sys.path.insert(0, '.')
from r58_api.main import app

schema = app.openapi()
output_path = '../../openapi/openapi.json'

import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(schema, f, indent=2)

print(f'OpenAPI schema written to {output_path}')
"

echo "Generating TypeScript client..."

cd "$PROJECT_ROOT/packages/frontend"

# Generate TypeScript client
npx openapi-typescript-codegen \
    --input ../../openapi/openapi.json \
    --output src/api \
    --client fetch \
    --useOptions

echo "TypeScript client generated successfully!"
echo "Files written to: packages/frontend/src/api/"

