# WPG BOS — Module Dependency Map

Version: 1.0 Draft

## Core Rule

No module should work alone.  
Every module must connect to Core Engine, Master Data, Finance, Inventory, and Reporting where applicable.

## accounts

Depends on:

- core
- Employee
- finance
- orders
- all modules

Used for:

- Authentication
- User management
- Role-based access

## core

Contains:

- Module
- RoleModule
- Workflow
- Approval
- Audit
- Notification

Used by all modules.

## inventory

Depends on:

- products
- raw materials
- warehouses
- stock movements
- assets

Used by:

- ecommerce
- furniture
- construction
- agriculture
- procurement

## orders

Handles:

- ecommerce orders
- custom furniture orders
- restock orders
- new product orders
- POS orders

Connects to:

- inventory
- furniture
- ecommerce
- finance
- marketplace

## furniture

Depends on:

- orders.Order
- inventory.Product
- inventory.RawMaterial
- Employee.Employee
- inventory.StockMovement

Handles:

- production jobs
- quotations
- materials
- labour
- machines
- production output

## construction

Depends on:

- projects
- clients
- materials
- assets
- labour
- finance
- furniture products

Handles:

- blueprints
- interior design
- construction projects
- maintenance
- real estate development

## finance

Depends on:

- business units
- income
- expense
- receivables
- payables
- payments
- treasury
- investor reporting

Used by all business units.

## ecommerce

Depends on:

- inventory.Product
- orders.Order
- orders.OrderItem
- customers
- payments

Handles:

- online store
- cart
- checkout
- customer orders
- marketplace sales

## agriculture

Future module.

Will depend on:

- poultry batches
- feed inventory
- egg production
- mortality
- sales
- finance