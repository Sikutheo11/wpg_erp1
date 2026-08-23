# WPG obligation catalog deployment

Apply this package on a clean branch created from the current `main` branch.

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate

python manage.py test \
  finance.test_obligations \
  finance.test_permissions \
  finance.test_counterparty_views \
  finance.test_debt_service \
  -v 2 --keepdb

git diff --check
git status --short
```

The migration seeds the Furniture, Construction and Agriculture catalogs. It
does not delete legacy debt fields or existing obligation records.
