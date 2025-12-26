# R58 Documentation Maintenance Checklist
**Created**: December 26, 2025  
**Purpose**: Prevent documentation gaps like the VDO.ninja incident

---

## The Problem We're Solving

**What Happened**:
- VDO.ninja was running in production
- Wiki didn't mention it at all
- User discovered it and asked: "Dont we have vdo.ninja running locally?"
- We had to add it retroactively

**Root Cause**:
- No systematic process for documenting new components
- Assumed "obvious" services didn't need documentation
- No regular audits

**Solution**: This checklist

---

## When to Use This Checklist

Use this checklist whenever you:
- ✅ Add a new service
- ✅ Install new software
- ✅ Create new configuration files
- ✅ Add new directories to /opt/
- ✅ Modify system architecture
- ✅ Deploy new features

**Rule**: If it runs on R58, it must be documented.

---

## New Service Checklist

When adding a new systemd service:

### 1. Service Documentation
- [ ] Service name and purpose documented
- [ ] Port(s) documented (if applicable)
- [ ] User/permissions documented
- [ ] Dependencies documented
- [ ] Configuration file location documented
- [ ] Log location documented

### 2. Wiki Updates
- [ ] Added to "System Services" section
- [ ] Added to relevant architecture diagrams
- [ ] Added to port mapping table
- [ ] Added to troubleshooting (if needed)
- [ ] Added to navigation menu

### 3. Verification
- [ ] Service appears in component inventory
- [ ] Service appears in wiki search results
- [ ] Service file location documented
- [ ] Restart/management commands documented

### Example Entry
```markdown
### my-new-service.service

**Purpose**: [What it does]

**Configuration**:
- Code: /opt/my-service/
- User: [user]
- Port: [port]
- Config: /opt/my-service/config.yml

**Management**:
\`\`\`bash
sudo systemctl status my-new-service
sudo systemctl restart my-new-service
sudo journalctl -u my-new-service -f
\`\`\`
```

---

## New Software Checklist

When installing new software (e.g., VDO.ninja, raspberry.ninja):

### 1. Software Documentation
- [ ] Name and version documented
- [ ] Installation location documented (/opt/...)
- [ ] Purpose and functionality documented
- [ ] Source (git repo, package, custom) documented
- [ ] Configuration files documented
- [ ] Dependencies documented

### 2. Wiki Updates
- [ ] Added to "Directory Structure" section
- [ ] Added to "Components" section
- [ ] Added to "Technology Stack" (if major component)
- [ ] Version information added
- [ ] Custom modifications noted (if any)

### 3. Verification
- [ ] Appears in directory map
- [ ] Source/origin clearly stated
- [ ] Version clearly stated
- [ ] Relationship to other components explained

### Example Entry
```markdown
### /opt/my-software

**Purpose**: [What it does]

**Source**: https://github.com/user/repo

**Version**: v1.2.3 (Git commit abc123)

**Type**: Third-party / Custom / Vendor

**Configuration**: /opt/my-software/config.json

**Used By**: [which services use it]
```

---

## New Configuration File Checklist

When creating new configuration files:

### 1. Configuration Documentation
- [ ] File path documented
- [ ] Purpose documented
- [ ] Format documented (YAML/TOML/JSON/etc.)
- [ ] Key settings explained
- [ ] Default values documented
- [ ] Environment variables documented

### 2. Wiki Updates
- [ ] Added to "Configuration Files" section
- [ ] Key settings explained
- [ ] Example configuration shown
- [ ] Reload/restart procedure documented

### Example Entry
```markdown
### /opt/my-service/config.yml

**Purpose**: Configuration for my-service

**Key Settings**:
- `port`: Service port (default: 8080)
- `log_level`: Logging verbosity (info/debug/error)
- `enabled`: Enable/disable service

**Reload Configuration**:
\`\`\`bash
sudo systemctl reload my-service
\`\`\`
```

---

## Architecture Change Checklist

When modifying system architecture:

### 1. Architecture Documentation
- [ ] System overview diagram updated
- [ ] Data flow diagram updated
- [ ] Component relationships updated
- [ ] Port mappings updated
- [ ] Network diagram updated (if applicable)

### 2. Wiki Updates
- [ ] "System Overview" section updated
- [ ] "Data Flow" section updated
- [ ] "Components" section updated
- [ ] Relevant API documentation updated

### 3. Verification
- [ ] All diagrams reflect current state
- [ ] No outdated information remains
- [ ] New architecture is clearly explained

---

## Regular Audit Checklist

Perform this audit monthly or after major changes:

### 1. Service Audit
```bash
# On R58 device
systemctl list-units --type=service --all | grep -E '(preke|media|frp|vdo|ninja|r58|fleet)'
```

- [ ] All active services documented in wiki
- [ ] All disabled services reviewed (remove or document why disabled)
- [ ] No surprise services running

### 2. Directory Audit
```bash
# On R58 device
ls -la /opt/
```

- [ ] All /opt/ directories documented
- [ ] Purpose of each directory clear
- [ ] No unknown directories

### 3. Port Audit
```bash
# On R58 device
ss -tlnp | grep LISTEN
```

- [ ] All listening ports documented
- [ ] Purpose of each port clear
- [ ] No unexpected ports open

### 4. Configuration Audit
```bash
# On R58 device
find /opt -name "*.yml" -o -name "*.toml" -o -name "*.json" -o -name ".env"
```

- [ ] All configuration files documented
- [ ] Purpose of each file clear
- [ ] No orphaned config files

### 5. Wiki Completeness Check
- [ ] Can understand entire system from wiki alone
- [ ] No "TODO" or "Coming soon" placeholders
- [ ] All sections have content
- [ ] All links work
- [ ] Search finds all major components

---

## Documentation Quality Standards

All documentation must meet these standards:

### 1. Clarity
- ✅ Simple explanation for non-technical users
- ✅ Technical details for developers
- ✅ Examples where helpful
- ✅ No jargon without explanation

### 2. Completeness
- ✅ What it is
- ✅ What it does
- ✅ Where it is
- ✅ How to use it
- ✅ How to troubleshoot it

### 3. Accuracy
- ✅ Verified against actual system
- ✅ Version numbers correct
- ✅ Paths correct
- ✅ Commands tested
- ✅ No outdated information

### 4. Maintainability
- ✅ Date of last update
- ✅ Verification status
- ✅ Clear ownership
- ✅ Easy to update

---

## Git Commit Standards

When updating documentation:

### Commit Message Format
```
docs: [area] - [what changed]

Examples:
docs: wiki - add vdo-signaling custom server documentation
docs: services - document r58-fleet-agent service
docs: architecture - update system overview diagram
```

### What to Commit
- [ ] All wiki content changes
- [ ] All markdown documentation
- [ ] Component inventory updates
- [ ] Architecture diagrams (if changed)

### Commit Checklist
- [ ] Descriptive commit message
- [ ] All related files included
- [ ] No temporary/test files
- [ ] Changes tested (wiki loads, links work)

---

## Prevention Strategies

### 1. Documentation-First Approach

**Before** deploying new component:
1. Write documentation
2. Add to wiki
3. Update diagrams
4. Then deploy

**Benefits**:
- Forces you to think through the design
- Documentation is never "behind"
- No forgotten components

### 2. Peer Review

Before merging documentation changes:
- [ ] Another person reviews
- [ ] Check for completeness
- [ ] Check for accuracy
- [ ] Check for clarity

### 3. Automated Checks

Consider adding automated checks:
```bash
# Check all services are documented
systemctl list-units --type=service | grep -E '(preke|media|frp|vdo|ninja|r58|fleet)' > /tmp/services.txt
# Compare against wiki content
# Alert if mismatch
```

### 4. Documentation Debt Tracking

Keep a list of documentation TODOs:
- [ ] Document X
- [ ] Update Y
- [ ] Add diagram for Z

Review monthly and prioritize.

---

## Quick Reference: Documentation Locations

### Wiki
- **Location**: `src/static/wiki.html`
- **Content**: `src/static/js/wiki-content*.js`
- **Purpose**: User-facing documentation
- **Update**: When adding/changing features

### Component Inventory
- **Location**: `R58_COMPONENT_INVENTORY.md`
- **Purpose**: Complete list of all components
- **Update**: After every system change

### Architecture Docs
- **Location**: `docs/CURRENT_ARCHITECTURE.md`
- **Purpose**: Technical architecture reference
- **Update**: After architecture changes

### README
- **Location**: `README.md`
- **Purpose**: Quick start and overview
- **Update**: When main features change

---

## Success Metrics

Documentation is successful when:

1. ✅ **Discoverability**: User can find any component via search
2. ✅ **Completeness**: User can understand entire system from docs alone
3. ✅ **Accuracy**: All information is verified and current
4. ✅ **No Surprises**: No more "I didn't know that was running" moments
5. ✅ **Maintainability**: Easy to keep docs up to date

---

## Lessons Learned

### From VDO.ninja Incident

**What We Learned**:
1. Running services must be documented immediately
2. Assumptions about "obvious" components are dangerous
3. Regular audits catch gaps
4. Documentation is not optional

**How We Prevent Recurrence**:
1. ✅ This checklist
2. ✅ Regular audits (monthly)
3. ✅ Documentation-first approach
4. ✅ Peer review

---

## Checklist Usage

### For New Features
1. Print this checklist
2. Check off items as you go
3. Don't deploy until all items checked
4. Keep checklist with feature documentation

### For Regular Audits
1. Schedule monthly audit
2. Run all audit commands
3. Document any gaps found
4. Update wiki immediately
5. Update component inventory

### For Onboarding
1. Give this checklist to new team members
2. Explain the VDO.ninja incident
3. Make documentation part of culture
4. Lead by example

---

## Template: New Component Documentation

Use this template when documenting new components:

```markdown
## [Component Name]

**Status**: Active / Disabled / Legacy  
**Type**: Service / Software / Configuration / Directory  
**Location**: /path/to/component  
**Version**: vX.Y.Z or commit hash  
**Documented**: [Date]

### Purpose

[What it does in 1-2 sentences]

### Configuration

- **Location**: /path/to/config
- **Format**: YAML / TOML / JSON
- **Key Settings**:
  - setting1: description
  - setting2: description

### Management

\`\`\`bash
# Start/stop/restart
sudo systemctl [start|stop|restart] [service]

# View logs
sudo journalctl -u [service] -f

# Check status
sudo systemctl status [service]
\`\`\`

### Dependencies

- Depends on: [other components]
- Used by: [other components]

### Troubleshooting

**Common Issues**:
1. Issue 1: Solution
2. Issue 2: Solution

### Related Documentation

- [Link to wiki section]
- [Link to architecture doc]
```

---

## Final Checklist: Is Documentation Complete?

Before marking documentation as complete, verify:

- [ ] All active services documented
- [ ] All /opt/ directories documented
- [ ] All configuration files documented
- [ ] All ports documented
- [ ] Architecture diagrams updated
- [ ] Wiki updated
- [ ] Component inventory updated
- [ ] Changes committed to git
- [ ] Peer review completed
- [ ] No "TODO" placeholders
- [ ] All links work
- [ ] Search finds all components
- [ ] Can understand system from docs alone

**If all checked**: Documentation is complete! ✅

**If any unchecked**: Complete those items before proceeding.

---

**Remember**: Documentation is not a chore, it's insurance against confusion and mistakes. The VDO.ninja incident showed us that undocumented components cause problems. Use this checklist to prevent that from happening again.

**Next Audit Due**: January 26, 2026

