"""
Script to export data from Neon PostgreSQL and import to Google Cloud SQL
"""
import os
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Source database (Neon PostgreSQL)
NEON_DB_URL = "postgresql://neondb_owner:npg_Hclv1yP9IEeL@ep-lively-smoke-a5b0oxbb.us-east-2.aws.neon.tech/neondb"

# Target database (Google Cloud SQL)
# Replace these with your actual Google Cloud SQL details
GOOGLE_DB_HOST = "34.60.72.203"  # Change to your actual IP
GOOGLE_DB_NAME = "budget_ai"
GOOGLE_DB_USER = "postgres"
GOOGLE_DB_PASSWORD = "your_password_here"  # Replace with your actual password

def get_source_connection():
    """Connect to the source database (Neon PostgreSQL)"""
    conn = psycopg2.connect(NEON_DB_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def get_target_connection():
    """Connect to the target database (Google Cloud SQL)"""
    conn = psycopg2.connect(
        host=GOOGLE_DB_HOST,
        database=GOOGLE_DB_NAME,
        user=GOOGLE_DB_USER,
        password=GOOGLE_DB_PASSWORD
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def get_table_names(conn):
    """Get all table names from the source database"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
    """)
    tables = [table[0] for table in cursor.fetchall()]
    cursor.close()
    return tables

def get_create_table_statement(source_conn, table_name):
    """Get the CREATE TABLE statement for a table"""
    cursor = source_conn.cursor()
    cursor.execute(f"""
        SELECT 
            'CREATE TABLE ' || table_name || ' (' ||
            string_agg(
                column_name || ' ' || data_type || 
                CASE 
                    WHEN character_maximum_length IS NOT NULL 
                    THEN '(' || character_maximum_length || ')'
                    ELSE ''
                END ||
                CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                ', '
            ) || ');'
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
        GROUP BY table_name;
    """, (table_name,))
    
    create_statement = cursor.fetchone()[0]
    cursor.close()
    return create_statement

def get_primary_key_statement(source_conn, table_name):
    """Get the ALTER TABLE statement to add primary key"""
    cursor = source_conn.cursor()
    cursor.execute("""
        SELECT 
            'ALTER TABLE ' || tc.table_name || 
            ' ADD CONSTRAINT ' || tc.constraint_name || 
            ' PRIMARY KEY (' || 
            string_agg(kcu.column_name, ', ') || 
            ');'
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_schema = 'public'
        AND tc.table_name = %s
        GROUP BY tc.table_name, tc.constraint_name;
    """, (table_name,))
    
    result = cursor.fetchone()
    pk_statement = result[0] if result else None
    cursor.close()
    return pk_statement

def get_table_data(source_conn, table_name):
    """Get all data from a table"""
    cursor = source_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    
    # Get column names
    column_names = [desc[0] for desc in cursor.description]
    
    cursor.close()
    return column_names, data

def create_tables(target_conn, tables, source_conn):
    """Create all tables in the target database"""
    cursor = target_conn.cursor()
    
    for table_name in tables:
        print(f"Creating table {table_name}...")
        
        # Create the table
        create_statement = get_create_table_statement(source_conn, table_name)
        cursor.execute(create_statement)
        
        # Add primary key if exists
        pk_statement = get_primary_key_statement(source_conn, table_name)
        if pk_statement:
            cursor.execute(pk_statement)
    
    cursor.close()

def import_data(target_conn, tables, source_conn):
    """Import data into the target database"""
    for table_name in tables:
        print(f"Importing data for table {table_name}...")
        column_names, data = get_table_data(source_conn, table_name)
        
        if not data:
            print(f"  No data to import for {table_name}")
            continue
        
        cursor = target_conn.cursor()
        
        # Generate placeholders for each row
        placeholders = ', '.join(['%s'] * len(column_names))
        columns = ', '.join(column_names)
        
        # Insert data in batches
        batch_size = 100
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            try:
                args_str = ','.join(cursor.mogrify(f"({placeholders})", row).decode('utf-8') for row in batch)
                cursor.execute(f"INSERT INTO {table_name} ({columns}) VALUES {args_str}")
                print(f"  Imported {len(batch)} rows to {table_name}")
            except Exception as e:
                print(f"  Error importing data to {table_name}: {e}")
        
        cursor.close()

def main():
    """Main function to export and import data"""
    try:
        print("Connecting to source database...")
        source_conn = get_source_connection()
        
        print("Getting table names...")
        tables = get_table_names(source_conn)
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        print("\nConnecting to target database...")
        target_conn = get_target_connection()
        
        print("\nCreating tables in target database...")
        create_tables(target_conn, tables, source_conn)
        
        print("\nImporting data to target database...")
        import_data(target_conn, tables, source_conn)
        
        print("\nDatabase migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        if 'source_conn' in locals():
            source_conn.close()
        if 'target_conn' in locals():
            target_conn.close()

if __name__ == "__main__":
    main()