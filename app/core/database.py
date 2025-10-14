"""
Database configuration and connection management
Centralized database access for the application
"""

from pymongo import MongoClient
from pymongo.database import Database
import redis
from rq import Queue
import os
from typing import Optional

from .config import get_config


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self):
        self._mongo_client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._redis_conn: Optional[redis.Redis] = None
        self._queue: Optional[Queue] = None
        self._premium_queue: Optional[Queue] = None
        self._initialized = False
    
    def init_db(self, app=None):
        """Initialize database connections"""
        if self._initialized:
            return
        
        config = get_config()
        
        # MongoDB Connection
        try:
            self._mongo_client = MongoClient(
                config.MONGO_URI, 
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000
            )
            self._db = self._mongo_client[config.MONGO_DB]
            
            # Test connection
            self._mongo_client.admin.command('ping')
            print("✅ MongoDB connected successfully")
            
            # Create indexes
            self._create_indexes()
            
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            raise
        
        # Redis Connection
        try:
            allow_without_redis = os.getenv('ALLOW_START_WITHOUT_REDIS', '0') in ('1', 'true', 'True', 'yes')
            
            self._redis_conn = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD or None,
                decode_responses=False
            )
            
            # Test connection
            self._redis_conn.ping()
            
            # Initialize queues
            self._queue = Queue(
                config.RQ_QUEUE_NAME, 
                connection=self._redis_conn,
                default_timeout=config.RQ_JOB_TIMEOUT
            )
            self._premium_queue = Queue(
                config.RQ_QUEUE_NAME + '_premium',
                connection=self._redis_conn,
                default_timeout=config.RQ_JOB_TIMEOUT
            )
            
            print("✅ Redis connected successfully")
            
        except Exception as e:
            if not allow_without_redis:
                print(f"❌ Redis connection failed: {e}")
                raise
            else:
                print(f"⚠️ Redis not available, using dummy queues: {e}")
                self._setup_dummy_queues(config)
        
        self._initialized = True
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # User indexes
            self._db.users.create_index('email', unique=True)
            self._db.users.create_index('username', unique=True)
            
            # Upload indexes
            self._db.uploads.create_index([('uploaded_by', 1), ('uploaded_at', -1)])
            
            # Processed images indexes
            self._db.processed.create_index([('created_by', 1), ('created_at', -1)])
            self._db.processed.create_index([('session_id', 1), ('sequence', 1)])
            self._db.processed.create_index('expires_at')
            
            # Download indexes
            self._db.downloads.create_index([('user_id', 1), ('download_timestamp', -1)])
            self._db.downloads.create_index('download_timestamp')
            
            # Usage tracking indexes
            self._db.usage_tracking.create_index([('user_id', 1), ('date', 1), ('usage_type', 1)])
            
            # Subscription indexes
            self._db.subscriptions.create_index([('user_id', 1), ('status', 1)])
            
            print("✅ Database indexes created")
            
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    def _setup_dummy_queues(self, config):
        """Setup dummy queues for development without Redis"""
        import uuid
        
        class DummyJob:
            def __init__(self):
                self._id = uuid.uuid4().hex
            
            def get_id(self):
                return self._id
        
        class DummyQueue:
            def __init__(self, name):
                self.name = name
            
            @property
            def connection(self):
                return None
            
            def enqueue(self, *args, **kwargs):
                print(f"[DATABASE] WARNING: enqueue called on DummyQueue '{self.name}'. Task not executed.")
                return DummyJob()
        
        self._redis_conn = None
        self._queue = DummyQueue(config.RQ_QUEUE_NAME)
        self._premium_queue = DummyQueue(config.RQ_QUEUE_NAME + '_premium')
    
    @property
    def mongo_client(self) -> MongoClient:
        """Get MongoDB client"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._mongo_client
    
    @property
    def db(self) -> Database:
        """Get MongoDB database"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._db
    
    @property
    def redis_conn(self) -> redis.Redis:
        """Get Redis connection"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._redis_conn
    
    @property
    def queue(self) -> Queue:
        """Get default queue"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._queue
    
    @property
    def premium_queue(self) -> Queue:
        """Get premium queue"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._premium_queue


# Global database manager instance
_db_manager = DatabaseManager()


def init_db(app=None):
    """Initialize database connections"""
    _db_manager.init_db(app)


def get_db() -> Database:
    """Get MongoDB database instance"""
    return _db_manager.db


def get_mongo_client() -> MongoClient:
    """Get MongoDB client instance"""
    return _db_manager.mongo_client


def get_redis() -> redis.Redis:
    """Get Redis connection instance"""
    return _db_manager.redis_conn


def get_queue() -> Queue:
    """Get default RQ queue instance"""
    return _db_manager.queue


def get_premium_queue() -> Queue:
    """Get premium RQ queue instance"""
    return _db_manager.premium_queue
