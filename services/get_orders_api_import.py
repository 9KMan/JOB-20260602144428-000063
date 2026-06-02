"""
Get Orders API Import Service
Fetches orders from GTN Trade API and imports into SQL Server.
"""
import sys
import time
from datetime import datetime, timedelta
import uuid

from utils.config import config
from utils.logging import setup_logger
from db.connection import db
from db.system_tables import ensure_system_tables, register_service, log_execution, complete_execution, log_debug
from services.gtn_api_client import GTNApiClient
from models.gtn_order import Order

logger = setup_logger(__name__)

SERVICE_NAME = "get_orders_api_import"
SERVICE_TYPE = "API_IMPORT"


def import_order(order: Order, exec_id: int) -> bool:
    """
    Import a single order into SQL Server.

    Args:
        order: Order object to import
        exec_id: Execution ID for logging

    Returns:
        True if successful, False otherwise
    """
    try:
        import json

        # Dynamic schema: create order-specific table if needed
        table_name = f"tbl_orders_{order.status.lower()}" if order.status else "tbl_orders"

        # Insert into orders table (using dynamic table name)
        insert_sql = f"""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_orders')
            BEGIN
                CREATE TABLE tbl_orders (
                    order_id NVARCHAR(100) PRIMARY KEY,
                    order_number NVARCHAR(50),
                    customer_id NVARCHAR(100),
                    order_date DATETIME,
                    status NVARCHAR(50),
                    total_amount DECIMAL(18,2),
                    currency NVARCHAR(10),
                    shipping_address NVARCHAR(MAX),
                    billing_address NVARCHAR(MAX),
                    payment_method NVARCHAR(50),
                    payment_status NVARCHAR(50),
                    shipping_method NVARCHAR(50),
                    tracking_number NVARCHAR(100),
                    notes NVARCHAR(MAX),
                    order_data NVARCHAR(MAX),
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
            END
        """
        db.execute_non_query(insert_sql)

        # Insert/update order
        upsert_sql = """
            MERGE INTO tbl_orders AS target
            USING (SELECT ? as order_id) AS source
            ON target.order_id = source.order_id
            WHEN MATCHED THEN
                UPDATE SET updated_at = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (order_id, order_number, customer_id, order_date, status, total_amount,
                       currency, shipping_address, billing_address, payment_method, payment_status,
                       shipping_method, tracking_number, notes, order_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        shipping_addr = json.dumps(order.shipping_address) if order.shipping_address else None
        billing_addr = json.dumps(order.billing_address) if order.billing_address else None
        order_data = json.dumps(order.model_dump(mode='json')) if hasattr(order, 'model_dump') else json.dumps({
            'order_id': order.order_id,
            'status': order.status,
            'total_amount': order.total_amount
        })

        db.execute_non_query(upsert_sql, (
            order.order_id,
            order.order_id,
            order.order_number,
            order.customer_id,
            order.order_date,
            order.status,
            order.total_amount,
            order.currency,
            shipping_addr,
            billing_addr,
            order.payment_method,
            order.payment_status,
            order.shipping_method,
            order.tracking_number,
            order.notes,
            order_data
        ))

        log_debug(db, register_service(db, SERVICE_NAME, SERVICE_TYPE), exec_id, "INFO",
                 f"Imported order {order.order_id}")

        return True

    except Exception as e:
        logger.error(f"Failed to import order {order.order_id}: {e}")
        log_debug(db, register_service(db, SERVICE_NAME, SERVICE_TYPE), exec_id, "ERROR",
                 f"Failed import: {str(e)}", {'order_id': order.order_id})
        return False


def run_import(date_from: datetime = None, date_to: datetime = None) -> dict:
    """
    Run the import process.

    Args:
        date_from: Start date for order search
        date_to: End date for order search

    Returns:
        Dict with import statistics
    """
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'start_time': datetime.now()
    }

    service_id = register_service(db, SERVICE_NAME, SERVICE_TYPE,
                                  "Fetches orders from GTN API and imports to SQL Server")
    exec_id = log_execution(db, service_id, 'RUNNING', {'date_from': str(date_from), 'date_to': str(date_to)})

    try:
        client = GTNApiClient()

        # Default to last 24 hours if no dates specified
        if date_from is None:
            date_from = datetime.now() - timedelta(hours=24)
        if date_to is None:
            date_to = datetime.now()

        logger.info(f"Importing orders from {date_from} to {date_to}")

        orders = client.fetch_orders_batch(date_from, date_to)
        stats['total'] = len(orders)

        logger.info(f"Found {stats['total']} orders to import")

        for order in orders:
            if import_order(order, exec_id):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        stats['end_time'] = datetime.now()
        status = 'SUCCESS' if stats['failed'] == 0 else 'PARTIAL' if stats['success'] > 0 else 'FAILED'

        complete_execution(db, exec_id, status, stats['success'],
                          f"Failed: {stats['failed']}" if stats['failed'] > 0 else None)

        logger.info(f"Import complete: {stats}")

    except Exception as e:
        logger.error(f"Import failed: {e}")
        complete_execution(db, exec_id, 'FAILED', stats['success'], str(e))
        stats['error'] = str(e)

    return stats


def main():
    """Main entry point for the service."""
    logger.info(f"Starting {SERVICE_NAME} service...")

    # Ensure system tables exist
    ensure_system_tables(db)

    # Run import
    stats = run_import()

    logger.info(f"Service finished. Stats: {stats}")
    return 0 if stats.get('failed', 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())