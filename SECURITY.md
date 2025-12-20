# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in DubSync, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Send an email to the maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to expect

- We will acknowledge receipt within 48 hours
- We will provide an initial assessment within 7 days
- We will work on a fix and coordinate disclosure timing
- Credit will be given to reporters (unless anonymity is preferred)

### Scope

This security policy applies to:
- The DubSync application itself
- Built-in plugins
- The plugin loading mechanism

External/third-party plugins are the responsibility of their respective authors.

## Security Best Practices for Users

1. **Plugin Security**: Only install plugins from trusted sources
2. **Project Files**: Be cautious when opening `.dubsync` files from unknown sources
3. **Updates**: Keep DubSync updated to get the latest security fixes

## Security Considerations for Plugin Developers

If you're developing plugins for DubSync:

1. **Input Validation**: Always validate user input
2. **File Operations**: Be careful with file system access
3. **Dependencies**: Keep your dependencies updated and audit them regularly
4. **Code Review**: Consider having your code reviewed before publishing

---

*This document is available in [Hungarian](docs/SECURITY_HU.md).*
