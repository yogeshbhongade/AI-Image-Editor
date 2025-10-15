"""
Subscription API routes
Handles payment and subscription management with Razorpay
"""

import razorpay
import hmac
import hashlib
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.core.config import get_config
from app.core.database import get_db
from app.models.subscription import SubscriptionService
from app.models.user import UserService

subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscription')

# Initialize Razorpay client
def get_razorpay_client():
    """Get Razorpay client instance"""
    config = get_config()
    if config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET:
        return razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
    return None


@subscription_bp.route('/create-order', methods=['POST'])
@login_required
def create_subscription_order():
    """Create a Razorpay order for subscription"""
    razorpay_client = get_razorpay_client()
    if not razorpay_client:
        return jsonify({
            'success': False,
            'error': 'Payment system not configured'
        }), 500

    try:
        config = get_config()
        db = get_db()
        
        plan_type = request.json.get('plan_type', 'monthly')
        amount = config.PREMIUM_PLAN_AMOUNT

        order_data = {
            'amount': amount,
            'currency': config.RAZORPAY_CURRENCY,
            'receipt': f'order_{current_user.id}_{int(datetime.utcnow().timestamp())}',
            'notes': {
                'user_id': str(current_user.id),
                'plan_type': plan_type
            }
        }

        order = razorpay_client.order.create(data=order_data)

        # Store payment record
        db.payments.insert_one({
            'user_id': str(current_user.id),
            'razorpay_order_id': order['id'],
            'amount': amount,
            'currency': config.RAZORPAY_CURRENCY,
            'status': 'created',
            'plan_type': plan_type,
            'created_at': datetime.utcnow()
        })

        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': amount,
            'currency': config.RAZORPAY_CURRENCY,
            'key_id': config.RAZORPAY_KEY_ID
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@subscription_bp.route('/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    """Verify Razorpay payment signature"""
    try:
        config = get_config()
        db = get_db()
        
        data = request.json
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return jsonify({
                'success': False,
                'error': 'Missing payment information'
            }), 400

        # Verify signature
        message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
        secret = config.RAZORPAY_KEY_SECRET.encode()
        expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

        if expected_signature != razorpay_signature:
            return jsonify({
                'success': False,
                'error': 'Invalid payment signature'
            }), 400

        # Update payment record
        db.payments.update_one(
            {'razorpay_order_id': razorpay_order_id},
            {
                '$set': {
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature,
                    'status': 'completed',
                    'completed_at': datetime.utcnow()
                }
            }
        )

        # Activate premium subscription
        subscription_service = SubscriptionService()
        subscription_service.activate_premium(
            current_user.id,
            duration_days=30,  # Default to 30 days
            payment_id=razorpay_payment_id
        )

        return jsonify({
            'success': True,
            'message': 'Payment verified and subscription activated'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@subscription_bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user subscription"""
    try:
        subscription_service = SubscriptionService()
        result = subscription_service.cancel_subscription(current_user.id)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Subscription cancelled successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel subscription'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@subscription_bp.route('/reactivate', methods=['POST'])
@login_required
def reactivate_subscription():
    """Reactivate a cancelled subscription"""
    try:
        subscription_service = SubscriptionService()
        result = subscription_service.reactivate_subscription(current_user.id)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Subscription reactivated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to reactivate subscription'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Note: payment.js expects /create-subscription at root level
# This will be handled by registering an additional route in core.py
