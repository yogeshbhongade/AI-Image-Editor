"""
Subscription model and service layer
Handles subscription management and usage tracking
"""

from datetime import datetime, timedelta
from bson import ObjectId
from typing import Optional, Dict, Any
from enum import Enum

class SubscriptionTier(Enum):
    """Subscription tier enumeration"""
    FREE = "free"
    PREMIUM = "premium"


class UsageType(Enum):
    """Usage type enumeration"""
    EDIT = "edit"
    AI_EDIT = "ai"
    DOWNLOAD = "download"
    GENERATION = "generation"


class SubscriptionModel:
    """Subscription model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = str(data.get('_id'))
        self.user_id = data.get('user_id')
        self.tier = data.get('tier', SubscriptionTier.FREE.value)
        self.status = data.get('status', 'active')
        self.started_at = data.get('started_at')
        self.expires_at = data.get('expires_at')
        self.payment_id = data.get('payment_id')
        self.amount = data.get('amount', 0)
        self.currency = data.get('currency', 'INR')
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is active"""
        if self.status != 'active':
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    @property
    def is_premium(self) -> bool:
        """Check if subscription is premium"""
        return self.tier == SubscriptionTier.PREMIUM.value and self.is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'tier': self.tier,
            'status': self.status,
            'started_at': self.started_at,
            'expires_at': self.expires_at,
            'is_active': self.is_active,
            'is_premium': self.is_premium,
            'payment_id': self.payment_id,
            'amount': self.amount,
            'currency': self.currency
        }


class UsageModel:
    """Usage tracking model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = str(data.get('_id'))
        self.user_id = data.get('user_id')
        self.usage_type = data.get('usage_type')
        self.count = data.get('count', 0)
        self.date = data.get('date')
        self.reset_at = data.get('reset_at')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'usage_type': self.usage_type,
            'count': self.count,
            'date': self.date,
            'reset_at': self.reset_at
        }


class SubscriptionService:
    """Service layer for subscription operations"""
    
    # Usage limits for different tiers
    USAGE_LIMITS = {
        SubscriptionTier.FREE.value: {
            UsageType.EDIT.value: 50,
            UsageType.AI_EDIT.value: 5,
            UsageType.DOWNLOAD.value: 20,
            UsageType.GENERATION.value: 3
        },
        SubscriptionTier.PREMIUM.value: {
            UsageType.EDIT.value: 999999999,  # Unlimited
            UsageType.AI_EDIT.value: 999999999,
            UsageType.DOWNLOAD.value: 999999999,
            UsageType.GENERATION.value: 999999999
        }
    }
    
    def __init__(self):
        self._db = None
        self._subscriptions_collection = None
        self._usage_collection = None
        self._payments_collection = None
    
    @property
    def db(self):
        if self._db is None:
            from app.core.database import get_db
            self._db = get_db()
        return self._db
    
    @property
    def subscriptions_collection(self):
        if self._subscriptions_collection is None:
            self._subscriptions_collection = self.db.subscriptions
        return self._subscriptions_collection
    
    @property
    def usage_collection(self):
        if self._usage_collection is None:
            self._usage_collection = self.db.usage_tracking
        return self._usage_collection
    
    @property
    def payments_collection(self):
        if self._payments_collection is None:
            self._payments_collection = self.db.payments
        return self._payments_collection
    
    def get_user_subscription(self, user_id: str) -> SubscriptionModel:
        """Get user's current subscription"""
        subscription = self.subscriptions_collection.find_one({
            'user_id': user_id,
            'status': 'active'
        })
        
        if not subscription:
            # Create default free subscription
            subscription = {
                'user_id': user_id,
                'tier': SubscriptionTier.FREE.value,
                'status': 'active',
                'started_at': datetime.utcnow(),
                'expires_at': None
            }
            result = self.subscriptions_collection.insert_one(subscription)
            subscription['_id'] = result.inserted_id
        
        return SubscriptionModel(subscription)
    
    def upgrade_subscription(self, user_id: str, payment_id: str, 
                           amount: int, duration_months: int = 1) -> SubscriptionModel:
        """Upgrade user to premium subscription"""
        # Deactivate current subscription
        self.subscriptions_collection.update_many(
            {'user_id': user_id, 'status': 'active'},
            {'$set': {'status': 'inactive'}}
        )
        
        # Create new premium subscription
        expires_at = datetime.utcnow() + timedelta(days=30 * duration_months)
        
        subscription_data = {
            'user_id': user_id,
            'tier': SubscriptionTier.PREMIUM.value,
            'status': 'active',
            'started_at': datetime.utcnow(),
            'expires_at': expires_at,
            'payment_id': payment_id,
            'amount': amount,
            'currency': 'INR'
        }
        
        result = self.subscriptions_collection.insert_one(subscription_data)
        subscription_data['_id'] = result.inserted_id
        
        return SubscriptionModel(subscription_data)
    
    def get_usage_limits(self, user_id: str) -> Dict[str, int]:
        """Get usage limits for user based on subscription"""
        subscription = self.get_user_subscription(user_id)
        return self.USAGE_LIMITS.get(subscription.tier, self.USAGE_LIMITS[SubscriptionTier.FREE.value])
    
    def get_current_usage(self, user_id: str) -> Dict[str, int]:
        """Get current usage for user"""
        # Use start of today to match exactly with increment_usage method
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        usage_data = {}
        for usage_type in UsageType:
            usage = self.usage_collection.find_one({
                'user_id': user_id,
                'usage_type': usage_type.value,
                'date': today_start  # Match exactly with stored date
            })
            usage_data[usage_type.value] = usage.get('count', 0) if usage else 0
        
        return usage_data
    
    def increment_usage(self, user_id: str, usage_type: str) -> bool:
        """Increment usage counter for user"""
        # Use datetime objects instead of date objects
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)
        
        try:
            # Upsert usage record
            self.usage_collection.update_one(
                {
                    'user_id': user_id,
                    'usage_type': usage_type,
                    'date': today_start
                },
                {
                    '$inc': {'count': 1},
                    '$setOnInsert': {
                        'user_id': user_id,
                        'usage_type': usage_type,
                        'date': today_start,
                        'reset_at': tomorrow_start,
                        'created_at': now
                    }
                },
                upsert=True
            )
            return True
        except Exception:
            return False
    
    def can_perform_action(self, user_id: str, usage_type: str) -> bool:
        """Check if user can perform action based on usage limits"""
        try:
            limits = self.get_usage_limits(user_id)
            current_usage = self.get_current_usage(user_id)
            
            limit = limits.get(usage_type, 0)
            used = current_usage.get(usage_type, 0)
            
            return used < limit
        except Exception as e:
            # Default to allowing action on error to avoid blocking users
            return True
    
    def get_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive usage statistics"""
        limits = self.get_usage_limits(user_id)
        current_usage = self.get_current_usage(user_id)
        subscription = self.get_user_subscription(user_id)
        
        stats = {
            'subscription': subscription.to_dict(),
            'limits': limits,
            'current_usage': current_usage,
            'remaining': {}
        }
        
        # Calculate remaining usage
        for usage_type, limit in limits.items():
            used = current_usage.get(usage_type, 0)
            stats['remaining'][usage_type] = max(0, limit - used)
        
        return stats
    
    def cleanup_old_usage(self) -> int:
        """Clean up old usage records"""
        try:
            # Delete usage records older than 7 days
            cutoff_datetime = datetime.utcnow() - timedelta(days=7)
            
            result = self.usage_collection.delete_many({
                'date': {'$lt': cutoff_datetime}
            })
            
            return result.deleted_count
        except Exception:
            return 0
    
    def is_premium_feature(self, feature: str) -> bool:
        """Check if feature requires premium subscription"""
        premium_features = {
            'emboss', 'edges', 'enhance', 'ai_edit', 'ai_generate',
            'batch_process', 'bulk_download', 'permanent_storage'
        }
        return feature in premium_features
