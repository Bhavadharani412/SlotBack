import psycopg

def setup():
    conn = psycopg.connect('postgresql://postgres:postgres@localhost:5432/postgres', autocommit=True)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname='slotback'")
    if not cur.fetchone():
        cur.execute("CREATE USER slotback WITH PASSWORD 'slotback_dev_password' NOSUPERUSER CREATEDB")
        print("Created slotback user with NOSUPERUSER privileges")
    else:
        cur.execute("ALTER ROLE slotback NOSUPERUSER CREATEDB")
        print("Updated slotback user to NOSUPERUSER")
    
    cur.execute("SELECT 1 FROM pg_database WHERE datname='slotback'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE slotback OWNER slotback")
        print("Created slotback database")
    else:
        cur.execute("ALTER DATABASE slotback OWNER TO slotback")
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE slotback TO slotback")
        
    cur.execute("SELECT 1 FROM pg_database WHERE datname='slotback_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE slotback_test OWNER slotback")
        print("Created slotback_test database")
    else:
        cur.execute("ALTER DATABASE slotback_test OWNER TO slotback")
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE slotback_test TO slotback")
    conn.close()

    # Grant public schema permissions in both databases
    for db in ['slotback', 'slotback_test']:
        db_conn = psycopg.connect(f'postgresql://postgres:postgres@localhost:5432/{db}', autocommit=True)
        db_cur = db_conn.cursor()
        db_cur.execute("GRANT ALL ON SCHEMA public TO slotback")
        db_cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO slotback")
        db_cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO slotback")
        db_cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO slotback")
        db_conn.close()
        
    print("PostgreSQL least-privilege setup completed successfully!")

if __name__ == "__main__":
    setup()
