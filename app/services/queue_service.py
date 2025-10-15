"""Queue service for managing background jobs.

Provides queue abstraction that gracefully degrades when Redis/RQ are not
available (common during local development). When Redis is unavailable, jobs
are executed synchronously and tracked in an in-memory store so the rest of the
application can continue to poll for job status without code changes.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid
from threading import Lock

from app.core.database import get_queue, get_premium_queue, get_redis
from app.core.exceptions import QueueError, ValidationError
from app.core.config import get_config


# In-memory storage for jobs when Redis is unavailable (development fallback)
_dummy_job_store: Dict[str, Dict[str, Any]] = {}
_dummy_jobs_lock = Lock()


class QueueService:
    """Service for managing background job queues"""
    
    def __init__(self):
        self.config = get_config()
        self._default_queue = None
        self._premium_queue = None
        self._redis_conn = None
    
    @property
    def default_queue(self):
        if self._default_queue is None:
            self._default_queue = get_queue()
        return self._default_queue
    
    @property
    def premium_queue(self):
        if self._premium_queue is None:
            self._premium_queue = get_premium_queue()
        return self._premium_queue
    
    @property
    def redis_conn(self):
        if self._redis_conn is None:
            self._redis_conn = get_redis()
        return self._redis_conn
    
    def enqueue_image_processing(self, user_id: str, operation: str, filename: str,
                                parameters: Dict[str, Any], is_premium: bool = False) -> str:
        """Enqueue image processing job"""
        try:
            # Import here to avoid circular imports
            from app.tasks.image_tasks import process_image_task
            
            # Check if Redis is available
            if self.redis_conn is None:
                # No Redis - process synchronously and store in dummy store
                job_id = uuid.uuid4().hex
                
                # Store job metadata in dummy store
                with _dummy_jobs_lock:
                    _dummy_job_store[job_id] = {
                        'job_id': job_id,
                        'status': 'started',
                        'user_id': user_id,
                        'operation': operation,
                        'filename': filename,
                        'created_at': datetime.utcnow().isoformat(),
                        'started_at': datetime.utcnow().isoformat(),
                        'metadata': {
                            'user_id': user_id,
                            'operation': operation,
                            'filename': filename,
                            'created_at': datetime.utcnow().isoformat(),
                            'queue': 'premium' if is_premium else 'default'
                        }
                    }
                
                try:
                    # Process synchronously
                    result = process_image_task(
                        user_id=user_id,
                        operation=operation,
                        filename=filename,
                        **parameters
                    )
                    
                    # Update dummy store with success
                    with _dummy_jobs_lock:
                        _dummy_job_store[job_id].update({
                            'status': 'finished',
                            'ended_at': datetime.utcnow().isoformat(),
                            'result': result
                        })
                        
                except Exception as task_error:
                    # Update dummy store with error
                    with _dummy_jobs_lock:
                        _dummy_job_store[job_id].update({
                            'status': 'failed',
                            'ended_at': datetime.utcnow().isoformat(),
                            'error': str(task_error)
                        })
                    
                return job_id
            
            # Redis available - use normal queue
            queue = self.premium_queue if is_premium else self.default_queue
            
            # Prepare job parameters
            job_params = {
                'user_id': user_id,
                'operation': operation,
                'filename': filename,
                **parameters
            }
            
            # Enqueue job
            job = queue.enqueue(
                process_image_task,
                **job_params,
                timeout=self.config.RQ_JOB_TIMEOUT
            )
            
            # Store job metadata
            self._store_job_metadata(job.get_id(), {
                'user_id': user_id,
                'operation': operation,
                'filename': filename,
                'created_at': datetime.utcnow().isoformat(),
                'queue': 'premium' if is_premium else 'default'
            })
            
            return job.get_id()
            
        except Exception as e:
            raise QueueError(f"Failed to enqueue image processing job: {str(e)}")
    
    def enqueue_ai_task(self, user_id: str, task_type: str, parameters: Dict[str, Any],
                       is_premium: bool = True) -> str:
        """Enqueue AI processing job"""
        try:
            # Import here to avoid circular imports
            if task_type == 'generate':
                from app.tasks.ai_tasks import process_ai_generate_task
                task_func = process_ai_generate_task
            elif task_type == 'edit':
                from app.tasks.ai_tasks import process_ai_edit_task
                task_func = process_ai_edit_task
            else:
                raise ValidationError(f"Unknown AI task type: {task_type}")
            
            # AI tasks typically use premium queue
            queue = self.premium_queue if is_premium else self.default_queue
            
            # Prepare job parameters
            job_params = {
                'user_id': user_id,
                **parameters
            }
            
            # Enqueue job with longer timeout for AI tasks
            job = queue.enqueue(
                task_func,
                **job_params,
                timeout=self.config.RQ_JOB_TIMEOUT * 2  # AI tasks take longer
            )
            
            # Store job metadata
            self._store_job_metadata(job.get_id(), {
                'user_id': user_id,
                'task_type': task_type,
                'created_at': datetime.utcnow().isoformat(),
                'queue': 'premium' if is_premium else 'default'
            })
            
            return job.get_id()
            
        except Exception as e:
            raise QueueError(f"Failed to enqueue AI task: {str(e)}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a background job"""
        try:
            # Check if Redis is available
            if self.redis_conn is None:
                # Check dummy store first
                with _dummy_jobs_lock:
                    if job_id in _dummy_job_store:
                        job_data = _dummy_job_store[job_id].copy()
                        return job_data
                
                # Fallback for jobs not in dummy store
                return self._simulate_job_processing(job_id)
            
            from rq import Job
            
            # Get job from queue
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            # Get job metadata
            metadata = self._get_job_metadata(job_id)
            
            # Determine status
            if job.is_finished:
                status = 'finished'
                result = job.result
            elif job.is_failed:
                status = 'failed'
                result = {
                    'error': str(job.exc_info) if job.exc_info else 'Job failed',
                    'traceback': job.exc_info
                }
            elif job.is_started:
                status = 'started'
                result = None
                # Get progress from job meta if available
                progress = job.meta.get('progress', 0) if job.meta else 0
            elif job.is_queued:
                status = 'queued'
                result = None
                progress = 0
            elif job.is_deferred:
                status = 'deferred'
                result = None
                progress = 0
            else:
                status = 'unknown'
                result = None
                progress = 0
            
            response = {
                'job_id': job_id,
                'status': status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                'metadata': metadata
            }
            
            if status == 'finished':
                response['result'] = result
            elif status == 'failed':
                response['error'] = result.get('error') if isinstance(result, dict) else str(result)
            elif status == 'started':
                response['progress'] = progress
            return response
            
        except Exception as e:
            # If Redis is not available, simulate processing
            if "Connection refused" in str(e) or "Redis" in str(e):
                return self._simulate_job_processing(job_id)
            raise QueueError(f"Failed to get job status: {str(e)}")
        
    def _simulate_job_processing(self, job_id: str) -> Dict[str, Any]:
        """Simulate job processing when Redis is not available"""
        try:
            # Get job metadata to understand what operation was requested
            metadata = self._get_job_metadata(job_id)
            
            if not metadata:
                # If no metadata, create a failed job response
                return {
                    'job_id': job_id,
                    'status': 'failed',
                    'error': 'Job metadata not found',
                    'metadata': {}
                }
            
            # Simulate immediate processing for development
            # In a real scenario, you'd want to process synchronously here
            operation = metadata.get('operation', 'unknown')
            filename = metadata.get('filename', 'unknown')
            user_id = metadata.get('user_id')
            
            # Process the image synchronously
            try:
                from app.tasks.image_tasks import process_image_task
                
                # Execute the task directly (synchronously)
                result = process_image_task(
                    user_id=user_id,
                    operation=operation,
                    filename=filename,
                    **{k: v for k, v in metadata.items() if k not in ['user_id', 'operation', 'filename', 'created_at', 'queue']}
                )
                
                return {
                    'job_id': job_id,
                    'status': 'finished',
                    'result': result,
                    'created_at': metadata.get('created_at'),
                    'started_at': datetime.utcnow().isoformat(),
                    'ended_at': datetime.utcnow().isoformat(),
                    'metadata': metadata
                }
                
            except Exception as task_error:
                return {
                    'job_id': job_id,
                    'status': 'failed',
                    'error': f'Processing failed: {str(task_error)}',
                    'created_at': metadata.get('created_at'),
                    'metadata': metadata
                }
                
        except Exception as e:
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': f'Simulation failed: {str(e)}',
                'metadata': {}
            }
    
    def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a background job"""
        try:
            from rq import Job
            metadata = self._get_job_metadata(job_id)
            if not metadata or metadata.get('user_id') != user_id:
                raise ValidationError("Job not found or access denied")
            
            # Get and cancel job
            job = Job.fetch(job_id, connection=self.redis_conn)
            
            if job.is_started or job.is_queued:
                job.cancel()
                return True
            
            return False
            
        except Exception as e:
            raise QueueError(f"Failed to cancel job: {str(e)}")
    
    def get_user_jobs(self, user_id: str, limit: int = 50) -> list:
        """Get user's recent jobs"""
        try:
            # Get job metadata for user
            pattern = f"job_meta:*"
            keys = self.redis_conn.keys(pattern) if self.redis_conn else []
            
            user_jobs = []
            for key in keys:
                try:
                    metadata_str = self.redis_conn.get(key)
                    if metadata_str:
                        # Fixed: Decode bytes before JSON parsing
                        metadata = json.loads(metadata_str.decode('utf-8'))
                        if metadata.get('user_id') == user_id:
                            job_id = key.decode('utf-8').split(':')[1]
                            job_status = self.get_job_status(job_id)
                            user_jobs.append(job_status)
                except Exception:
                    continue
            
            # Sort by creation time and limit
            user_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return user_jobs[:limit]
            
        except Exception as e:
            raise QueueError(f"Failed to get user jobs: {str(e)}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            stats = {
                'default_queue': {
                    'name': self.default_queue.name if hasattr(self.default_queue, 'name') else 'default',
                    'length': len(self.default_queue) if hasattr(self.default_queue, '__len__') else 0,
                },
                'premium_queue': {
                    'name': self.premium_queue.name if hasattr(self.premium_queue, 'name') else 'premium',
                    'length': len(self.premium_queue) if hasattr(self.premium_queue, '__len__') else 0,
                }
            }
            
            # Add worker information if available
            if self.redis_conn:
                from rq import Worker
                workers = Worker.all(connection=self.redis_conn)
                stats['workers'] = {
                    'total': len(workers),
                    'active': len([w for w in workers if w.get_state() == 'busy']),
                    'idle': len([w for w in workers if w.get_state() == 'idle'])
                }
            
            return stats
            
        except Exception as e:
            return {'error': f"Failed to get queue stats: {str(e)}"}
    
    def _store_job_metadata(self, job_id: str, metadata: Dict[str, Any]) -> None:
        """Store job metadata in Redis or dummy store"""
        try:
            if self.redis_conn:
                key = f"job_meta:{job_id}"
                # Fixed: Use correct setex syntax (name, time, value)
                self.redis_conn.setex(
                    key,
                    86400,  # 24 hours in seconds
                    json.dumps(metadata)
                )
            else:
                # Store in dummy store if Redis not available
                with _dummy_jobs_lock:
                    if job_id not in _dummy_job_store:
                        _dummy_job_store[job_id] = {}
                    _dummy_job_store[job_id]['metadata'] = metadata
        except Exception:
            pass  # Non-critical operation
    
    def _get_job_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job metadata from Redis or dummy store"""
        try:
            if self.redis_conn:
                key = f"job_meta:{job_id}"
                metadata_str = self.redis_conn.get(key)
                if metadata_str:
                    # Fixed: Decode bytes before JSON parsing
                    return json.loads(metadata_str.decode('utf-8'))
            else:
                # Check dummy store
                with _dummy_jobs_lock:
                    if job_id in _dummy_job_store:
                        return _dummy_job_store[job_id].get('metadata', {})
        except Exception:
            pass
        return None
    
    def cleanup_old_jobs(self, max_age_days: int = 7) -> int:
        """Clean up old job metadata"""
        try:
            if not self.redis_conn:
                return 0
            
            pattern = f"job_meta:*"
            keys = self.redis_conn.keys(pattern)
            
            cutoff_time = datetime.utcnow().timestamp() - (max_age_days * 86400)
            deleted_count = 0
            
            for key in keys:
                try:
                    metadata_str = self.redis_conn.get(key)
                    if metadata_str:
                        metadata = json.loads(metadata_str)
                        created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                        if created_at.timestamp() < cutoff_time:
                            self.redis_conn.delete(key)
                            deleted_count += 1
                except Exception:
                    continue
            
            return deleted_count
            
        except Exception:
            return 0
