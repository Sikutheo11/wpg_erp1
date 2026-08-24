# WPG Enterprise Finance Workflow V1

This package upgrades Finance from direct data entry to company-wide controlled workflows.

## Workflows

### Money out

Employee request -> Unit/Line Manager -> Accountant funds check -> Finance Manager -> CEO -> Accountant payment -> Expense posting.

### Money in

Business Unit employee declaration -> Unit/Line Manager -> Finance account confirmation -> Income posting.

Pending requests and declarations never change Cash, Bank or Mobile Money balances.

## Business-unit ownership

- Django Groups are the source of roles and permissions.
- `Employee.department.business_unit` is the source of an employee's business unit.
- Non-superusers cannot choose a different unit when initiating a request or declaration.
- Unit managers see their own records and records belonging to departments they manage.
- Accountant, Finance Manager, CEO and superusers have company-wide Finance visibility.
- A department and assigned manager are required before a draft enters an approval workflow.

## Local installation

```bash
tar -xzf /d/WPG_project/WPG_enterprise_finance_workflow_v1.tar.gz

python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py sync_core

python manage.py test \
core.test_group_permissions \
finance.test_expense_request_workflow \
finance.test_accounts \
finance.test_permissions \
finance.test_obligations \
finance.test_counterparty_views \
finance.test_debt_service \
finance.test_debt_models \
-v 2 --keepdb
```

## Browser verification

1. Create an expense request as a Worker.
2. Approve it as the employee's Department manager.
3. Verify funds as Accountant.
4. Approve as Finance Manager.
5. Give final approval as CEO.
6. Pay as Accountant and verify the account decreases once.
7. Record Business Unit Income as a Worker.
8. Confirm its source as the Department manager.
9. Confirm the destination account as Accountant and verify the account increases once.

Do not deploy before the migration dry-run and all tests pass locally.
