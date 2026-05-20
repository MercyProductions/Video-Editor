# Plugin API

Plugins are local folders under `plugins/`. The current stable API is manifest-first. Plugin code is not executed by default.

Required manifest fields:

```json
{
  "id": "sample_effect",
  "name": "Sample Effect",
  "type": "effect",
  "version": "0.1.0",
  "localOnly": true,
  "enabled": true,
  "permissions": [],
  "sandbox": {
    "mode": "manifest_only",
    "crashIsolation": true
  },
  "capabilities": {}
}
```

Supported plugin types:

- `transition`
- `effect`
- `template`
- `export_preset`
- `automation`

Permission names:

- `read_project`
- `write_project`
- `read_assets`
- `write_assets`
- `run_ffmpeg`
- `spawn_process`

Audit plugins:

```powershell
python render.py plugin audit
python render.py plugin disable sample_effect
python render.py plugin enable sample_effect
```

Render hooks and executable event hooks are intentionally conservative. Any future executable plugin must run as a separate local process and display permission warnings before use.
