# Heretto Deploy MCP Server

A Model Context Protocol (MCP) server that provides access to the [Heretto Deploy API](https://help.heretto.com/en/heretto-deploy-api/deploy-api-overview). This allows AI assistants like Claude Desktop to interact with your Heretto deployments.

## Features

- Search deployment content
- Get deployment information and structure
- Retrieve content by path or ID
- Access HTML strings and translations
- Fetch OpenAPI specifications
- **Automatic URL generation**: When `HERETTO_PORTAL_BASE_URL` is configured, the server automatically adds `portal_url` fields to any content with paths, making it easy for Claude to provide direct links to your documentation

## Installation

### Option 1: Install from source

```bash
git clone https://github.com/yourusername/heretto-deploy-mcp.git
cd heretto-deploy-mcp
python -m pip install -e .
```

### Option 2: Install with uvx (coming soon)

```bash
uvx heretto-deploy-mcp
```

## Configuration

### 1. Get your Heretto Deploy API token

Obtain a Deploy API token from your Heretto account.

### 2. Set up environment

Create a `.env` file in your project root:

```bash
HERETTO_DEPLOY_TOKEN=your-token-here

# Optional but recommended - set defaults
HERETTO_DEFAULT_ORG_ID=your-org-id
HERETTO_DEFAULT_DEPLOYMENT_ID=your-deployment-id

# Optional - portal URL for generating links
HERETTO_PORTAL_BASE_URL=https://your-portal.heretto.com

# Optional - use EU endpoint
# HERETTO_API_BASE_URL=https://deploy-eu.heretto.com/v3
```

Or set them as environment variables:

```bash
export HERETTO_DEPLOY_TOKEN="your-token-here"
export HERETTO_DEFAULT_ORG_ID="your-org-id"
export HERETTO_DEFAULT_DEPLOYMENT_ID="your-deployment-id"
export HERETTO_PORTAL_BASE_URL="https://your-portal.heretto.com"
```

### 3. Configure Claude Desktop

Add the server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "heretto-deploy": {
      "command": "python",
      "args": ["-m", "heretto_mcp.server"],
      "env": {
        "HERETTO_DEPLOY_TOKEN": "your-token-here",
        "HERETTO_DEFAULT_ORG_ID": "your-org-id",
        "HERETTO_DEFAULT_DEPLOYMENT_ID": "your-deployment-id",
        "HERETTO_PORTAL_BASE_URL": "https://your-portal.heretto.com"
      }
    }
  }
}
```

Or if installed globally:

```json
{
  "mcpServers": {
    "heretto-deploy": {
      "command": "heretto-deploy-mcp",
      "env": {
        "HERETTO_DEPLOY_TOKEN": "your-token-here"
      }
    }
  }
}
```

## Usage

Once configured, you can ask Claude Desktop to:

**With defaults configured:**
- "Search for 'installation guide' in Heretto" (uses default org/deployment)
- "Get the deployment structure" (uses defaults)
- "Show me the content at path '/guides/getting-started'"

**When portal URL is configured:**
- Claude will automatically receive clickable links for any content with paths
- Search results will include `portal_url` fields
- Content responses will include direct links to your documentation

**Overriding defaults:**
- "Search for 'API docs' in organization 'other-org' deployment 'api-docs'"
- "Get info for deployment 'staging' in organization 'test-org'"

**Without defaults (must specify both):**
- "Search for 'installation guide' in organization 'my-org' deployment 'my-docs'"
- "Get the structure of deployment 'my-docs' in organization 'my-org'"

## Available Tools

The MCP server provides these tools:

### `search_deployment`
Search for content within a deployment.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID
- `query` (required): Search query string

### `get_deployment_info`
Get metadata about a deployment.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID

### `get_deployment_structure`
Get the navigation structure of a deployment.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID

### `get_content`
Retrieve specific content by path or ID.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID
- `for_path` (optional): Content path
- `for_id` (optional): Content ID

### `get_html_strings`
Get HTML strings/translations for a deployment.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID
- `locale` (optional): Locale code (default: "en")

### `get_open_api_spec`
Retrieve an OpenAPI specification from a deployment.

Parameters:
- `organization_id` (optional if default set): Your organization ID
- `deployment_id` (optional if default set): The deployment ID
- `specification_id` (required): The specification ID

### `generate_portal_urls`
Generate portal URLs for given paths. Useful when automatic URL injection isn't working as expected.

Parameters:
- `paths` (required): Array of paths to generate URLs for

Returns URLs in the format: `{base_url}{path}`

## Development

### Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m heretto_mcp.server
```

### Testing with MCP Inspector

You can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to test the server:

```bash
npx @modelcontextprotocol/inspector python -m heretto_mcp.server
```

## Troubleshooting

1. **"HERETTO_DEPLOY_TOKEN not set" warning**: Make sure you've set the environment variable or created a `.env` file
2. **Connection errors**: Verify your token is valid and you have internet connectivity
3. **Tool not found**: Restart Claude Desktop after updating the configuration
4. **URLs not working**: Make sure your `HERETTO_PORTAL_BASE_URL` is correct and doesn't include a trailing slash. The server will append paths directly (e.g., `https://docs.example.com` + `/guide/intro` = `https://docs.example.com/guide/intro`)

## License

MIT