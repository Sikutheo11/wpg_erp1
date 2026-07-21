# WPG ERP SYSTEM ARCHITECTURE
## Official Technical Architecture Document

**Project:** Wisdom Palace Group ERP

**Version:** 1.0

**Status:** Official System Architecture

**Owner:** Wisdom Palace Group

---

# 1. Purpose

This document defines the technical architecture of the WPG ERP.

It explains:

- Module organization
- Application communication
- Layer responsibilities
- Data ownership
- Security
- Integration rules
- Future scalability

This document must be followed by every developer.

---

# 2. High-Level Architecture

```

                            Users
│
────────────────────────────────────────────
│
Presentation Layer
(Django Templates / Bootstrap / JS)
│
────────────────────────────────────────────
│
Views Layer
│
────────────────────────────────────────────
│
Business Logic Layer
(models.py + services.py)
│
────────────────────────────────────────────
│
Database Layer
(SQLite / PostgreSQL)

```

Every request flows through these layers.

---

# 3. Application Architecture

```

                     WPG ERP

                         │

────────────────────────────────────────────

                         │

        ┌──────────────┬──────────────┐
        │              │              │

     Accounts        Employee        Core

        │              │              │

────────┴──────────────┴──────────────┘

                       │

       ┌───────────────┼─────────────────┐
       │               │                 │

   Inventory       Furniture      Construction

       │               │                 │

       └───────────────┼─────────────────┘

                       │

              Finished Products

                       │

        ┌──────────────┼──────────────┐
        │                             │

    Ecommerce                    Sales

        │                             │

        └──────────────┬──────────────┘

                       │

                   Finance

```

---

# 4. Module Responsibilities

## Accounts

Responsible for:

- Authentication
- Authorization
- Users
- Roles
- Login
- Registration

Never stores business information.

---

## Employee

Responsible for:

- Employees
- Departments
- Positions
- Attendance
- Leave

Provides workforce information to other modules.

---

## Inventory

Responsible for:

- Products
- Raw Materials
- Warehouses
- Assets
- Suppliers
- Stock Movements

Inventory owns stock.

No other module updates stock directly.

---

## Furniture

Responsible for manufacturing.

Includes:

- Production Orders
- BOM
- Machines
- Labour
- Material Consumption
- Production Outputs

Furniture never sells products.

---

## Construction

Responsible for:

- Projects
- Sites
- Tasks
- Construction Materials
- Labour
- Expenses

---

## Ecommerce

Responsible for:

- Online Store
- Product Showcase
- Shopping Cart
- Checkout
- Customer Portal

Ecommerce never manufactures products.

---

## Sales

Responsible for:

- Walk-in Sales
- Quotations
- POS
- Invoices
- Customer Payments

---

## Finance

Responsible for:

- Accounting
- Income
- Expenses
- Receivables
- Payables
- Payroll Accounting

Finance never creates sales.

---

## Core

Responsible for:

- Dashboard Registry
- Shared Utilities
- Global Settings
- Common Services

---

# 5. Data Ownership

Every business object has one owner.

| Data | Owner Module |
|-------|--------------|
| Users | Accounts |
| Employees | Employee |
| Products | Inventory |
| Stock | Inventory |
| Raw Materials | Inventory |
| Production Orders | Furniture |
| Projects | Construction |
| Online Products | Ecommerce |
| Walk-in Sales | Sales |
| Accounting | Finance |

No duplicate ownership is allowed.

---

# 6. Communication Rules

Applications communicate only through business logic.

Example:

```

Furniture

↓

Inventory Service

↓

Stock Movement

↓

Inventory Updated

```

Never:

```

Furniture

↓

Direct Database Update

```

---

# 7. Business Logic Layer

Business logic should stay inside:

```

services.py

```

Examples:

Inventory Service

- Receive Stock
- Dispatch Stock
- Transfer Stock

Furniture Service

- Start Production
- Complete Production

Ecommerce Service

- Checkout
- Cart Management

Finance Service

- Record Payment
- Generate Journal

Views should call services.

---

# 8. Views Layer

Views are controllers.

Responsibilities:

- Receive Request
- Validate Form
- Call Service
- Render Response

Views should never contain complex business logic.

---

# 9. Models Layer

Models contain:

- Data
- Relationships
- Entity business rules

Example:

Product.current_stock

Order.total_cost

Quotation.total_price

Models should not contain workflow logic.

---

# 10. Dashboard Architecture

Dashboards never store business data.

Dashboard collects information from:

Inventory

Furniture

Sales

Finance

Construction

Employee

Dashboards are read-only.

---

# 11. Authentication Flow

```

Login

↓

Accounts

↓

Permissions

↓

Dashboard

```

Authorization is controlled by:

Role

↓

Permissions

↓

Modules

---

# 12. Customer Architecture

Customer accesses:

```

Homepage

↓

Shop

↓

Product Detail

↓

Cart

↓

Checkout

↓

Order History

```

Customer never accesses internal ERP modules.

---

# 13. Manager Architecture

Manager accesses:

Dashboard

↓

Inventory

↓

Furniture

↓

Construction

↓

Finance Reports

↓

Ecommerce Management

Manager has operational visibility.

---

# 14. Integration Architecture

Furniture

↓

Inventory

↓

Ecommerce

↓

Sales

↓

Finance

Every integration follows the Business Flow document.

---

# 15. Future API Architecture

Future applications:

Mobile App

Supplier Portal

Customer Portal

will communicate through REST APIs.

API layer sits above business services.

```

Mobile App

↓

REST API

↓

Services

↓

Database

```

---

# 16. Security Principles

Users access only authorized modules.

Every request requires:

Authentication

Authorization

Validation

Audit Logging (future)

---

# 17. Folder Architecture

Every module follows:

```

app/

models.py

views.py

urls.py

forms.py

admin.py

services.py

dashboard.py

signals.py (optional)

templates/

static/

tests/

```

---

# 18. Performance Principles

Use:

select_related()

prefetch_related()

database indexes

pagination

caching (future)

Avoid unnecessary database queries.

---

# 19. Scalability Strategy

Current:

SQLite

Future:

PostgreSQL

Redis

Celery

REST API

Docker

Cloud Deployment

Architecture must support migration without redesign.

---

# 20. Development Lifecycle

Business Analysis

↓

Blueprint

↓

Architecture Review

↓

Database Design

↓

Implementation

↓

Testing

↓

Documentation Update

↓

Deployment

---

# 21. Architecture Governance

All developers must follow:

- Blueprint
- Business Flows
- System Architecture

Any architectural change requires updating documentation before implementation.

---

# END OF DOCUMENT

**Version:** 1.0

**Status:** Approved

**Document Owner:** Wisdom Palace Group ERP