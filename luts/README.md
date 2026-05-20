# Local LUT Folder

Place `.cube` or `.3dl` LUT files here. They stay local and can be listed with:

```powershell
python render.py color luts
```

Apply a LUT alongside a built-in grade:

```powershell
python render.py color apply examples/project.json clean_cinematic --lut luts/my-grade.cube
```
