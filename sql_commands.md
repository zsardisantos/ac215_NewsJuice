# SQL Commands for Database Exploration

Use these SQL commands to explore your NewsJuice PostgreSQL database. Connect using:

```bash
# Start Cloud SQL proxy first
cloud-sql-proxy --credentials-file=./secrets/sa-key.json --port 5432 newsjuice-123456:us-central1:newsdb-instance

# Connect with psql
psql "postgresql://postgres:Newsjuice25%2B@localhost:5432/newsdb"
```

## 1. List All Tables

```sql
-- List all tables in the public schema
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- Alternative using PostgreSQL system catalogs
\dt
```

## 2. Show Table Structure

```sql
-- Show detailed column information for a specific table
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'your_table_name' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- Alternative using PostgreSQL describe
\d your_table_name
```

## 3. View Table Data

```sql
-- Show all data from a table (be careful with large tables!)
SELECT * FROM your_table_name;

-- Show first 10 rows
SELECT * FROM your_table_name LIMIT 10;

-- Show row count
SELECT COUNT(*) FROM your_table_name;
```

## 4. Database Statistics

```sql
-- Show table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Show total database size
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Show database name and current user
SELECT current_database(), current_user;
```

## 5. Index Information

```sql
-- Show indexes for a specific table
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'your_table_name'
AND schemaname = 'public';
```

## 6. Foreign Key Relationships

```sql
-- Show foreign key relationships
SELECT 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.key_column_usage AS kcu
JOIN information_schema.referential_constraints AS rcs
    ON kcu.constraint_name = rcs.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = rcs.constraint_name
WHERE kcu.table_name = 'your_table_name'
AND kcu.table_schema = 'public';
```

## 7. Search for Specific Data

```sql
-- Search for tables containing specific text
SELECT table_name, column_name
FROM information_schema.columns
WHERE column_name ILIKE '%search_term%'
AND table_schema = 'public';

-- Search for data in JSONB columns (if you have any)
SELECT * FROM your_table_name 
WHERE jsonb_column @> '{"key": "value"}';
```

## 8. Quick Database Overview

```sql
-- Get a quick overview of all tables with row counts
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
```

## 9. Useful PostgreSQL Meta-Commands

When using `psql`, these commands are very helpful:

```sql
-- List all tables
\dt

-- Describe a table structure
\d table_name

-- List all databases
\l

-- List all schemas
\dn

-- Show current database and user
\conninfo

-- Show all tables with sizes
\dt+

-- Quit psql
\q
```

## 10. Based on Your README

Based on your conversation database README, you should have these tables:

```sql
-- Check for LLM conversation tables
SELECT * FROM llm_conversations LIMIT 5;
SELECT * FROM llm_messages LIMIT 5;

-- Check table schemas
\d llm_conversations
\d llm_messages
```

## Troubleshooting

If you get connection errors:

1. **Make sure Cloud SQL proxy is running:**
   ```bash
   ps aux | grep cloud-sql-proxy
   ```

2. **Check if port 5432 is listening:**
   ```bash
   netstat -tlnp | grep 5432
   ```

3. **Test connection:**
   ```bash
   telnet localhost 5432
   ```

4. **Check credentials file exists:**
   ```bash
   ls -la ./secrets/sa-key.json
   ```