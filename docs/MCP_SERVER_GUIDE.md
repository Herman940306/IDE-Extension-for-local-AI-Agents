# MCP Server Integration Guide

**Project:** AI Agents Integration System for VS Code  
**Creator:** Herman Swanepoel  
**Date:** 2025-01-13

## Overview

This project integrates the **AURA-DEV OMNIDEV GODMODE** MCP (Model Context Protocol) server, providing advanced AI capabilities for development, architecture, and automation tasks.

## Quick Start

### 1. Start the MCP Server

```powershell
.\scripts\start-mcp-server.ps1
```

This will:
- Check if the server is already running
- Start the MCP server in the background
- Create log files in the `logs/` directory
- Save process information for management

### 2. Test the Connection

```powershell
.\scripts\test-mcp-connection.ps1
```

This will:
- Verify the server process is running
- Check server logs for errors
- Display recent server activity

### 3. Stop the Server

```powershell
.\scripts\stop-mcp-server.ps1
```

## MCP Server Capabilities

The ai-assistant-ml MCP server provides:

### 🧠 ML & AI Features
- **Emotion Detection** - Analyze sentiment and emotional context from text
- **Predictive Analytics** - AI predictions and automation suggestions
- **Learning Insights** - Track learning progress and AI effectiveness
- **Reasoning Engine** - Complex multi-step command analysis
- **Personality Profiles** - Adaptive AI personality configuration

### 🏗️ Architecture & Design
- **System Design** - Architecture analysis and recommendations
- **API Design** - RESTful and GraphQL API planning
- **Multi-Cloud Architecture** - Cloud-agnostic design patterns

### ⚙️ DevOps & Infrastructure
- **Infrastructure as Code** - Terraform, Ansible, CloudFormation
- **CI/CD Orchestration** - Pipeline automation and optimization
- **Observability** - Monitoring, logging, and alerting setup
- **Resilience** - High availability and disaster recovery

### 🔒 Security & Compliance
- **DevSecOps** - Security-first development practices
- **Compliance Validation** - GDPR, SOC2, HIPAA checks
- **Vulnerability Mitigation** - Security scanning and remediation
- **Identity Management** - IAM, RBAC, Zero Trust

### 📚 Documentation
- **Documentation Generation** - Auto-generate docs from code
- **Diagram Generation** - Architecture and flow diagrams
- **API Specs** - OpenAPI/Swagger documentation
- **Runbooks** - Operational procedures

## Configuration

The MCP server is configured in `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "ai-assistant-ml": {
      "command": "C:\\AI\\_Assistant\\_HomeServer\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\AI\\_Assistant\\_HomeServer\\mcp_server\\ai_assistant_ml_server.py"
      ],
      "env": {
        "AURA_DEV_MODE": "GODMODE",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "disabled": false,
      "autoApprove": [
        "ml_analyze_emotion",
        "ml_get_predictions",
        "ml_get_learning_insights",
        "ml_analyze_reasoning",
        "system_design",
        "architecture_analysis",
        "devops_orchestration",
        "security_audit",
        "ai_integration",
        "documentation_generation",
        "ml_pipeline_automation",
        "infrastructure_as_code",
        "compliance_validation"
      ]
    }
  }
}
```

## Using MCP Tools in Kiro

Once the server is running, Kiro can automatically use MCP tools:

### Example: Emotion Analysis
```
Analyze the emotion in this text: "I'm so excited about this new feature!"
```

### Example: System Design
```
Design a scalable architecture for a real-time chat application
```

### Example: Security Audit
```
Review this code for security vulnerabilities
```

### Example: Documentation
```
Generate API documentation for this service
```

## Troubleshooting

### Server Won't Start

1. Check if Python path is correct in `scripts/start-mcp-server.ps1`
2. Verify the MCP server file exists at the specified path
3. Check logs in `logs/mcp-server-error.log`

### Connection Issues

1. Ensure the server is running: `.\scripts\test-mcp-connection.ps1`
2. Restart Kiro to reconnect to the MCP server
3. Check `.kiro/settings/mcp.json` configuration

### Server Already Running

If you see "MCP server is already running":
- Choose 'y' to restart it
- Or use `.\scripts\stop-mcp-server.ps1` first

## Log Files

All logs are stored in the `logs/` directory:

- `mcp-server-output.log` - Server output and activity
- `mcp-server-error.log` - Error messages and warnings
- `mcp-server-process.json` - Process information (PID, start time)

### View Live Logs

```powershell
Get-Content logs\mcp-server-output.log -Wait
```

## Integration with Kiro

The MCP server is automatically integrated with Kiro through:

1. **Workspace Configuration** - `.kiro/settings/workspace.json`
2. **MCP Configuration** - `.kiro/settings/mcp.json`
3. **Steering Rules** - `.kiro/steering/` directory

Kiro will automatically use MCP tools when appropriate for:
- Architecture decisions
- Code analysis
- Security reviews
- Documentation generation
- DevOps automation

## Advanced Usage

### Custom MCP Tools

To add custom MCP tools, edit the server configuration and add them to the `autoApprove` list in `mcp.json`.

### Environment Variables

Customize server behavior with environment variables in `mcp.json`:

- `AURA_DEV_MODE` - Set to "GODMODE" for full capabilities
- `FASTMCP_LOG_LEVEL` - Control logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Best Practices

1. **Always start the MCP server** before working with Kiro
2. **Check logs regularly** for errors or warnings
3. **Restart the server** after configuration changes
4. **Stop the server** when not in use to free resources
5. **Keep the server updated** with the latest features

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review the configuration in `.kiro/settings/mcp.json`
3. Restart the server and test connection
4. Contact Herman Swanepoel for advanced support

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-13  
**Project Creator:** Herman Swanepoel
