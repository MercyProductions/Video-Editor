# Advanced Workflows

Refinement pass:

```powershell
python render.py refine examples/project.json --preset premium_red_black -o examples/generated/refined.json
```

Color/LUT pipeline:

```powershell
python render.py color list
python render.py color luts
python render.py color apply examples/project.json clean_cinematic --lut luts/custom.cube -o examples/generated/graded.json
```

Asset database:

```powershell
python render.py asset-db index examples/assets
python render.py asset-db duplicates
python render.py asset-db report -o output/asset_db_report.json
```

Performance and release readiness:

```powershell
python render.py profile-run examples/project.json -o output/profile.json
python render.py release-check -o output/release_candidate_check.json
```

Recovery:

```powershell
python render.py recovery restore-point examples/project.json --label before_changes
python render.py recovery integrity examples/project.json
python render.py recovery relink examples/project.json examples/assets -o examples/generated/relinked.json
```
