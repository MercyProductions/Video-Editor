# Beginner Tutorial

Fastest local workflow:

1. Open the desktop app.
2. Choose a bundled template or demo.
3. Import media assets.
4. Render a preview.
5. Review quality warnings.
6. Render final output.

CLI equivalent:

```powershell
python render.py template create product_promo -o examples/generated/my_product.json --generate-placeholders
python render.py refine examples/generated/my_product.json --preset clean_cinematic -o examples/generated/my_product.refined.json
python render.py render examples/generated/my_product.refined.json -o output/my_product.mp4 --quality preview --cache --resume
```

Use `python render.py demo list` to see polished demo projects.
