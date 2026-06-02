# GTN Trade API & WebSocket Integration — Python Backend

**Lead:** https://www.upwork.com/jobs/~022061767919755273499
**Client:** GTN Trade API Integration
**Tier:** MEDIUM | **Budget:** hourly ($15-35/hr, <30hrs/wk, <1mo, contract-to-hire)

---

## 🎯 Business Problem Solved

GTN needs three Python services to integrate with their proprietary Trade API and WebSocket, synchronizing trading/account data into SQL Server with zero data loss and full audit traceability.

**Pain:** Manual data entry across disconnected systems — GTN's trading platform, WebSocket feed, and SQL Server database were not connected. Traders lacked real-time visibility into open/closed trades, account balances, and portfolio positions.

**Solution delivered:** Three production-grade Python services that:
1. **API Import Service** — pulls Order Search data from GTN Trade API and upserts into SQL Server business tables with dynamic schema migration
2. **WebSocket Listener** — continuously ingests real-time GTN Trade Events WebSocket into a spool table, with auto-reconnect and debug logging
3. **Spool Processor** — processes spooled messages, routes to correct business tables (open_trades, closed_trades, accounts, etc.), and maintains a full audit log

**Data model:** `gtn_open_trades`, `gtn_closed_trades`, `gtn_bank_accounts`, `gtn_cash_accounts`, `gtn_customer_accounts`, `gtn_exchange_accounts`, `gtn_security_accounts`, `gtn_websocket_spool`, `gtn_websocket_spool_log` + system tables `tbl_system_service`, `tbl_system_service_exec`, `tbl_system_service_debug`

**Key differentiators:** Zero-downtime on bad records, dynamic column addition, comprehensive audit logging, ODBC connection management, and production-grade error handling.

---

## Quick Start

```bash
# Service 1: API Import
python get_orders_api.py \
  --sql-server "DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=GTN;UID=admin;PWD=xxx" \
  --insert-db-name GTN \
  --uid-service GTN_GET_ORDERS

# Service 2: WebSocket Listener
python websocket_spool_listener.py \
  --sql-server "..." --insert-db-name GTN --uid-service GTN_WEBSOCKET

# Service 3: Spool Processor
python websocket_spool_processor.py \
  --sql-server "..." --insert-db-name GTN --uid-service GTN_WEBSOCKET
```

## Tech Stack

`python` · `sql-server` · `odbc` · `websockets` · `api-integration` · `json` · `rest-api` · `etl` · `audit-logging`

## Architecture

- **Service 1 (get_orders_api.py):** Scheduled/ondemand API import → dynamic SQL upsert
- **Service 2 (websocket_spool_listener.py):** Persistent WebSocket connection → raw spool table
- **Service 3 (websocket_spool_processor.py):** Polls unprocessed spool → routes to business tables → audit log

All services write to `tbl_system_service_debug`, track execution time in `tbl_system_service_exec`, and survive individual record failures without crashing.

## Project Structure

```
├── SPEC.md                          ← this file
├── README.md                        ← you are here
├── get_orders_api.py                ← File 1: GTN Order Search API import
├── websocket_spool_listener.py     ← File 2: WebSocket → spool table
├── websocket_spool_processor.py    ← File 3: Process spool → business tables
├── requirements.txt                 ← pyodbc, websocket-client, requests, msal
└── sql/
    └── init_tables.sql             ← DDL for all business + system tables
```