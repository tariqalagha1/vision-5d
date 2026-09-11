#!/usr/bin/env python3
"""Poll GitHub device flow, then login + create repo + push vision-5d."""
import json, time, urllib.request, os, subprocess, sys

DEV = os.path.expandvars(r"$LOCALAPPDATA/Temp/v5d_device.json")
d = json.load(open(DEV))
device_code = d["device_code"]
interval = int(d.get("interval", 5))
client_id = "178c6fc778ccc68e1d6a"
REPO = "vision-5d"

def poll_token(timeout=880):
    iv = interval
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(iv)
        data = (f"client_id={client_id}&device_code={device_code}"
                "&grant_type=urn:ietf:params:oauth:grant-type:device_code").encode()
        req = urllib.request.Request("https://github.com/login/oauth/access_token",
                                     data=data, headers={"Accept": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        if "access_token" in r:
            return r["access_token"]
        e = r.get("error", "")
        if e == "authorization_pending":
            continue
        if e == "slow_down":
            iv += 5
            continue
        print(f"DEVICE_FLOW_ERROR {e}", flush=True)
        return None
    return None

print("POLLING for device authorization...", flush=True)
token = poll_token()
if not token:
    print("DEVICE_FLOW_TIMEOUT", flush=True)
    sys.exit(1)

# gh login via hosts.yml fallback (avoids --with-token keyring hang)
login = json.loads(urllib.request.urlopen(urllib.request.Request(
    "https://api.github.com/user",
    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )).read())["login"]
ghdir = os.path.expanduser("~/.config/gh")
os.makedirs(ghdir, exist_ok=True)
hosts = os.path.join(ghdir, "hosts.yml")
with open(hosts, "w") as f:
    f.write(f"github.com:\n    users:\n        {login}:\n            oauth_token: {token}\n"
            f"    git_protocol: https\n    oauth_token: {token}\n    user: {login}\n")
os.chmod(hosts, 0o600)
print(f"GH_LOGIN_OK user={login}", flush=True)

subprocess.run(["gh", "auth", "setup-git"], check=False)

# create repo + push
print("CREATING_REPO", flush=True)
r = subprocess.run(["gh", "repo", "create", REPO, "--public", "--source", ".", "--push"],
                   capture_output=True, text=True)
print("REPO_CREATE_EXIT", r.returncode, flush=True)
if r.returncode != 0:
    print("STDERR:", r.stderr[-1500:], flush=True)
    print("STDOUT:", r.stdout[-1500:], flush=True)
else:
    print("PUSH_COMPLETE", flush=True)
    print(r.stdout[-500:], flush=True)
