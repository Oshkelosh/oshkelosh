from pathlib import Path
from typing import Union

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .defaults import default_list

# SQLAlchemy database instance
db = SQLAlchemy()


def ensure_db_directory(app_or_uri: Union[Flask, str]) -> None:
    """
    Ensure the parent directory exists for SQLite database files.
    
    For SQLite databases, creates the parent directory if it doesn't exist.
    For other database types, this is a no-op.
    
    Args:
        app_or_uri: Flask app instance or database URI string
    """
    # Extract URI from Flask app or use provided string
    if isinstance(app_or_uri, Flask):
        uri = app_or_uri.config.get("SQLALCHEMY_DATABASE_URI", "")
    else:
        uri = app_or_uri
    
    # Only handle SQLite databases
    if not uri.startswith("sqlite:///"):
        return
    
    # Extract file path from SQLite URI
    # sqlite:///path/to/db.db or sqlite:////absolute/path/to/db.db
    file_path_str = uri.replace("sqlite:///", "", 1)
    
    # Handle absolute paths (sqlite:////absolute/path)
    if file_path_str.startswith("/"):
        db_path = Path(file_path_str)
    else:
        # Relative path - resolve from current working directory
        db_path = Path(file_path_str).resolve()
    
    # Create parent directory if it doesn't exist
    parent_dir = db_path.parent
    if parent_dir and not parent_dir.exists():
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"Failed to create database directory '{parent_dir}': {e}. "
                f"Please ensure you have write permissions for this location."
            ) from e
