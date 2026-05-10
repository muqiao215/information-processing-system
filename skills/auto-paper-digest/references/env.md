# APD environment notes

The project loads optional `.env` values for publishing and shared login reuse.

Key variables from `.env.example`:

- `HF_TOKEN`
- `HF_USERNAME`
- `HF_DATASET_NAME`
- `GITHUB_DIGEST_REPO`

NotebookLM profile reuse priority in `apd.config.resolve_notebooklm_profile()`:

1. `APD_NOTEBOOKLM_PROFILE_DIR`
2. `NOTEBOOKLM_HOME/browser_profile`
3. `~/.notebooklm/browser_profile`
4. `data/profiles/default`

## Practical rule

If the user already has a working NotebookLM CLI login, prefer reusing that profile rather than creating a new APD-local login state.

Examples:

```powershell
$env:NOTEBOOKLM_HOME="$HOME\\.notebooklm"
```

or

```powershell
$env:APD_NOTEBOOKLM_PROFILE_DIR="$HOME\\.notebooklm\\browser_profile"
```

## Caution

- Do not commit real `.env` files or tokens.
- Publish commands depend on Hugging Face credentials being present.
- Douyin publish and NotebookLM generation may require headful mode during login repair.
