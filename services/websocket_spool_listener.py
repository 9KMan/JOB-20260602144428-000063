"""
WebSocket Spool Listener Service
Connects to GTN WebSocket and spools events to SQL Server for processing.
"""
import sys
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

import websockets

from utils.config import config
from utils.logging import setup_logger
from db.connection import db
from db.system_tables import ensure_system_tables, register_service, log_execution, complete_execution, log_debug

logger = setup_logger(__name__)

SERVICE_NAME = "websocket_spool_listener"
SERVICE_TYPE = "WEBSOCKET_LISTENER"


class WebSocketListener:
    """GTN WebSocket event listener with spooling."""

    def __init__(self):
        self.ws_url = config.get('gtn', 'websocket', 'url')
        self.reconnect_delay = config.get('gtn', 'websocket', 'reconnect_delay', default=5)
        self.ping_interval = config.get('gtn', 'websocket', 'ping_interval', default=30)
        self.running = False
        self.connection = None

    async def connect(self):
        """Establish WebSocket connection."""
        logger.info(f"Connecting to {self.ws_url}")
        self.connection = await websockets.connect(self.ws_url)
        logger.info("WebSocket connected")
        return self.connection

    async def receive_events(self):
        """Receive and spool events from WebSocket."""
        service_id = register_service(db, SERVICE_NAME, SERVICE_TYPE,
                                      "Listens to GTN WebSocket and spools events")
        exec_id = log_execution(db, service_id, 'RUNNING', {'ws_url': self.ws_url})

        try:
            self.running = True
            event_count = 0

            while self.running:
                try:
                    message = await asyncio.wait_for(
                        self.connection.recv(),  # type: ignore
                        timeout=self.ping_interval + 10
                    )

                    event_data = json.loads(message)
                    spool_id = str(uuid.uuid4())

                    # Spool event to database
                    self._spool_event(spool_id, event_data, service_id, exec_id)
                    event_count += 1

                    log_debug(db, service_id, exec_id, "DEBUG",
                             f"Spooled event {spool_id}", event_data)

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if self.connection:
                        await self.connection.ping()  # type: ignore
                    logger.debug("Ping sent")

                except websockets.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    break

            complete_execution(db, exec_id, 'SUCCESS' if event_count > 0 else 'PARTIAL',
                             event_count, "No events received" if event_count == 0 else None)

        except Exception as e:
            logger.error(f"Listener error: {e}")
            complete_execution(db, exec_id, 'FAILED', event_count, str(e))
            if event_count is None:
                event_count = 0

    def _spool_event(self, spool_id: str, event_data: dict, service_id: int, exec_id: int):
        """
        Save event to spool table for later processing.

        Args:
            spool_id: Unique spool identifier
            event_data: Event payload
            service_id: Service ID
            exec_id: Execution ID
        """
        # Ensure spool table exists
        create_table_sql = """
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_event_spool')
            BEGIN
                CREATE TABLE tbl_event_spool (
                    spool_id NVARCHAR(100) PRIMARY KEY,
                    event_type NVARCHAR(100),
                    event_data NVARCHAR(MAX),
                    received_at DATETIME DEFAULT GETDATE(),
                    processed BIT DEFAULT 0,
                    processed_at DATETIME,
                    retry_count INT DEFAULT 0,
                    error_message NVARCHAR(MAX),
                    INDEX idx_processed (processed, received_at)
                )
            END
        """
        db.execute_non_query(create_table_sql)

        # Insert spool record
        insert_sql = """
            INSERT INTO tbl_event_spool (spool_id, event_type, event_data)
            VALUES (?, ?, ?)
        """

        event_type = event_data.get('event_type', 'UNKNOWN')
        event_json = json.dumps(event_data)

        db.execute_non_query(insert_sql, (spool_id, event_type, event_json))

    async def disconnect(self):
        """Close WebSocket connection."""
        if self.connection:
            await self.connection.close()
            logger.info("WebSocket disconnected")

    def stop(self):
        """Signal listener to stop."""
        self.running = False


async def run_listener():
    """Run the WebSocket listener."""
    listener = WebSocketListener()

    while True:
        try:
            await listener.connect()
            await listener.receive_events()
        except websockets.ConnectionClosed:
            logger.warning("Connection lost, reconnecting...")
        except Exception as e:
            logger.error(f"Listener error: {e}")

        logger.info(f"Reconnecting in {listener.reconnect_delay} seconds...")
        await asyncio.sleep(listener.reconnect_delay)


def main():
    """Main entry point."""
    logger.info(f"Starting {SERVICE_NAME}...")

    # Ensure system tables exist
    ensure_system_tables(db)

    try:
        asyncio.run(run_listener())
    except KeyboardInterrupt:
        logger.info("Listener stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Listener failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())