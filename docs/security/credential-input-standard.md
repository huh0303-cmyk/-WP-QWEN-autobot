# Secure credential entry standard

**Standard UI name:** `Encrypt and save on this PC`

Use this workflow whenever the operator must provide a password, WordPress REST Application Password, Meta/Threads App Secret, API key, or other credential to a local automation.

## Operator experience
1. Launch the Windows PowerShell script through the authorized Desktop Commander connection (STA mode).
2. The operator enters or pastes the value into the masked Windows dialog.
3. The script encrypts the value with Windows DPAPI using the current Windows user context.
4. The encrypted file is stored under `%LOCALAPPDATA%\Korea365\Secrets\<SecretName>.dpapi`.
5. Never print, echo, log, screenshot, commit, or transmit the plaintext credential.

## Script
- Reusable implementation: `scripts/security/secure-secret-input.ps1`
- Example invocation from Desktop Commander:
  `powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "<repo>\scripts\security\secure-secret-input.ps1" -SecretName "threads-app-secret" -Prompt "Enter the Threads App Secret from Meta."`
- The PowerShell console is used only to launch the script; the operator does not need to paste commands or secrets into the console.

## Important security boundaries
- DPAPI-encrypted files are tied to the Windows user context (and local machine protection); they are not portable secrets for GitHub-hosted runners or another PC/user.
- Do not commit encrypted credential files, plaintext credentials, generated secret values, or local secret stores to Git.
- Add secret-store paths and credential files to `.gitignore` where appropriate.
- If a credential must be used by GitHub Actions, store it separately in GitHub Actions Secrets/Environment Secrets using GitHub's secure secret-entry interface or a properly authenticated secret-management workflow. Never commit it to repository files.
- A local DPAPI file alone does not configure GitHub Actions. Validate the intended secret name and workflow variable mapping before running an authenticated publish.
- If the credential was copied while still masked (for example, eight bullet characters), stop and repeat the entry after revealing the actual value in the provider UI. Do not treat character count as proof that the credential is correct.
- Keep secret values out of command-line arguments, shell history, logs, issue comments, chat messages, and screenshots.

## Standard behavior
Use the same dialog label and masked-entry experience for future credential requests. Change only the logical secret name and prompt. Verify save success without displaying the value.
