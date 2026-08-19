from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import threading

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Thread-safe tenant engine and session factory cache
_tenant_engines = {}
_tenant_sessions = {}
_engine_lock = threading.Lock()
_session_lock = threading.Lock()

def get_tenant_db_url(subdomain, app=None, db_name=None):
    """Build a connection URL for a tenant database."""
    from flask import current_app
    import urllib
    _app = app or current_app
    server = _app.config['DB_SERVER']
    driver = _app.config['DB_DRIVER']
    user = _app.config.get('DB_USER')
    password = _app.config.get('DB_PASSWORD')
    
    # 1. Use provided db_name, otherwise resolve dynamically from TurMasterDB.Agencies
    if not db_name:
        db_name = subdomain.lower()
        # Ensure TCP/IP works even if DB_SERVER uses the local pipe alias '.'
        _tcp_server = server.replace('.\\', 'localhost\\') if server.startswith('.\\') else server
        
        try:
            import pyodbc
            if user and password:
                conn_str = f"Driver={{{driver}}};Server={_tcp_server};Database=TurMasterDB;UID={user};PWD={password};Encrypt=no;TrustServerCertificate=yes;"
            else:
                conn_str = f"Driver={{{driver}}};Server={_tcp_server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
                
            # print(f"[DEBUG] [get_tenant_db_url] Connecting to Master DB with: {conn_str}", flush=True)
            with pyodbc.connect(conn_str, timeout=10) as conn:
                # print("[DEBUG] [get_tenant_db_url] Connected successfully, executing query...", flush=True)
                with conn.cursor() as cursor:
                    cursor.execute("SELECT AgencyDBName FROM Agencies WITH (NOLOCK) WHERE Username = ?", (subdomain,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        db_name = row[0]
                        # print(f"[DEBUG] [get_tenant_db_url] Found physical DB name: {db_name}", flush=True)
        except Exception as e:
            # print(f"[DEBUG] [get_tenant_db_url] [ERROR] Failed to query master DB: {e}", flush=True)
            raise e
    _tcp_server = server.replace('.\\', 'localhost\\') if server.startswith('.\\') else server

    if user and password:
        params = urllib.parse.quote_plus(f"DRIVER={{{driver}}};SERVER={_tcp_server};DATABASE={db_name};UID={user};PWD={password};Encrypt=no;TrustServerCertificate=yes")
    else:
        params = urllib.parse.quote_plus(f"DRIVER={{{driver}}};SERVER={_tcp_server};DATABASE={db_name};Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes")
        
    return f"mssql+pyodbc:///?odbc_connect={params}"

def check_and_update_tenant_schema(engine):
    """Deprecated: Schema is now managed by the DB Migration system (migrate_tenants.py)."""
    pass
def get_tenant_engine(subdomain, app=None, db_name=None):
    """Get or create a cached engine for the given tenant subdomain with optimized connection pooling."""
    key = subdomain.upper()
    if key not in _tenant_engines:
        with _engine_lock:
            if key not in _tenant_engines:
                url = get_tenant_db_url(subdomain, app, db_name=db_name)
                from sqlalchemy.pool import QueuePool
                engine = create_engine(
                    url, 
                    poolclass=QueuePool,
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=1800,
                    pool_pre_ping=True
                )
                check_and_update_tenant_schema(engine)
                _tenant_engines[key] = engine
    return _tenant_engines[key]

def ensure_tenant_tables(subdomain, app=None):
    """Auto-scan tenant database and create any missing tables (rentals, vehicles, etc.) safely without touching existing data."""
    try:
        from models import TenantBase
        tenant_engine = get_tenant_engine(subdomain, app)
        TenantBase.metadata.create_all(tenant_engine)
    except Exception as e:
        print(f"[TENANT AUTO-MIGRATE ERROR] Failed to create missing tables for {subdomain}: {e}", flush=True)

def get_tenant_session(subdomain=None, app=None, db_name=None):
    """Get or create a cached scoped session for a tenant database to reduce instantiation overhead."""
    from flask import g
    if subdomain is None:
        subdomain = g.current_company.subdomain
    if db_name is None and hasattr(g, 'current_company') and g.current_company:
        db_name = getattr(g.current_company, 'db_name', None)
        
    key = subdomain.upper()
    if key not in _tenant_sessions:
        with _session_lock:
            if key not in _tenant_sessions:
                # Eksik tablo kontrolü ve otomatik tablo tamamlama
                ensure_tenant_tables(subdomain, app)
                
                engine = get_tenant_engine(subdomain, app, db_name=db_name)
                session_factory = sessionmaker(bind=engine)
                # OPTIMIZATION: Cache scoped_session instance globally per tenant instead of recreations on each request
                _tenant_sessions[key] = scoped_session(session_factory)
                
    return _tenant_sessions[key]()

def close_all_tenant_sessions():
    """Remove and clean up all scoped sessions for the current thread context to prevent database connection leaks."""
    with _session_lock:
        for session_obj in _tenant_sessions.values():
            try:
                session_obj.remove()
            except:
                pass

def create_tenant_database(subdomain, app=None):
    """Create a new tenant database and all tenant tables."""
    from flask import current_app
    from models import TenantBase
    _app = app or current_app
    
    server = _app.config['DB_SERVER']
    driver = _app.config['DB_DRIVER']
    db_name = subdomain.lower()
    
    # Connect to master to issue CREATE DATABASE
    master_url = _app.config['SQLALCHEMY_DATABASE_URI']
    master_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
    
    with master_engine.connect() as conn:
        # Check if DB already exists
        result = conn.execute(
            __import__('sqlalchemy').text(f"SELECT DB_ID('{db_name}')")
        )
        exists = result.scalar() is not None
        
        if not exists:
            conn.execute(__import__('sqlalchemy').text(f"CREATE DATABASE [{db_name}]"))
            print(f"[TENANT] Veritabani olusturuldu: {db_name}")
    
    master_engine.dispose()
    
    # Create all tenant tables in the new DB
    tenant_engine = get_tenant_engine(subdomain, _app)
    TenantBase.metadata.create_all(tenant_engine)
    print(f"[TENANT] Tablolar olusturuldu: {db_name}")
    
    return db_name

def init_extensions(app):
    from sqlalchemy.pool import QueuePool
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True
    }
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Lütfen önce giriş yapın.'
    login_manager.login_message_category = 'info'
    
    # BEYOND ENTERPRISE: SQLAlchemy Event Listeners for Automatic Smart Cache Invalidation
    try:
        from sqlalchemy import event
        from models import Rental, Vehicle, Service, VehicleExpense
        from utils.stats import invalidate_stats_cache
        
        def on_change(mapper, connection, target):
            invalidate_stats_cache()
            
        for model in [Rental, Vehicle, Service, VehicleExpense]:
            event.listen(model, 'after_insert', on_change)
            event.listen(model, 'after_update', on_change)
            event.listen(model, 'after_delete', on_change)
            
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
            
        print("[STATS CACHE] SQLAlchemy mutation cache invalidation listeners registered successfully.")
    except Exception as e:
        print(f"[STATS CACHE] Failed to register listeners: {e}")
