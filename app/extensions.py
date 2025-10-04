import os
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from pymongo import MongoClient
import redis
from rq import Queue

login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()

mongo_client = None
db = None
users_col = None
uploads_col = None
processed_col = None
history_col = None
payments_col = None
webhooks_col = None
usage_col = None
downloads_col = None
redis_conn = None
queue = None
premium_queue = None

def init_app(app):
    global mongo_client, db, users_col, uploads_col, processed_col, history_col, payments_col, webhooks_col, usage_col, downloads_col
    global redis_conn, queue, premium_queue

    login_manager.init_app(app)
    # Redirect unauthorized users to login page instead of 401
    try:
        login_manager.login_view = 'auth.login'
        login_manager.login_message_category = 'info'
    except Exception:
        pass
    csrf.init_app(app)
    
    if app.config.get('RATE_LIMIT_STORAGE_URL'):
        limiter.storage_uri = app.config['RATE_LIMIT_STORAGE_URL']
    
    limiter.init_app(app)
    talisman.init_app(app, content_security_policy=app.config.get('CONTENT_SECURITY_POLICY'), frame_options='DENY')

    # MongoDB (fast-fail)
    mongo_client = MongoClient(app.config['MONGO_URI'], serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
    db = mongo_client[app.config['MONGO_DB']]
    users_col = db['users']
    uploads_col = db['uploads']
    processed_col = db['processed']
    history_col = db['history']
    payments_col = db['payments']
    webhooks_col = db['webhooks']
    usage_col = db['usage_tracking']
    downloads_col = db['downloads']
    
    downloads_col.create_index([('user_id', 1), ('download_timestamp', -1)])
    downloads_col.create_index('download_timestamp')

    # Redis (fast-fail with optional dev fallback)
    allow_without_redis = os.getenv('ALLOW_START_WITHOUT_REDIS', '0') in ('1','true','True','yes')
    try:
        redis_conn = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB'],
            password=app.config['REDIS_PASSWORD'] or None,
            decode_responses=False
        )
        redis_conn.ping()
        queue = Queue(app.config['RQ_QUEUE_NAME'], connection=redis_conn, default_timeout=app.config['RQ_JOB_TIMEOUT'])
        premium_queue = Queue(app.config['RQ_QUEUE_NAME'] + '_premium', connection=redis_conn, default_timeout=app.config['RQ_JOB_TIMEOUT'])
    except Exception as e:
        if not allow_without_redis:
            raise RuntimeError(f"Redis connection failed: {e}")
        # Dev fallback: provide dummy queues so app can start without Redis
        import uuid
        class _DummyJob:
            def __init__(self):
                self._id = uuid.uuid4().hex
            def get_id(self):
                return self._id
        class _DummyQueue:
            def __init__(self, name):
                self.name = name
            @property
            def connection(self):
                return None
            def enqueue(self, *args, **kwargs):
                print(f"[extensions] WARNING: enqueue called on DummyQueue '{self.name}'. Task not executed.")
                return _DummyJob()
        redis_conn = None
        queue = _DummyQueue(app.config['RQ_QUEUE_NAME'])
        premium_queue = _DummyQueue(app.config['RQ_QUEUE_NAME'] + '_premium')

