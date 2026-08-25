# WPG template shell audit

This patch separates the user interfaces into two supported shells:

- `base_dashboard.html`: internal WPG BOS pages for employees and managers.
- `ecommerce/base_ecommerce.html`: Marketplace pages for customers and public visitors.

## Changes

- Public home, customer registration, the legacy customer dashboard template and
  logout compatibility page now inherit the Marketplace shell.
- Customer Group users always land on `ecommerce:shop`.
- The customer dashboard URL remains as a compatibility redirect.
- Profile uses the Marketplace shell for Customer Group users and the BOS shell
  for staff users.
- Marketplace seller, settlement, refund and management report pages inherit the
  BOS shell.
- Marketplace Management navigation is hidden from ordinary customers.
- Dashboard KPI widgets are limited to Business Units and Enterprise Engines the
  logged-in user may access.

## Legacy base

`templates/base.html` is intentionally retained for one release as a rollback
fallback. No active page should extend it. Remove it only after the regression
test and browser smoke tests pass in the real project.

## Verification

Run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test core.test_template_shells core.test_group_permissions -v 2 --keepdb
```

Then verify in a browser:

- `/` as an anonymous visitor
- `/accounts/registerUser/`
- `/accounts/profile/` as Customer
- `/accounts/profile/` as staff
- `/dashboard/` as staff roles
- Marketplace seller and settlement management pages as authorized staff
