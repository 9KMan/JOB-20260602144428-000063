"""
WebSocket Spool Processor Service
Processes spoolsed events from tbl_event_spool and applies to database.
"""
import sys
import time
import json
from datetime import datetime
from typing import Optional

from utils.config import config
from utils.logging import setup_logger
from db.connection import db
from db.system_tables import ensure_system_tables, register_service, log_execution, complete_execution, log_debug

logger = setup_logger(__name__)

SERVICE_NAME = "websocket_spool_processor"
SERVICE_TYPE = "WEBSOCKET_PROCESSOR"

MAX_RETRIES = 3
BATCH_SIZE = 50
POLL_INTERVAL = 5  # seconds


def create_dynamic_table(table_name: str, columns: dict) -> None:
    """
    Create a dynamic table for event data if it doesn't exist.

    Args:
        table_name: Name of table to create
        columns: Dict of column_name -> data_type
    """
    create_sql = f"""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}')
        BEGIN
            CREATE TABLE {table_name} (
                id INT IDENTITY(1,1) PRIMARY KEY,
                event_id NVARCHAR(100),
                event_type NVARCHAR(100),
                event_data NVARCHAR(MAX),
                processed_at DATETIME DEFAULT GETDATE(),
                INDEX idx_event_id (event_id),
                INDEX idx_event_type (event_type)
            )
        END
    """
    db.execute_non_query(create_sql)


def process_event(spool_id: str, event_data: dict, service_id: int, exec_id: int) -> bool:
    """
    Process a single spoolsed event.

    Args:
        spool_id: Spool identifier
        event_data: Event payload
        service_id: Service ID
        exec_id: Execution ID

    Returns:
        True if successful, False otherwise
    """
    event_type = event_data.get('event_type', 'UNKNOWN')
    table_name = f"tbl_events_{event_type.lower()}"

    try:
        # Create dynamic table for this event type if needed
        create_dynamic_table(table_name, {})

        # Insert event into type-specific table
        insert_sql = f"""
            INSERT INTO {table_name} (event_id, event_type, event_data)
            VALUES (?, ?, ?)
        """

        event_id = event_data.get('event_id', spool_id)
        event_json = json.dumps(event_data)

        db.execute_non_query(insert_sql, (event_id, event_type, event_json))

        # Mark spool as processed
        update_sql = """
            UPDATE tbl_event_spool
            SET processed = 1, processed_at = GETDATE()
            WHERE spool_id = ?
        """
        db.execute_non_query(update_sql, (spool_id,))

        log_debug(db, service_id, exec_id, "INFO",
                 f"Processed event {spool_id}", {'event_type': event_type})

        return True

    except Exception as e:
        logger.error(f"Failed to process event {spool_id}: {e}")

        # Increment retry count
        retry_sql = """
            UPDATE tbl_event_spool
            SET retry_count = retry_count + 1,
                error_message = ?
            WHERE spool_id = ?
        """
        db.execute_non_query(retry_sql, (str(e), spool_id))

        return False


def fetch_pending_events(batch_size: int = BATCH_SIZE) -> list:
    """
    Fetch pending events from spool table.

    Args:
        batch_size: Number of events to fetch

    Returns:
        List of (spool_id, event_data) tuples
    """
    query_sql = f"""
        SELECT TOP {batch_size} spool_id, event_data
        FROM tbl_event_spool
        WHERE processed = 0 AND retry_count < ?
        ORDER BY received_at ASC
    """

    rows = db.execute_query(query_sql, (MAX_RETRIES,))

    events = []
    if rows:
        for row in rows:
            try:
                event_data = json.loads(row['event_data'])
                events.append((row['spool_id'], event_data))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse event data for {row['spool_id']}: {e}")

    return events


def mark_failed_events(spool_ids: list) -> None:
    """
    Mark events that exceeded max retries as permanently failed.

    Args:
        spool_ids: List of spool IDs to mark
    """
    if not spool_ids:
        return

    placeholders = ','.join(['?' for _ in spool_ids])
    update_sql = f"""
        UPDATE tbl_event_spool
        SET processed = 2, processed_at = GETDATE()
        WHERE spool_id IN ({placeholders})
    """
    db.execute_non_query(update_sql, spool_ids)


def run_processor(poll_interval: int = POLL_INTERVAL) -> dict:
    """
    Run the processor loop.

    Args:
        poll_interval: Seconds between polling cycles

    Returns:
        Dict with processing statistics
    """
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'start_time': datetime.now()
    }

    service_id = register_service(db, SERVICE_NAME, SERVICE_TYPE,
                                  "Processes spoolsed WebSocket events")
    exec_id = log_execution(db, service_id, 'RUNNING', {'poll_interval': poll_interval})

    try:
        while True:
            events = fetch_pending_events()

            if not events:
                logger.debug("No pending events, waiting...")
                time.sleep(poll_interval)
                continue

            logger.info(f"Processing {len(events)} events")
            stats['total'] += len(events)

            failed_ids = []

            for spool_id, event_data in events:
                if process_event(spool_id, event_data, service_id, exec_id):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                    # Check if we should mark as permanently failed
                    check_sql = "SELECT retry_count FROM tbl_event_spool WHERE spool_id = ?"
                    result = db.execute_query(check_sql, (spool_id,))
                    if result and result[0].get('retry_count', 0) >= MAX_RETRIES:
                        failed_ids.append(spool_id)

            # Mark permanently failed events
            if failed_ids:
                mark_failed_events(failed_ids)
                logger.warning(f"Marked {len(failed_ids)} events as permanently failed")

            stats['end_time'] = datetime.now()

    except KeyboardInterrupt:
        logger.info("Processor stopped by user")
    except Exception as e:
        logger.error(f"Processor error: {e}")
        complete_execution(db, exec_id, 'FAILED', stats['success'], str(e))
        stats['error'] = str(e)

    if 'error' not in stats:
        status = 'SUCCESS' if stats['failed'] == 0 else 'PARTIAL' if stats['success'] > 0 else 'FAILED'
        complete_execution(db, exec_id, status, stats['success'],
                          f"Failed: {stats['failed']}" if stats['failed'] > 0 else None)

    return stats


def main():
    """Main entry point."""
    logger.info(f"Starting {SERVICE_NAME}...")

    # Ensure system tables exist
    ensure_system_tables(db)

    stats = run_processor()

    logger.info(f"Processor finished. Stats: {stats}")
    return 0 if stats.get('failed', 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())