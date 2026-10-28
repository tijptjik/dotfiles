"""Authenticated GitHub metadata requests for standalone installer bundles.

Keep the copies in Chezmoi and Chezetc identical; neither checkout is required
at runtime. Credentials are resolved in memory and only sent to api.github.com.
"""
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request


def github_token():
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(name, "").strip()
        if token:
            return token
    command = ["gh", "auth", "token", "--hostname", "github.com"]
    desktop_user = os.environ.get("SUDO_USER", "")
    if os.geteuid() == 0 and desktop_user and desktop_user != "root":
        # Launcher installers run under sudo. Do not look in root's gh config.
        command = ["sudo", "-n", "-H", "-u", desktop_user, "--", "env",
                   "-u", "XDG_CONFIG_HOME", "-u", "GH_CONFIG_DIR", *command]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (result.stdout.strip() or None) if result.returncode == 0 else None


def is_github_api(url):
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme == "https" and parsed.netloc == "api.github.com")


class GitHubRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if not is_github_api(new_url):
            raise RuntimeError("GitHub API redirected outside api.github.com; lookup stopped")
        return super().redirect_request(request, response, code, message, headers, new_url)


def github_json(url):
    if not is_github_api(url):
        raise RuntimeError("GitHub metadata requests must use https://api.github.com")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tjik-github-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(GitHubRedirectHandler())
    try:
        with opener.open(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise RuntimeError(
                "GitHub rejected the configured credentials; refresh GH_TOKEN/GITHUB_TOKEN "
                "or run gh auth login --hostname github.com as the invoking user."
            ) from None
        if error.code in (403, 429):
            raise RuntimeError(
                f"GitHub lookup was denied or rate-limited (HTTP {error.code}); "
                "run gh auth login --hostname github.com as the invoking user "
                "or retry after the API limit resets."
            ) from None
        raise RuntimeError(f"GitHub metadata lookup failed (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("GitHub metadata lookup failed; check the network connection and retry") from None
    except (ValueError, UnicodeError):
        raise RuntimeError("GitHub returned invalid JSON metadata; retry later") from None
