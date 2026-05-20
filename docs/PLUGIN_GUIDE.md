# Plugin Guide

Plugins are local folders under `plugins/`. By default they are manifest-only and are not executed as code.

Create and audit a plugin:

```powershell
python render.py plugin init "My Transition" transition
python render.py plugin audit
python render.py plugin disable my_transition
```

Plugin manifests must declare:

- `id`
- `name`
- `type`
- `version`
- `localOnly: true`
- requested `permissions`
- `sandbox` metadata

Risky permissions such as `spawn_process`, `write_project`, and `write_assets` are reported during audits.
