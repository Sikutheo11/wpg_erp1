# Role dashboard and access-denied browser fix v3

Apply after template shell separation v1 and v2.

## Changes

- Executive company-wide data is available only to superusers.
- Other users see `My Work Dashboard` and summaries only for Business Units
  and Enterprise Engines allowed by their Django Group permissions.
- Non-executive pending approvals and audit activity are limited to the
  logged-in user's own records.
- Permission failures render a branded 403 page instead of the plain browser
  response.
- The 403 page uses Marketplace shell for Customer Group users and BOS shell
  for staff users.

## Verification

```bash
python manage.py check
python manage.py test core.test_template_shells core.test_group_permissions sales.test_permissions -v 2 --keepdb
```

Browser checks:

- A Marketplace-only user must not see Finance, Furniture or Construction
  summaries on `/dashboard/`.
- A superuser must still see the company-wide Executive Dashboard.
- A user without Sales invoice permission should receive the branded 403 page.
