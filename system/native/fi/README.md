# Fi system policy

This is Fi's active native manifest. Tjikup renders `.j2` templates and deploys
regular files, symlinks and explicit retirements with conflict preflight and
recovery receipts. Li and Si have their own manifests in adjacent directories.

Use `tjikup config system plan` to inspect changes. Run isolated manifest tests
with `TJIKUP_BINARY=/path/to/tjikup python3 -B -m unittest discover -s tests -p
test_native_integration.py` from the Dotjik repository root. These tests rewrite
ownership to the invoking user and apply twice under temporary roots. They do
not read credentials, modify live /etc or start services.
