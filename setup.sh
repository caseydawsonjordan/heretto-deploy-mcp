# Install in development mode
pip install -e .

# Create .env file
cp .env.example .env
# Edit .env and add your token

# Test the server
python -m heretto_mcp.server