"""
Data Versioning Script for loader
=================================
This script:
1. Exports PostgreSQL tables to SQL files
2. Tracks exports with DVC
3. Commits to Git
4. Pushes to GCS
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up to ac215_NewsJuice/
DATA_DIR = PROJECT_ROOT / "data" / "exports"
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "data_versioning"

# Database configuration
# DB_HOST = "/cloudsql/newsjuice-123456:us-central1:newsdb-instance"
DB_HOST = os.environ.get("PGHOST", "127.0.0.1")
DB_PORT = int(os.environ.get("PGPORT", "5432"))
DB_USER = "postgres"
DB_NAME = "newsdb"
DB_PASSWORD = os.environ.get("DB_PASS", "Newsjuice25+")
# DB_PASSWORD = os.environ.get("DB_PASS")  # set in shell; optional

# Tables to export
TABLES_TO_EXPORT = ["articles", "chunks_vector"]


def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Step: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Success: {description}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {description}")
        print(f"Error message: {e.stderr}")
        raise


def export_database():
    """Step 1: Export PostgreSQL tables to SQL file"""

    # Create timestamp for version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Create export filename
    export_file = DATA_DIR / f"db_export_{timestamp}.sql"

    print(f"\n🗄️  Exporting database tables to: {export_file}")

    # Build pg_dump command
    # This exports both tables with data and schema
    # cmd = [
    #    "pg_dump",
    #    f"-h{DB_HOST}",
    #    f"-U{DB_USER}",
    #    f"-d{DB_NAME}",
    # ]

    cmd = [
        "pg_dump",
        "-h",
        DB_HOST,
        "-p",
        str(DB_PORT),
        "-U",
        DB_USER,
        "-d",
        DB_NAME,
    ]

    # Add each table
    for table in TABLES_TO_EXPORT:
        cmd.extend(["-t", table])

    # Add output options
    cmd.extend(
        [
            "--data-only",  # Only data, not schema
            "--column-inserts",  # Use INSERT statements (more readable)
            "-f",
            str(export_file),  # Output file
        ]
    )

    # Set password environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD

    # Run export
    result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

    print(f"✓ Database exported successfully")
    print(f"  File size: {export_file.stat().st_size / 1024 / 1024:.2f} MB")

    return export_file, timestamp


def track_with_dvc(export_file):
    """Step 2: Track the export file with DVC"""

    print(f"\n📊 Tracking {export_file.name} with DVC")

    # Add file to DVC tracking
    # This creates a .dvc file (small pointer) and adds actual file to .gitignore
    run_command(
        ["dvc", "add", str(export_file)], f"Add {export_file.name} to DVC tracking"
    )

    # DVC creates:
    # - data/exports/db_export_20251112_143000.sql.dvc (small pointer file)
    # - Adds db_export_20251112_143000.sql to .gitignore

    dvc_file = Path(str(export_file) + ".dvc")
    print(f"✓ Created DVC pointer file: {dvc_file}")

    return dvc_file


def commit_to_git(dvc_file, timestamp):
    """Step 3: Commit the DVC pointer file to Git"""

    print(f"\n📝 Committing to Git")

    # Stage the .dvc file (not the actual data!)
    run_command(["git", "add", str(dvc_file)], "Stage DVC pointer file")

    # Also stage .gitignore changes
    gitignore_file = dvc_file.parent / ".gitignore"
    if gitignore_file.exists():
        run_command(["git", "add", str(gitignore_file)], "Stage .gitignore updates")

    # Commit with descriptive message
    commit_message = f"Data version {timestamp}"
    run_command(["git", "commit", "-m", commit_message], f"Commit version {timestamp}")

    print(f"✓ Committed to Git: {commit_message}")


def push_data_to_gcs():
    """Step 4: Push actual data to GCS via DVC"""

    print(f"\n☁️  Pushing data to Google Cloud Storage")

    # This uploads the actual data file to GCS
    run_command(["dvc", "push"], "Push data to GCS")

    print(f"✓ Data pushed to GCS bucket")


def push_code_to_git():
    """Step 5: Push Git commits to remote"""

    print(f"\n🚀 Pushing to Git remote")

    run_command(["git", "push"], "Push commits to GitHub")

    print(f"✓ Code pushed to GitHub")


def main():
    """Main versioning workflow"""

    print("\n" + "=" * 60)
    print("NewsJuice Data Versioning")
    print("=" * 60)

    try:
        # Step 1: Export database
        export_file, timestamp = export_database()

        # Step 2: Track with DVC
        dvc_file = track_with_dvc(export_file)

        # Step 3: Commit to Git
        commit_to_git(dvc_file, timestamp)

        # Step 4: Push data to GCS
        push_data_to_gcs()

        # Step 5: Push code to Git
        push_code_to_git()

        print("\n" + "=" * 60)
        print("✓ Data versioning complete!")
        print(f"Version: {timestamp}")
        print(f"Export file: {export_file.name}")
        print(f"Data location: gs://newsjuice-data-versions/dvc-storage/")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during versioning: {e}")
        raise


if __name__ == "__main__":
    main()
