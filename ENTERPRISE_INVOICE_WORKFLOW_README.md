# WPG Enterprise Invoice Workflow

## Ownership

- Sales owns customers, invoice creation, invoice PDF and customer delivery.
- Orders owns product/service lines and commercial totals.
- Finance owns receivables, confirmed payments, balances and accounting.
- Issuing an invoice creates at most one Finance Receivable per Order.

## Required production environment

Do not commit these values to Git:

```
PUBLIC_BASE_URL=https://wisdompalacegroup.com
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_INVOICE_TEMPLATE=wpg_invoice
WHATSAPP_TEMPLATE_LANGUAGE=en
WHATSAPP_GRAPH_API_VERSION=v23.0
```

Configure Django email settings in `/etc/wpg-bos.env` as already used by the project.
The Meta template must have four body variables: customer name, invoice number,
amount due, and the secure invoice URL.

## Deployment order

1. `python manage.py migrate`
2. `python manage.py sync_core`
3. `python manage.py sync_invoice_permissions`
4. `python manage.py collectstatic --noinput`
5. restart Gunicorn/systemd and run smoke tests.

The public PDF URL uses an unguessable UUID and only serves issued, partial or
paid invoices. Rotate the token from Django admin if a link is exposed.
