# Legacy wallet recovery

The old Arweave (`arkb-nodejs`) configuration and Solana keypair/configuration
files are recoverable from Bitwarden Secrets Manager's dotfiles project:

- `LEGACY_ARWEAVE_WALLET_RECOVERY`
- `LEGACY_SOLANA_WALLETS_RECOVERY`

Each entry preserves the exact original bytes from both the Google Drive
`system` tree and li. Cloud and laptop versions have separate paths; do not
assume one is authoritative or discard a differing version. The opaque Arweave
wallet string is preserved as stored; this does not establish that any separate
password required by its original application is available.

## Restore format

Retrieve the chosen secret using the existing Bitwarden Secrets Manager access.
Do not print its value or place it in Git, shell history, or command arguments.

1. Parse the secret value as JSON. Its `encoding` is `zlib-base64-json`.
2. Base64-decode `payload`, decompress it with zlib, and parse the resulting JSON.
3. The inner format is `legacy-wallet-files-v1`. Each item in `files` contains
   `path`, `sha256`, and `content_base64`.
4. Base64-decode each file's content and verify its SHA-256 before use.
5. Restore into a new private directory, preserving the `cloud/` and `laptop/`
   branches. Reject absolute paths or `..` components. Use directory mode 0700
   and file mode 0600. Do not overwrite an active wallet or CLI configuration.

Import verification retrieved both secrets, reconstructed every file and
compared the restored bytes with the staged originals. This verifies recovery
of the files; it does not verify wallet balances, signing, or application unlock.
Non-secret provenance hashes and secret IDs are recorded on fi in
`~/.local/state/private-storage/migrations/wallet-bitwarden-import.json`.
