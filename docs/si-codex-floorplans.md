# Codex floor-plan extraction on Si

The `codex-floorplans` manifest group installs a private extraction worker beside
Si's existing subscription-authenticated Codex VPN service. It does not replace
image rendering or enable a new public endpoint. No live deployment is performed
by adding this policy.

The reference implementation is HYPE's `scripts/floorplans/`; the four files in
`system/native/si/files/floorplans/` must be synchronized when changing the protocol.

Prerequisites: the existing Codex account login and VPN network, Python 3 with
Pillow, Poppler (`pdfinfo` and `pdftoppm`), and a root-owned 0600 environment file
`/etc/codex-vpn/floorplans.env` containing `FLOORPLAN_TOKEN`. Obtain and install the
credential using the established private BWS flow; never commit its value.

Apply only the `codex-floorplans` group through the existing native Tjikup manifest
and state directory, review the plan, then start `codex-floorplans.service`.
Do not blanket-apply the host manifest. The unit is not enabled automatically.

The worker listens on `/run/codex-floorplans/worker.sock` so it can retain the
Codex VPN namespace without exposing an unauthenticated listener. A separately
reviewed private reverse proxy must be able to access this socket and preserve
Authorization. Do not publish the socket through an unrestricted public route.
HYPE requires server-side `FLOORPLAN_WORKER_URL` and `FLOORPLAN_WORKER_TOKEN`
bindings. The browser never receives the credential or the worker URL.

Jobs accept at most 30 MiB and 12 PDF pages, queue eight jobs, and execute one at
a time. Source scans, logs and generated JSON remain in the 0700 state directory.
Set an operations retention policy before production use; source plans may be
private. HYPE copies completed page images and results into its private asset
bucket. Model output is an untrusted review draft and is validated before use.
No automatic publication, geographic placement, room identity creation or routing
is performed.

Verify with synthetic PDFs and mocked Codex output before sending building plans.
Then perform a subscription inference check, upload/poll round trip, source image
fetch and authenticated HYPE draft save. A running service alone does not prove
this integration works. The current change has not been deployed to Si.

The adapter now exposes `POST /jobs/:id/retry` for failed jobs using the retained
source. Restart recovery marks interrupted queued/running jobs failed, allowing an
explicit retry. HYPE retains the current building job pointer independently and
serves completed review data from its private bucket after worker shutdown.

The test-only fixture server and integration harness in HYPE are never part of
this manifest group. Production uses `extract.py` and the subscription Codex CLI.
Page ordering is numeric, including PDFs with 10-12 pages.
