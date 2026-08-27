# Legacy Model Retirement Plan

WPG BOS keeps historical records readable while new operations use the shared
enterprise engines. No legacy table should be deleted until production data has
been exported, mapped, migrated, reconciled, and backed up.

| Legacy model | Current replacement |
| --- | --- |
| `furniture.Order` | `orders.Order` and `orders.OrderItem` |
| `sales.Sale` / `sales.SaleItem` | Shared Order Engine and approved quotations |
| `sales.Invoice` | `sales.EnterpriseInvoice` |
| `sales.CustomerPayment` | `finance.Payment` and `finance.Receivable` |
| `furniture.ProductionOutput.legacy_order` | `furniture.ProductionJob` relationship |

## Stage 1 — enforced now

- Legacy lists and Django Admin records are read-only.
- Legacy furniture write routes are removed.
- The shadowed legacy `sales/services.py` write helpers reject writes; active
  workflows use the `sales.services` package and enterprise services.
- Sidebar permissions grant view access only to legacy registers.
- `python manage.py audit_legacy_models` reports remaining records and links.

## Later removal stages

1. Export every legacy record and retain its original primary key.
2. Define and verify mappings to the enterprise replacement records.
3. Migrate data, reconcile totals, and detach `ProductionOutput.legacy_order`.
4. Run `python manage.py audit_legacy_models --require-empty` in a production
   copy. Remove models and tables only after it succeeds and a restorable
   database backup has been verified.

`inventory.RawMaterial` is not part of this retirement because active workflows
still depend on it. It requires a separate migration project before removal.
