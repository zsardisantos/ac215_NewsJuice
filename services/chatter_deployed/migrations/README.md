# Database Migrations

## Running Migrations

### Option 1: Using psql Command Line

```bash
psql $DATABASE_URL -f migrations/001_add_source_chunks_column.sql
```

### Option 2: Using Cloud SQL Proxy

```bash
# Connect to Cloud SQL
cloud_sql_proxy -instances=PROJECT_ID:REGION:INSTANCE_NAME=tcp:5432

# In another terminal
psql "host=127.0.0.1 port=5432 dbname=DATABASE_NAME user=USERNAME" -f migrations/001_add_source_chunks_column.sql
```

### Option 3: Using GCP Console

1. Go to Cloud SQL instance in GCP Console
2. Click "Import" or use the SQL editor
3. Copy and paste the contents of `001_add_source_chunks_column.sql`
4. Execute

## Verification

After running the migration, verify the column was added:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'audio_history'
AND column_name = 'source_chunks';
```

Expected output:
```
column_name    | data_type | is_nullable
---------------+-----------+-------------
source_chunks  | jsonb     | YES
```

## Rollback (if needed)

```sql
ALTER TABLE audio_history DROP COLUMN IF EXISTS source_chunks;
```
