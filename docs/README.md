# Documentation Index

This directory contains organized documentation for the Anthropic Proxy project.

## 📚 Documentation Structure

### Core Documentation (Root Directory)
- **[README.md](../README.md)** - Main project documentation, quick start, usage examples
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes  
- **[AGENTS.md](../AGENTS.md)** - Essential context for AI agents working on this project

### API Documentation
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API reference and examples

### Development Documentation
- **[DEVELOPMENT.md](development/DEVELOPMENT.md)** - Development setup, scripts, and troubleshooting
- **[LOGGING_IMPROVEMENTS.md](development/LOGGING_IMPROVEMENTS.md)** - Logging system enhancements
- **[TESTING_ORGANIZATION.md](development/TESTING_ORGANIZATION.md)** - Test suite organization and structure

### Performance Documentation
- **[OPTIMIZATION_SUMMARY.md](performance/OPTIMIZATION_SUMMARY.md)** - Performance optimization journey and results
- **[ADVANCED_PERFORMANCE_ANALYSIS.md](performance/ADVANCED_PERFORMANCE_ANALYSIS.md)** - Framework optimization analysis and recommendations
- **[PERFORMANCE_ANALYSIS.md](performance/PERFORMANCE_ANALYSIS.md)** - Detailed performance metrics and analysis

### Architecture Documentation
- **[IMAGE_ROUTING.md](architecture/IMAGE_ROUTING.md)** - Image processing and routing logic
- **[CONNECTION_HANDLING.md](architecture/CONNECTION_HANDLING.md)** - HTTP connection management and pooling

## 🎯 Quick Navigation

### For Users
1. Start with **[README.md](../README.md)** for quick setup and usage
2. Reference **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** for API details
3. Check **[CHANGELOG.md](../CHANGELOG.md)** for latest updates

### For Developers
1. Read **[DEVELOPMENT.md](development/DEVELOPMENT.md)** for development setup
2. Review **[AGENTS.md](../AGENTS.md)** for AI agent context (critical!)
3. Check **[TESTING_ORGANIZATION.md](development/TESTING_ORGANIZATION.md)** for testing guidelines

### For Performance Analysis
1. Review **[OPTIMIZATION_SUMMARY.md](performance/OPTIMIZATION_SUMMARY.md)** for current performance status
2. See **[ADVANCED_PERFORMANCE_ANALYSIS.md](performance/ADVANCED_PERFORMANCE_ANALYSIS.md)** for optimization recommendations

### For Architecture Understanding
1. Check **[IMAGE_ROUTING.md](architecture/IMAGE_ROUTING.md)** for routing logic
2. Review **[CONNECTION_HANDLING.md](architecture/CONNECTION_HANDLING.md)** for HTTP management

## 📋 Documentation Standards

### File Naming Convention
- Use `UPPERCASE_WITH_UNDERSCORES.md` for technical documentation
- Use descriptive names that clearly indicate content
- Place in appropriate subdirectory based on content type

### Content Organization
- **Core docs** (README, CHANGELOG, AGENTS) stay in root
- **API docs** in `/docs/` root level
- **Development** docs in `/docs/development/`
- **Performance** docs in `/docs/performance/`
- **Architecture** docs in `/docs/architecture/`

### Special Files

#### AGENTS.md - Critical for AI Development
The `AGENTS.md` file **must remain in the root directory** as it provides essential context for AI agents working on this project. It contains:
- Project architecture overview
- Critical development rules (Docker Compose usage)
- Environment configuration guidelines
- Testing requirements and patterns
- Recent changes and bug fixes

This file serves as a "constitution" for AI agents to ensure consistent, proper development practices.

---

*Documentation organized on September 28, 2025*  
*Structure: Core (root) → API → Development → Performance → Architecture*