# Security Policy

## 🔒 Security Best Practices

This document outlines security measures implemented in Daleel AI and best practices for contributors and users.

---

## ✅ Implemented Security Features

### 1. API Key Protection

- **Environment Variables**: All API keys stored in `.env` (never committed)
- **Secrets Management**: Streamlit Cloud secrets for production
- **Validation**: App validates keys on startup before processing requests
- **No Hardcoding**: Zero API keys in source code

### 2. Rate Limiting

- **Per-Session Limits**: 6 requests per minute per user session
- **Configurable**: Adjust via `MAX_REQUESTS_PER_MINUTE` environment variable
- **In-Memory Tracking**: Timestamps tracked in session state
- **Automatic Reset**: 60-second sliding window

### 3. Input Validation

- **File Upload**: Only PDF files accepted for CV analysis
- **GitHub Username**: Sanitized before API calls
- **Job Search**: Input length limits to prevent abuse
- **JSON Parsing**: Safe parsing with fallbacks

### 4. Error Handling

- **No Stack Traces**: Users never see implementation details
- **Sanitized Messages**: Generic error messages for security failures
- **Logging**: All errors logged to `daleel.log` for investigation
- **Graceful Degradation**: App continues functioning if non-critical components fail

### 5. Database Security

- **SQLite Local**: Database stored locally, not transmitted
- **Parameterized Queries**: Prevents SQL injection
- **Session Isolation**: Each session has unique ID
- **Export Control**: Users can only export their own data

---

## 🚨 Reporting Security Vulnerabilities

If you discover a security vulnerability, please:

1. **DO NOT** open a public GitHub issue
2. Email: [your-security-email@domain.com]
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

**Response Time**: We aim to respond within 48 hours.

---

## ⚠️ Known Limitations

### Current Scope

- **No User Authentication**: All users share same app instance
- **No HTTPS Enforcement**: Depends on deployment platform
- **In-Memory Rate Limiting**: Resets on app restart
- **No Data Encryption at Rest**: SQLite database is unencrypted

### Mitigation Plans (Phase 2-3)

- ✅ Add user authentication (Firebase/Auth0)
- ✅ Implement database encryption
- ✅ Add persistent rate limiting (Redis)
- ✅ Enable HTTPS-only mode
- ✅ Add CORS protection for API endpoints

---

## 🔐 Security Checklist for Developers

Before deploying or sharing code:

- [ ] No API keys in source code
- [ ] `.env` is in `.gitignore`
- [ ] `.env.example` has placeholder values only
- [ ] All secrets use environment variables
- [ ] Error messages don't expose stack traces
- [ ] File uploads validated for type and size
- [ ] Database queries use parameterization
- [ ] Logs don't contain sensitive data
- [ ] Dependencies are up to date (`pip-audit`)
- [ ] Git history doesn't contain leaked secrets

---

## 🛡️ Security for Users

### Protecting Your API Keys

1. **Never share your `.env` file**
2. **Rotate keys if exposed**:
   - Groq: [console.groq.com](https://console.groq.com/keys)
   - GitHub: [github.com/settings/tokens](https://github.com/settings/tokens)
3. **Use read-only GitHub tokens** when possible
4. **Enable 2FA** on Groq and GitHub accounts

### Safe Usage

- **Don't upload sensitive CVs** containing SSN, passport numbers, etc.
- **Review exported data** before sharing
- **Clear session state** if using shared computer
- **Log out** when using public/shared deployment

---

## 🔍 Dependency Security

### Automated Scanning

```bash
# Check for known vulnerabilities
pip install pip-audit
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

### Manual Review

All dependencies are reviewed for:
- Known CVEs
- Unmaintained packages
- Suspicious code
- License compatibility

---

## 📋 Incident Response Plan

### If API Key is Leaked

1. **Immediate**: Revoke compromised key
2. **Generate**: Create new API key
3. **Update**: Replace in `.env` or secrets
4. **Monitor**: Check for unusual API usage
5. **Rotate**: Update all deployments

### If Database is Compromised

1. **Backup**: Save current database
2. **Analyze**: Check logs for unauthorized access
3. **Clean**: Delete compromised data
4. **Notify**: Inform affected users
5. **Migrate**: Move to encrypted storage

### If Code Vulnerability Found

1. **Validate**: Confirm vulnerability exists
2. **Patch**: Develop and test fix
3. **Deploy**: Update all environments
4. **Notify**: Security advisory if public
5. **Document**: Add to changelog

---

## 🧪 Security Testing

### Manual Tests

```bash
# Test rate limiting
for i in {1..10}; do
  curl http://localhost:8501/match_jobs
  sleep 5
done

# Test input validation
python -c "
import requests
# Test with malicious input
"
```

### Automated Tests

```python
# test_security.py
def test_api_key_required():
    """App should not start without API key."""
    # Remove GROQ_API_KEY
    # Attempt to start app
    # Assert error shown

def test_rate_limiting():
    """Too many requests should be blocked."""
    # Send 10 requests in 30 seconds
    # Assert 7th request fails

def test_sql_injection():
    """Database queries should be parameterized."""
    # Attempt SQL injection in inputs
    # Assert no database error
```

---

## 📚 Security Resources

### Tools

- [pip-audit](https://github.com/pypa/pip-audit) - Python dependency scanner
- [Bandit](https://github.com/PyCQA/bandit) - Python security linter
- [GitGuardian](https://www.gitguardian.com/) - Secret scanning

### Guides

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Streamlit Security](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)

---

## 🔄 Update Policy

### Security Updates

- **Critical**: Deployed within 24 hours
- **High**: Deployed within 1 week
- **Medium**: Deployed in next release
- **Low**: Documented for future consideration

### Dependency Updates

- **Monthly**: Review all dependencies
- **Quarterly**: Major version upgrades
- **Immediate**: Critical security patches

---

## 📞 Security Contact

- **Email**: [ypssefmohammedahmed@gmial.com]
- **PGP Key**: [Optional: Include public key]
- **Response Time**: 48 hours

---

## ✅ Security Checklist for Production

Before deploying to production:

- [ ] All secrets in environment variables
- [ ] HTTPS enabled
- [ ] Rate limiting configured
- [ ] Error logging enabled
- [ ] Database backups automated
- [ ] Monitoring and alerts set up
- [ ] Security headers configured
- [ ] CORS properly configured
- [ ] Dependencies up to date
- [ ] Security scan passed

---

*Last Updated: April 2026*
*Security Version: 1.1*