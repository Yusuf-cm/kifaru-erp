# Kifaru customer readiness

Updated the shared interface with a forest sidebar, warm paper workspace, quieter cards, clearer data hierarchy, keyboard focus and mobile navigation labels.

Fixed reverse-proxy HTTPS recognition and Render CSRF origins. POS uses authoritative catalogue prices, rejects invalid/non-finite/negative quantities, inactive products/warehouses, duplicate rows and invalid payment methods.

Validation: 21 Django tests, including stock/ledger completion, rollback on invalid checkout and authenticated page rendering.

Live service is suspended. Paid Postgres cutover needs owner connection and source backup/restore before service resumption. Multi-tenant business isolation is not implemented; this is a single-business ERP. Role separation and concurrent sale locking remain areas to verify before a broader public launch.
