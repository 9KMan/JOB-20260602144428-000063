"""
Database connection utilities for SQL Server via ODBC.
Handles connection pooling and auto-creation of system tables.
"""
import pyodbc
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from utils.config import config
from utils.logging import setup_logger

logger = setup_logger(__name__)


class DatabaseConnection:
    """SQL Server database connection manager."""

    _instance = None
    _connection_string: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._build_connection_string()
        return cls._instance

    def _build_connection_string(self) -> None:
        """Build ODBC connection string from config."""
        db_config = config.get('database', 'sqlserver')

        if db_config.get('trusted_connection', 'no').lower() == 'yes':
            self._connection_string = (
                f"DRIVER={{{db_config['driver']}}};"
                f"SERVER={db_config['server']};"
                f"DATABASE={db_config['database']};"
                f"Trusted_Connection={db_config.get('trusted_connection', 'no')};"
            )
        else:
            self._connection_string = (
                f"DRIVER={{{db_config['driver']}}};"
                f"SERVER={db_config['server']};"
                f"DATABASE={db_config['database']};"
                f"UID={db_config['uid']};"
                f"PWD={db_config['pwd']};"
                f"Connection Timeout={db_config.get('timeout', 30)};"
            )

    @contextmanager
    def get_connection(self):
        """
        Get a database connection with context manager.

        Yields:
            pyodbc.Connection object
        """
        conn = None
        try:
            conn = pyodbc.connect(self._connection_string)
            yield conn
        except pyodbc.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a query with optional parameters.

        Args:
            query: SQL query string
            params: Optional query parameters
            fetch: Whether to fetch results (SELECT)

        Returns:
            List of rows as dicts if fetch=True, else None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch:
                    columns = [column[0] for column in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    return results
                else:
                    conn.commit()
                    return None
            except pyodbc.Error as e:
                logger.error(f"Query execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute a non-query (INSERT/UPDATE/DELETE).

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
            except pyodbc.Error as e:
                logger.error(f"Non-query execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()


# Singleton instance
db = DatabaseConnection()