"""
System tables auto-creation and management.
Creates: tbl_system_service, tbl_system_service_exec, tbl_system_service_debug
"""
from typing import Optional, Dict, Any
from utils.logging import setup_logger

logger = setup_logger(__name__)


SYSTEM_TABLES = {
    "tbl_system_service": """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_system_service')
        BEGIN
            CREATE TABLE tbl_system_service (
                service_id INT IDENTITY(1,1) PRIMARY KEY,
                service_name VARCHAR(100) NOT NULL UNIQUE,
                service_type VARCHAR(50) NOT NULL,
                description VARCHAR(500),
                status VARCHAR(20) NOT NULL DEFAULT 'STOPPED',
                config JSON,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE(),
                last_heartbeat DATETIME,
                CONSTRAINT chk_status CHECK (status IN ('RUNNING', 'STOPPED', 'ERROR', 'PAUSED'))
            );
        END
    """,

    "tbl_system_service_exec": """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_system_service_exec')
        BEGIN
            CREATE TABLE tbl_system_service_exec (
                exec_id INT IDENTITY(1,1) PRIMARY KEY,
                service_id INT NOT NULL FOREIGN KEY REFERENCES tbl_system_service(service_id),
                exec_start DATETIME NOT NULL,
                exec_end DATETIME,
                exec_status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
                records_processed INT DEFAULT 0,
                error_message VARCHAR(MAX),
                exec_details JSON,
                created_at DATETIME DEFAULT GETDATE()
            );
        END
    """,

    "tbl_system_service_debug": """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_system_service_debug')
        BEGIN
            CREATE TABLE tbl_system_service_debug (
                debug_id INT IDENTITY(1,1) PRIMARY KEY,
                service_id INT,
                exec_id INT,
                log_level VARCHAR(20) NOT NULL,
                log_message VARCHAR(MAX) NOT NULL,
                log_data JSON,
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (service_id) REFERENCES tbl_system_service(service_id),
                FOREIGN KEY (exec_id) REFERENCES tbl_system_service_exec(exec_id)
            );
        END
    """
}


def ensure_system_tables(db) -> None:
    """
    Ensure all system tables exist, creating them if necessary.

    Args:
        db: DatabaseConnection instance
    """
    logger.info("Checking system tables existence...")

    for table_name, create_sql in SYSTEM_TABLES.items():
        try:
            # SQL Server uses IF NOT EXISTS in a different way
            check_sql = f"""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}')
                BEGIN
                    EXEC sp_executesql @statement = N'{create_sql.replace("'", "''")}'
                END
            """
            db.execute_non_query(check_sql)
            logger.info(f"System table '{table_name}' is ready")
        except Exception as e:
            logger.warning(f"Could not create '{table_name}': {e}")


def register_service(db, service_name: str, service_type: str, description: Optional[str] = None) -> int:
    """
    Register a service in tbl_system_service.

    Args:
        db: DatabaseConnection instance
        service_name: Unique service identifier
        service_type: Service type (e.g., 'API_IMPORT', 'WEBSOCKET_LISTENER')
        description: Optional service description

    Returns:
        service_id (int)
    """
    check_sql = "SELECT service_id FROM tbl_system_service WHERE service_name = ?"
    existing = db.execute_query(check_sql, (service_name,))

    if existing:
        logger.info(f"Service '{service_name}' already registered with id {existing[0]['service_id']}")
        return existing[0]['service_id']

    insert_sql = """
        INSERT INTO tbl_system_service (service_name, service_type, description, status)
        VALUES (?, ?, ?, 'STOPPED');
        SELECT SCOPE_IDENTITY() as service_id;
    """

    result = db.execute_query(insert_sql, (service_name, service_type, description))
    service_id = int(result[0]['service_id']) if result and result[0]['service_id'] else 0

    logger.info(f"Registered service '{service_name}' with id {service_id}")
    return service_id


def log_execution(db, service_id: int, status: str = 'RUNNING', details: dict = None) -> int:
    """
    Log an execution start in tbl_system_service_exec.

    Args:
        db: DatabaseConnection instance
        service_id: Service ID
        status: Execution status
        details: Optional execution details

    Returns:
        exec_id
    """
    insert_sql = """
        INSERT INTO tbl_system_service_exec (service_id, exec_start, exec_status, exec_details)
        VALUES (?, GETDATE(), ?, ?);
        SELECT SCOPE_IDENTITY() as exec_id;
    """

    import json
    details_json = json.dumps(details) if details else "{}"
    result = db.execute_query(insert_sql, (service_id, status, details_json))
    return result[0]['exec_id'] if result else None


def complete_execution(db, exec_id: int, status: str, records_processed: int = 0, error_message: str = None) -> None:
    """
    Mark an execution as complete.

    Args:
        db: DatabaseConnection instance
        exec_id: Execution ID
        status: Final status (SUCCESS, FAILED, PARTIAL)
        records_processed: Number of records processed
        error_message: Optional error message
    """
    update_sql = """
        UPDATE tbl_system_service_exec
        SET exec_end = GETDATE(),
            exec_status = ?,
            records_processed = ?,
            error_message = ?
        WHERE exec_id = ?
    """
    db.execute_non_query(update_sql, (status, records_processed, error_message, exec_id))


def log_debug(db, service_id: int, exec_id: int, level: str, message: str, data: dict = None) -> None:
    """
    Log a debug message to tbl_system_service_debug.

    Args:
        db: DatabaseConnection instance
        service_id: Service ID
        exec_id: Execution ID
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        message: Log message
        data: Optional additional data
    """
    import json
    insert_sql = """
        INSERT INTO tbl_system_service_debug (service_id, exec_id, log_level, log_message, log_data)
        VALUES (?, ?, ?, ?, ?)
    """
    data_json = json.dumps(data) if data else None
    db.execute_non_query(insert_sql, (service_id, exec_id, level, message, data_json))