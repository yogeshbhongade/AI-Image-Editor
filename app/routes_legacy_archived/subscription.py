"""
Subscription Management Routes
Handles premium subscription with Razorpay integration
"""

import razorpay
import hmac
import hashlib
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import extensions
from app.config import Config

bp = Blueprint('subscription', __name__)

razorpay_client = None
if Config.RAZORPAY_KEY_ID and Config.RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))


@bp.route('/subscription/manage')
@login_required
def manage_subscription():
    """View and manage user subscription."""
    user_data = extensions.db.users.find_one({'_id': current_user.id})

    subscription_info = {
        'status': user_data.get('subscription_status', 'free'),
        'subscription_id': user_data.get('subscription_id'),
        'started_at': user_data.get('subscription_started_at'),
        'ends_at': user_data.get('subscription_ends_at'),
        'auto_renew': user_data.get('auto_renew', False)
    }

    payment_history = list(extensions.db.payments.find(
        {'user_id': str(current_user.id)}
    ).sort('created_at', -1).limit(10))

    return render_template(
        'subscription_management.html',
        subscription=subscription_info,
        payments=payment_history
    )


@bp.route('/subscription/create-order', methods=['POST'])
@login_required
def create_subscription_order():
    """Create a Razorpay order for subscription."""
    if not razorpay_client:
        return jsonify({
            'success': False,
            'error': 'Payment system not configured'
        }), 500

    try:
        plan_type = request.json.get('plan_type', 'monthly')
        amount = Config.PREMIUM_PLAN_AMOUNT

        order_data = {
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'receipt': f'order_{current_user.id}_{int(datetime.utcnow().timestamp())}',
            'notes': {
                'user_id': str(current_user.id),
                'plan_type': plan_type
            }
        }

        order = razorpay_client.order.create(data=order_data)

        extensions.db.payments.insert_one({
            'user_id': str(current_user.id),
            'razorpay_order_id': order['id'],
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'status': 'created',
            'plan_type': plan_type,
            'created_at': datetime.utcnow()
        })

        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': amount,
            'currency': Config.RAZORPAY_CURRENCY,
            'key_id': Config.RAZORPAY_KEY_ID
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/subscription/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    """Verify Razorpay payment signature and activate subscription."""
    if not razorpay_client:
        return jsonify({
            'success': False,
            'error': 'Payment system not configured'
        }), 500

    try:
        data = request.json
        payment_id = data.get('razorpay_payment_id')
        order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')

        if not all([payment_id, order_id, signature]):
            return jsonify({
                'success': False,
                'error': 'Missing payment details'
            }), 400

        generated_signature = hmac.new(
            Config.RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != signature:
            return jsonify({
                'success': False,
                'error': 'Invalid payment signature'
            }), 400

        payment_doc = extensions.db.payments.find_one({
            'razorpay_order_id': order_id,
            'user_id': str(current_user.id)
        })

        if not payment_doc:
            return jsonify({
                'success': False,
                'error': 'Payment record not found'
            }), 404

        extensions.db.payments.update_one(
            {'_id': payment_doc['_id']},
            {
                '$set': {
                    'razorpay_payment_id': payment_id,
                    'status': 'captured',
                    'verified_at': datetime.utcnow()
                }
            }
        )

        plan_type = payment_doc.get('plan_type', 'monthly')
        subscription_duration = timedelta(days=30) if plan_type == 'monthly' else timedelta(days=365)

        subscription_started = datetime.utcnow()
        subscription_ends = subscription_started + subscription_duration

        extensions.db.users.update_one(
            {'_id': current_user.id},
            {
                '$set': {
                    'subscription_status': 'premium',
                    'subscription_started_at': subscription_started,
                    'subscription_ends_at': subscription_ends,
                    'updated_at': datetime.utcnow()
                }
            }
        )

        current_user.subscription_status = 'premium'

        return jsonify({
            'success': True,
            'message': 'Subscription activated successfully!',
            'subscription': {
                'status': 'premium',
                'started_at': subscription_started.isoformat(),
                'ends_at': subscription_ends.isoformat()
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user subscription."""
    try:
        user_data = extensions.db.users.find_one({'_id': current_user.id})

        if user_data.get('subscription_status') != 'premium':
            return jsonify({
                'success': False,
                'error': 'No active subscription to cancel'
            }), 400

        extensions.db.users.update_one(
            {'_id': current_user.id},
            {
                '$set': {
                    'subscription_status': 'cancelled',
                    'auto_renew': False,
                    'updated_at': datetime.utcnow()
                }
            }
        )

        current_user.subscription_status = 'cancelled'

        return jsonify({
            'success': True,
            'message': 'Subscription cancelled. You can continue using premium features until the end of your billing period.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/webhook/razorpay', methods=['POST'])
def razorpay_webhook():
    """Handle Razorpay webhook events."""
    if not razorpay_client or not Config.RAZORPAY_WEBHOOK_SECRET:
        return jsonify({'status': 'error', 'message': 'Webhook not configured'}), 500

    try:
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_body = request.data.decode('utf-8')

        razorpay_client.utility.verify_webhook_signature(
            webhook_body,
            webhook_signature,
            Config.RAZORPAY_WEBHOOK_SECRET
        )

        payload = request.json
        event_type = payload.get('event')

        extensions.db.webhooks.insert_one({
            'event_type': event_type,
            'payload': payload,
            'processed': False,
            'received_at': datetime.utcnow()
        })

        if event_type == 'payment.captured':
            handle_payment_captured(payload)
        elif event_type == 'subscription.cancelled':
            handle_subscription_cancelled(payload)
        elif event_type == 'subscription.halted':
            handle_subscription_halted(payload)

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


def handle_payment_captured(payload):
    """Handle successful payment capture."""
    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    order_id = payment_entity.get('order_id')

    if order_id:
        extensions.db.payments.update_one(
            {'razorpay_order_id': order_id},
            {
                '$set': {
                    'status': 'captured',
                    'updated_at': datetime.utcnow()
                }
            }
        )


def handle_subscription_cancelled(payload):
    """Handle subscription cancellation."""
    subscription_entity = payload.get('payload', {}).get('subscription', {}).get('entity', {})
    subscription_id = subscription_entity.get('id')

    if subscription_id:
        extensions.db.users.update_one(
            {'subscription_id': subscription_id},
            {
                '$set': {
                    'subscription_status': 'cancelled',
                    'auto_renew': False,
                    'updated_at': datetime.utcnow()
                }
            }
        )


def handle_subscription_halted(payload):
    """Handle subscription halt due to payment failure."""
    subscription_entity = payload.get('payload', {}).get('subscription', {}).get('entity', {})
    subscription_id = subscription_entity.get('id')

    if subscription_id:
        extensions.db.users.update_one(
            {'subscription_id': subscription_id},
            {
                '$set': {
                    'subscription_status': 'payment_failed',
                    'updated_at': datetime.utcnow()
                }
            }
        )


@bp.route('/subscription/check-status')
@login_required
def check_subscription_status():
    """Check and update subscription status."""
    try:
        user_data = extensions.db.users.find_one({'_id': current_user.id})

        subscription_status = user_data.get('subscription_status', 'free')
        ends_at = user_data.get('subscription_ends_at')

        if subscription_status == 'premium' and ends_at:
            if datetime.utcnow() > ends_at:
                extensions.db.users.update_one(
                    {'_id': current_user.id},
                    {
                        '$set': {
                            'subscription_status': 'expired',
                            'updated_at': datetime.utcnow()
                        }
                    }
                )
                subscription_status = 'expired'

        return jsonify({
            'success': True,
            'status': subscription_status,
            'ends_at': ends_at.isoformat() if ends_at else None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
