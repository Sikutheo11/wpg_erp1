# Sales navigation regression fix

This patch fixes the Sales pages that raised `NoReverseMatch` or
`TemplateDoesNotExist`.

## Included fixes

- Adds the `sales:` namespace to customer and legacy Sales links.
- Aligns Sale and Invoice view template paths with the templates in the repo.
- Adds the missing customer deactivation, payment list, and sales report
  templates.
- Keeps legacy Sale, Invoice, and CustomerPayment records read-only and points
  new work toward Quotations, Enterprise Orders, and Finance.
- Supports the project's custom User `full_name` property in Customer display
  names.
- Adds real-template navigation regression tests.

No model schema was changed, so this patch requires no migration.
