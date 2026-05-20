# Template Guide

Templates generate normal project JSON, so every template remains editable in Advanced Mode.

Useful commands:

```powershell
python render.py template list
python render.py template create product_promo -o examples/generated/product_promo.json --generate-placeholders
python render.py style apply examples/generated/product_promo.json red_black_aegis -o examples/generated/product_promo.red.json
```

Local packs can be exported and imported without a marketplace server:

```powershell
python render.py pack export examples/generated/product_promo.json --type template --name ProductPromo
python render.py pack import output/packs/ProductPromo.templatepack
```
