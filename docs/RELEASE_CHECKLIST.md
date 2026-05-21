# Release Checklist

Use this before handing a build to another person.

Required checks:

```powershell
python -m compileall src
python -m unittest discover -s tests
cd desktop-app
npm run typecheck
npm run test:unit
npm run build
cd ..
python render.py release-check -o output/release_candidate_check.json
python render.py installer portable -o output/automatic-video-editor-portable.zip
cd desktop-app
npm run build:installer
```

Shortcut for the main local gate:

```powershell
python scripts/verify_local.py
```

Manual checks:

- Open the app.
- Create or open a project.
- Render preview.
- Open Local Hardening and refresh status.
- Open bundled docs.
- Render final MP4.
- Confirm output folder opens.

Release artifacts:

- Windows installer `.exe`
- Desktop ZIP
- Engine portable ZIP
- `output/release_candidate_check.json`
- `output/architecture_audit.json`
- `output/performance_profile.json`
- Changelog
