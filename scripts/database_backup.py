#!/usr/bin/env python3
"""
Database backup and restore utilities for Expense Tracker MySQL database.

This script provides:
- Automated database backups with compression and rotation
- Database restore functionality
- Backup validation and verification
- Environment-aware configuration
"""

import os
import sys
import subprocess
import gzip
import shutil
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse

from dotenv import load_dotenv


class DatabaseBackup:
    """MySQL database backup and restore manager."""
    
    def __init__(self, backup_dir: str = "backups"):
        load_dotenv()
        
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Database configuration from environment
        self.db_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": os.getenv("MYSQL_PORT", "3306"),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "expense_tracker")
        }
        
        # Backup configuration
        self.retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.max_backups = int(os.getenv("MAX_BACKUP_COUNT", "50"))
        
    def create_backup(self, backup_name: Optional[str] = None, compress: bool = True) -> Dict[str, Any]:
        """
        Create a database backup.
        
        Args:
            backup_name: Custom backup name (default: timestamp-based)
            compress: Whether to compress the backup file
            
        Returns:
            Dict containing backup information
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"expense_tracker_backup_{timestamp}"
        
        # Determine file extension
        ext = ".sql.gz" if compress else ".sql"
        backup_file = self.backup_dir / f"{backup_name}{ext}"
        
        print(f"🗄️  Creating database backup: {backup_file}")
        
        try:
            # Prepare mysqldump command
            cmd = [
                "mysqldump",
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                "--single-transaction",
                "--routines",
                "--triggers",
                "--complete-insert",
                "--extended-insert",
                "--add-drop-table",
                "--create-options",
                "--disable-keys",
                "--set-charset",
                self.db_config["database"]
            ]
            
            # Add password if provided
            if self.db_config["password"]:
                cmd.append(f"--password={self.db_config['password']}")
            
            # Execute mysqldump
            print(f"Running: {' '.join(cmd[:-1])} [password hidden] {cmd[-1]}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Write backup file
            backup_data = result.stdout.encode('utf-8')
            
            if compress:
                with gzip.open(backup_file, 'wb') as f:
                    f.write(backup_data)
            else:
                with open(backup_file, 'wb') as f:
                    f.write(backup_data)
            
            # Calculate file hash for verification
            file_hash = self._calculate_file_hash(backup_file)
            file_size = backup_file.stat().st_size
            
            # Create backup metadata
            metadata = {
                "backup_name": backup_name,
                "file_path": str(backup_file),
                "timestamp": datetime.now().isoformat(),
                "database": self.db_config["database"],
                "compressed": compress,
                "file_size": file_size,
                "file_hash": file_hash,
                "mysql_version": self._get_mysql_version(),
                "tables_backed_up": self._get_table_list()
            }
            
            # Save metadata
            metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Backup created successfully!")
            print(f"   File: {backup_file}")
            print(f"   Size: {self._format_size(file_size)}")
            print(f"   Hash: {file_hash[:16]}...")
            
            return metadata
            
        except subprocess.CalledProcessError as e:
            error_msg = f"mysqldump failed: {e.stderr}"
            print(f"❌ Backup failed: {error_msg}")
            
            # Clean up partial backup
            if backup_file.exists():
                backup_file.unlink()
            
            raise Exception(error_msg)
        except Exception as e:
            print(f"❌ Backup failed: {str(e)}")
            raise
    
    def restore_backup(self, backup_file: str, force: bool = False) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_file: Path to backup file
            force: Skip confirmation prompt
            
        Returns:
            True if restore successful
        """
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False
        
        # Load and validate metadata
        metadata_file = backup_path.with_suffix(backup_path.suffix + '.meta')
        metadata = None
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Verify backup integrity
            if not self._verify_backup_integrity(backup_path, metadata):
                print("❌ Backup integrity check failed!")
                return False
        
        # Confirmation prompt
        if not force:
            print(f"⚠️  WARNING: This will replace the current database '{self.db_config['database']}'")
            print(f"   Backup file: {backup_path}")
            if metadata:
                print(f"   Backup date: {metadata.get('timestamp')}")
                print(f"   Tables: {len(metadata.get('tables_backed_up', []))}")
            
            confirm = input("Are you sure you want to proceed? (yes/no): ").lower()
            if confirm != 'yes':
                print("Restore cancelled.")
                return False
        
        print(f"🔄 Restoring database from: {backup_path}")
        
        try:
            # Read backup data
            if backup_path.suffix == '.gz':
                with gzip.open(backup_path, 'rt') as f:
                    backup_data = f.read()
            else:
                with open(backup_path, 'r') as f:
                    backup_data = f.read()
            
            # Prepare mysql command
            cmd = [
                "mysql",
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                self.db_config["database"]
            ]
            
            # Add password if provided
            if self.db_config["password"]:
                cmd.append(f"--password={self.db_config['password']}")
            
            # Execute mysql restore
            result = subprocess.run(
                cmd,
                input=backup_data,
                text=True,
                capture_output=True,
                check=True
            )
            
            print("✅ Database restored successfully!")
            
            # Verify restoration
            if metadata and self._verify_restoration(metadata):
                print("✅ Restoration verified - table counts match")
            
            return True
            
        except subprocess.CalledProcessError as e:
            error_msg = f"mysql restore failed: {e.stderr}"
            print(f"❌ Restore failed: {error_msg}")
            return False
        except Exception as e:
            print(f"❌ Restore failed: {str(e)}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups with metadata."""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            if backup_file.suffix in ['.sql', '.gz']:
                metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        backups.append(metadata)
                    except:
                        # Fallback to basic file info
                        backups.append({
                            "backup_name": backup_file.stem,
                            "file_path": str(backup_file),
                            "timestamp": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                            "file_size": backup_file.stat().st_size,
                            "compressed": backup_file.suffix == '.gz'
                        })
        
        # Sort by timestamp (newest first)
        return sorted(backups, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def cleanup_old_backups(self) -> int:
        """Remove old backups based on retention policy."""
        print(f"🧹 Cleaning up backups older than {self.retention_days} days...")
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        backups = self.list_backups()
        
        # Sort by timestamp and keep only the most recent ones
        if len(backups) > self.max_backups:
            backups_to_remove = backups[self.max_backups:]
            print(f"🗑️  Removing {len(backups_to_remove)} backups (exceeds max count of {self.max_backups})")
            
            for backup in backups_to_remove:
                self._remove_backup_files(backup['file_path'])
                removed_count += 1
        
        # Remove old backups
        for backup in backups:
            backup_time = datetime.fromisoformat(backup['timestamp'].replace('Z', '+00:00'))
            if backup_time < cutoff_date:
                print(f"🗑️  Removing old backup: {backup['backup_name']}")
                self._remove_backup_files(backup['file_path'])
                removed_count += 1
        
        print(f"✅ Cleaned up {removed_count} old backups")
        return removed_count
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _verify_backup_integrity(self, backup_path: Path, metadata: Dict[str, Any]) -> bool:
        """Verify backup file integrity using stored hash."""
        try:
            current_hash = self._calculate_file_hash(backup_path)
            stored_hash = metadata.get('file_hash')
            
            if current_hash == stored_hash:
                print("✅ Backup integrity verified")
                return True
            else:
                print(f"❌ Hash mismatch: expected {stored_hash[:16]}..., got {current_hash[:16]}...")
                return False
        except Exception as e:
            print(f"⚠️  Could not verify backup integrity: {e}")
            return True  # Don't block restore if verification fails
    
    def _verify_restoration(self, metadata: Dict[str, Any]) -> bool:
        """Verify restoration by checking table counts."""
        try:
            tables = self._get_table_list()
            backed_up_tables = metadata.get('tables_backed_up', [])
            
            return set(tables) == set(backed_up_tables)
        except:
            return False
    
    def _get_mysql_version(self) -> str:
        """Get MySQL server version."""
        try:
            cmd = [
                "mysql",
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                "--skip-column-names",
                "--batch",
                "-e", "SELECT VERSION();"
            ]
            
            if self.db_config["password"]:
                cmd.append(f"--password={self.db_config['password']}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _get_table_list(self) -> List[str]:
        """Get list of tables in the database."""
        try:
            cmd = [
                "mysql",
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--user={self.db_config['user']}",
                "--skip-column-names",
                "--batch",
                "-e", f"SHOW TABLES FROM {self.db_config['database']};"
            ]
            
            if self.db_config["password"]:
                cmd.append(f"--password={self.db_config['password']}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except:
            return []
    
    def _remove_backup_files(self, backup_path: str):
        """Remove backup and associated metadata files."""
        backup_file = Path(backup_path)
        metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
        
        if backup_file.exists():
            backup_file.unlink()
        if metadata_file.exists():
            metadata_file.unlink()
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    parser.add_argument("--backup-dir", default="backups", help="Backup directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--name", help="Custom backup name")
    backup_parser.add_argument("--no-compress", action="store_true", help="Don't compress backup")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("backup_file", help="Path to backup file")
    restore_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup_manager = DatabaseBackup(args.backup_dir)
    
    try:
        if args.command == "backup":
            result = backup_manager.create_backup(
                backup_name=args.name,
                compress=not args.no_compress
            )
            print(f"\n📄 Backup metadata saved to: {result['file_path']}.meta")
            
        elif args.command == "restore":
            success = backup_manager.restore_backup(args.backup_file, args.force)
            sys.exit(0 if success else 1)
            
        elif args.command == "list":
            backups = backup_manager.list_backups()
            
            if not backups:
                print("No backups found.")
                return
            
            print(f"\n📋 Available backups ({len(backups)}):")
            print("-" * 80)
            
            for backup in backups:
                timestamp = backup.get('timestamp', 'Unknown')
                name = backup.get('backup_name', 'Unknown')
                size = backup_manager._format_size(backup.get('file_size', 0))
                compressed = " (compressed)" if backup.get('compressed') else ""
                
                print(f"📁 {name}")
                print(f"   📅 {timestamp}")
                print(f"   📂 {backup['file_path']}")
                print(f"   💾 {size}{compressed}")
                print()
            
        elif args.command == "cleanup":
            removed = backup_manager.cleanup_old_backups()
            print(f"🎉 Cleanup complete! Removed {removed} old backups.")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
