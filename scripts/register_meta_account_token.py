"""Read a token privately; verify ownership before GitHub environment storage."""
import argparse
import getpass
import json
import subprocess
from meta_account_preflight import expected_handle, load_policy, verify_identity

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--platform", choices=["instagram", "threads"], required=True)
    p.add_argument("--account", required=True)
    args = p.parse_args()
    policy = load_policy()
    account = next(a for a in policy["accounts"] if a["key"] == args.account)
    token = getpass.getpass("Access token (hidden): ").strip()
    identity = verify_identity(args.platform, token)
    if identity.get("status") != "IDENTITY_RESPONSE_OK":
        raise SystemExit("BLOCKED: token could not be verified")
    if identity["resolved_username"].casefold() != expected_handle(account, args.platform).casefold():
        raise SystemExit("BLOCKED: token belongs to a different account")
    repo = "huh0303-cmyk/-WP-QWEN-autobot"
    prefix = f"META_{args.platform.upper()}_{args.account.upper()}"
    # stdin avoids command-line/process-list disclosure.
    subprocess.run(["gh", "secret", "set", prefix+"_ACCESS_TOKEN", "-R", repo,
                    "--env", "META-SOCIAL"], input=token, text=True, check=True)
    subprocess.run(["gh", "variable", "set", prefix+"_USER_ID", "-R", repo,
                    "--env", "META-SOCIAL", "--body", identity["resolved_user_id"]], check=True)
    print(json.dumps({"stored": True, "platform": args.platform,
        "handle": identity["resolved_username"], "environment": "META-SOCIAL"}))

if __name__ == "__main__":
    main()
