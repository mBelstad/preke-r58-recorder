# Coolify MCP Server Setup

## Overview

The Coolify MCP (Model Context Protocol) server allows you to manage Coolify deployments directly from Cursor IDE using natural language commands.

## Installation Steps

### 1. Generate Coolify API Token

1. Access your Coolify dashboard at `http://65.109.32.111:8000` (or your configured domain)
2. Log in with your credentials
3. Navigate to **Settings** → **API Tokens**
4. Click **"Create API Token"**
5. Give it a name (e.g., "Cursor MCP")
6. Copy the generated token (you won't see it again!)

### 2. Install MCP Server

The MCP server will be installed automatically by Cursor when you add the configuration.

### 3. Configure Cursor

Add this configuration to your Cursor MCP settings:

**Location**: Cursor Settings → Features → MCP Servers

```json
{
  "mcpServers": {
    "coolify": {
      "command": "npx",
      "args": ["-y", "@pashvc/mcp-server-coolify"],
      "env": {
        "COOLIFY_BASE_URL": "http://65.109.32.111:8000",
        "COOLIFY_TOKEN": "YOUR_API_TOKEN_HERE"
      }
    }
  }
}
```

Replace `YOUR_API_TOKEN_HERE` with the token you generated in step 1.

### 4. Restart Cursor

After adding the configuration, restart Cursor to load the MCP server.

### 5. Test the Connection

Try asking Cursor:
- "List all servers in Coolify"
- "Show me all applications"
- "What services are running?"

## Available Commands

The Coolify MCP server supports:

| Command | Description |
|---------|-------------|
| List servers | View all registered servers |
| List applications | View all deployed applications |
| List services | View all running services |
| Deploy application | Deploy or redeploy an application |
| Get application logs | View application logs |
| Start/Stop/Restart | Control application lifecycle |

## Troubleshooting

### MCP Server Not Loading

1. Check Cursor's MCP logs (Help → Show Logs)
2. Verify the API token is correct
3. Ensure Coolify is accessible from your machine
4. Try running manually: `npx @pashvc/mcp-server-coolify`

### Connection Failed

1. Verify Coolify URL is correct
2. Check if Coolify API is enabled (Settings → API)
3. Ensure no firewall blocking the connection

### Commands Not Working

1. Check API token permissions
2. Verify the resource exists in Coolify
3. Check Coolify logs for errors

## Security Notes

- **Never commit the API token** to Git
- Store the token securely
- Rotate tokens regularly
- Use read-only tokens for viewing operations

## References

- [Coolify MCP Server GitHub](https://github.com/pashvc/mcp-server-coolify)
- [Coolify API Documentation](https://coolify.io/docs/api-reference)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)

## Next Steps

Once MCP is configured, you can:
1. Deploy R58 services via Coolify dashboard
2. Use natural language to manage deployments
3. Monitor application status from Cursor

