# Bitwarden Secure Token Management

This configuration uses Bitwarden for secure storage of API tokens. Follow these steps to set up secure token management:

### Prerequisites

1. **Install Bitwarden CLI**:
   ```bash
   # Using curl (recommended)  
   wget "https://bitwarden.com/download/?app=cli&platform=linux" -O /tmp/bw.zip
   unzip /tmp/bw.zip -d /tmp && chmod +x /tmp/bw && sudo mv /tmp/bw $TOOLS
   
   # Verify installation
   bw --version
   ```

2. **Authenticate with Bitwarden**:
   ```bash
   # Login to Bitwarden (you'll need your Bitwarden credentials)
   bw login
   
   # Unlock your vault (required for each session)
   bw unlock
   ```

### Setting Up API Tokens

1. **Create Bitwarden Items**:
   - Create a login item named **"GitHub Token"** with your GitHub token in the password field
   - Create a login item named **"Anthropic API Token"** with your Anthropic token in the password field

2. **Test Bitwarden integration**:
   ```bash
   # Test individual token retrieval
   bw get "GitHub Token/password"
   bw get "Anthropic API Token/password"
   ```

### Token References

The configuration expects these Bitwarden items:

- **`GitHub Token/password`** → Sets `GHI_TOKEN` environment variable
- **`Anthropic API Token/password`** → Sets `ANTHROPIC_AUTH_TOKEN` environment variable

### Security Benefits

- ✅ **No hardcoded secrets** in version control
- ✅ **Encrypted storage** in Bitwarden vault  
- ✅ **Automatic decryption** only on authenticated machines
- ✅ **Team sharing** capabilities for organizational secrets

### Alternative: Manual Token Setup

If you prefer not to use Bitwarden:

1. Edit `~/.config/fish/conf.d/export.fish` directly
2. Replace `"REPLACE_WITH_BITWARDEN_SETUP"` with your actual tokens
3. **Warning**: Tokens will be stored in plaintext on your filesystem
