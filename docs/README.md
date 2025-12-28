# R58 Documentation

**Last Updated**: December 26, 2025  
**Status**: All information verified and up-to-date

---

## 📚 Quick Links

- **[Interactive Wiki](https://r58-api.itagenten.no/static/wiki.html)** - Searchable documentation with diagrams
- **[Quick Start](operations/QUICK_START.md)** - Get started in 5 minutes
- **[Remote Access](operations/REMOTE_ACCESS.md)** - SSH and web access
- **[API Reference](development/API_REFERENCE.md)** - Complete API documentation

---

## Documentation Structure

### 📦 Product Documentation
*For clients, stakeholders, and decision-makers*

- **[Product Overview](product/PRODUCT_OVERVIEW.md)** - What the R58 does, features, use cases

### 🏗️ Architecture Documentation
*For developers and technical evaluators*

- **[System Architecture](architecture/SYSTEM_ARCHITECTURE.md)** - Component diagrams, data flows
- **[Technology Stack](architecture/TECHNOLOGY_STACK.md)** - Why each technology was chosen
- **[Decisions & Alternatives](architecture/DECISIONS_AND_ALTERNATIVES.md)** - What we tried and rejected

### 🔧 Operations Documentation
*For users and administrators*

- **[Quick Start](operations/QUICK_START.md)** - 5-minute getting started guide
- **[Remote Access](operations/REMOTE_ACCESS.md)** - SSH, FRP tunnel, web interfaces
- **[Troubleshooting](operations/TROUBLESHOOTING.md)** - Common issues and solutions

### 💻 Development Documentation
*For developers and integrators*

- **[Developer Onboarding](development/DEVELOPER_ONBOARDING.md)** - New developer guide
- **[API Reference](development/API_REFERENCE.md)** - Complete API documentation
- **[Configuration](development/CONFIGURATION.md)** - config.yml and mediamtx.yml explained

---

## Interactive Wiki

The best way to explore this documentation is through the **interactive wiki**:

**URL**: https://r58-api.itagenten.no/static/wiki.html

**Features**:
- 🔍 Full-text search
- 📊 Interactive Mermaid diagrams
- 🌓 Dark mode support
- 📱 Mobile responsive
- 🖨️ Print-friendly

---

## Verification Status

All documentation has been verified against the live system:

- ✅ **Services**: Verified running on Dec 26, 2025
- ✅ **Ports**: Confirmed accessible
- ✅ **API Endpoints**: Tested and working
- ✅ **Configuration**: Matches actual config files
- ✅ **Commands**: All tested via SSH

See [VERIFIED_SYSTEM_INFO.md](../VERIFIED_SYSTEM_INFO.md) for complete verification details.

---

## For Different Audiences

### I'm a Client/Stakeholder
Start with:
1. [Product Overview](product/PRODUCT_OVERVIEW.md)
2. [Interactive Wiki](https://r58-api.itagenten.no/static/wiki.html) - "What is R58?" section

### I'm a New Developer
Start with:
1. [Developer Onboarding](development/DEVELOPER_ONBOARDING.md)
2. [System Architecture](architecture/SYSTEM_ARCHITECTURE.md)
3. [Quick Start](operations/QUICK_START.md) - Test the system

### I'm an Administrator/Operator
Start with:
1. [Quick Start](operations/QUICK_START.md)
2. [Remote Access](operations/REMOTE_ACCESS.md)
3. [Troubleshooting](operations/TROUBLESHOOTING.md)

### I'm Integrating with the API
Start with:
1. [API Reference](development/API_REFERENCE.md)
2. [Interactive API Docs](https://r58-api.itagenten.no/docs)
3. [Configuration](development/CONFIGURATION.md)

---

## Additional Resources

### Historical Documentation
- **[docs/archive/](archive/)** - Historical documents (150+ files)
- **[docs/archive-dec26/](archive-dec26/)** - Recent archived docs
- **[CLOUDFLARE_HISTORY.md](CLOUDFLARE_HISTORY.md)** - Why we don't use Cloudflare

### System Information
- **[VERIFIED_SYSTEM_INFO.md](../VERIFIED_SYSTEM_INFO.md)** - Complete verified system details
- **[config.yml](../config.yml)** - Application configuration
- **[mediamtx.yml](../mediamtx.yml)** - Streaming server configuration

### Scripts
- **[connect-r58-frp.sh](../connect-r58-frp.sh)** - SSH to R58
- **[deploy-simple.sh](../deploy-simple.sh)** - Deploy code

---

## Contributing to Documentation

### Updating Documentation

1. **Verify Information**: Test all commands and configurations
2. **Update Source**: Edit markdown files in appropriate folder
3. **Update Wiki**: Update corresponding section in `src/static/js/wiki-content*.js`
4. **Test**: Verify wiki renders correctly
5. **Deploy**: Use `./deploy-simple.sh`

### Documentation Standards

- **Date all updates**: Include "Last Updated" date
- **Verify everything**: Test all commands before documenting
- **Use examples**: Include real, working examples
- **Be specific**: Use actual values, not placeholders
- **Cross-reference**: Link to related documentation

---

## Getting Help

### Support Channels
- **Wiki Search**: Use search box in interactive wiki
- **Troubleshooting Guide**: [operations/TROUBLESHOOTING.md](operations/TROUBLESHOOTING.md)
- **System Logs**: `./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"`

### Reporting Issues
1. Check [Troubleshooting Guide](operations/TROUBLESHOOTING.md)
2. Search wiki for error messages
3. Collect logs: `./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 100"`
4. Document steps to reproduce

---

## Documentation Changelog

### December 26, 2025
- ✅ Complete documentation restructure
- ✅ Interactive wiki created
- ✅ All information verified
- ✅ 331 markdown files organized
- ✅ Mermaid diagrams added
- ✅ Full-text search implemented

### December 25, 2025
- Cloudflare code removed
- FRP documentation updated
- Architecture diagrams revised

### December 24, 2025
- Migration to FRP documented
- Remote access guide updated

---

**The R58 documentation is comprehensive, verified, and actively maintained.**

For the best experience, visit the **[Interactive Wiki](https://r58-api.itagenten.no/static/wiki.html)** 🚀

