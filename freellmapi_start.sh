#!/bin/bash
# Starts the FreeLLMAPI router with provider keys injected from the credential store.
# Keys never touch a second file: the declarative config is built in memory as FREEAPI_CONFIG_JSON.
set -euo pipefail
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:/usr/bin:/bin
set -a; source "$HOME/.config/market-secrets/credentials.env"; set +a
export FREEAPI_CONFIG_JSON="$(python3 -I - <<'PY'
import json, os
keys = []
for platform, var in [("groq","GROQ_API_KEY"),("cerebras","CEREBRAS_API_KEY"),("google","GEMINI_API_KEY"),
                      ("mistral","MISTRAL_API_KEY"),("huggingface","HF_TOKEN")]:
    v = os.environ.get(var, "").strip()
    if v:
        keys.append({"platform": platform, "key": v, "label": "credentials.env"})
cfg = {"admin": {"email": os.environ["FREELLMAPI_ADMIN_EMAIL"], "password": os.environ["FREELLMAPI_ADMIN_PASSWORD"]},
       "keys": keys, "routing": {"strategy": "balanced"}}
print(json.dumps(cfg))
PY
)"
cd "$HOME/freellmapi/server"
set -a; source "$HOME/freellmapi/.env"; set +a
exec node dist/index.js
