// Razorpay Payment Integration for ImageCraft

const PaymentManager = (function() {
    let razorpayKeyId = null;
    let orderData = null;

    function setKeyId(keyId) {
        razorpayKeyId = keyId;
    }

    function createSubscription(planId, onSuccess, onError) {
        ImageCraftApp.setLoading('.payment-btn', true);
        fetch('/create-subscription', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan_id: planId })
        })
        .then(res => res.json())
        .then(data => {
            ImageCraftApp.setLoading('.payment-btn', false);
            if (data.success && data.subscription_id) {
                initiatePayment(data.subscription_id, data.email, onSuccess, onError);
            } else {
                ImageCraftApp.showFlashMessage(data.error || 'Failed to create subscription', 'error');
                if (onError) onError(data.error);
            }
        })
        .catch(err => {
            ImageCraftApp.setLoading('.payment-btn', false);
            ImageCraftApp.showFlashMessage('Network error. Please try again.', 'error');
            if (onError) onError(err);
        });
    }

    function initiatePayment(subscription_id, email, onSuccess, onError) {
        if (!razorpayKeyId) {
            ImageCraftApp.showFlashMessage('Payment configuration error', 'error');
            return;
        }
        // Get success/cancel URLs from data attributes or fallback
        const upgradeBtn = document.getElementById('upgrade-btn');
        const successUrl = upgradeBtn?.dataset.successUrl || window.success_url || '/payment/success';
        const cancelUrl = upgradeBtn?.dataset.cancelUrl || window.cancel_url || '/payment/cancel';
        const options = {
            key: razorpayKeyId,
            subscription_id: subscription_id,
            name: 'ImageCraft Premium',
            description: 'Premium Subscription',
            handler: function (response) {
                // On payment success
                const params = new URLSearchParams({
                    razorpay_subscription_id: response.razorpay_subscription_id,
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_signature: response.razorpay_signature
                });
                window.location.href = `${successUrl}?${params.toString()}`;
            },
            modal: {
                ondismiss: function() {
                    window.location.href = cancelUrl;
                }
            },
            prefill: {
                email: email || '',
            },
            theme: {
                color: '#6e4cff'
            }
        };
        const rzp = new Razorpay(options);
        rzp.open();
    }

    function cancelSubscription(onSuccess, onError) {
        ImageCraftApp.setLoading('#cancel-sub-btn', true);
        fetch('/subscription/cancel', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            ImageCraftApp.setLoading('#cancel-sub-btn', false);
            if (data.success) {
                ImageCraftApp.showFlashMessage('Subscription cancelled', 'success');
                if (onSuccess) onSuccess();
            } else {
                ImageCraftApp.showFlashMessage(data.error || 'Failed to cancel subscription', 'error');
                if (onError) onError(data.error);
            }
        })
        .catch(err => {
            ImageCraftApp.setLoading('#cancel-sub-btn', false);
            ImageCraftApp.showFlashMessage('Network error. Please try again.', 'error');
            if (onError) onError(err);
        });
    }

    function reactivateSubscription(onSuccess, onError) {
        ImageCraftApp.setLoading('#reactivate-sub-btn', true);
        fetch('/subscription/reactivate', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            ImageCraftApp.setLoading('#reactivate-sub-btn', false);
            if (data.success) {
                ImageCraftApp.showFlashMessage('Subscription reactivated', 'success');
                if (onSuccess) onSuccess();
            } else {
                ImageCraftApp.showFlashMessage(data.error || 'Failed to reactivate subscription', 'error');
                if (onError) onError(data.error);
            }
        })
        .catch(err => {
            ImageCraftApp.setLoading('#reactivate-sub-btn', false);
            ImageCraftApp.showFlashMessage('Network error. Please try again.', 'error');
            if (onError) onError(err);
        });
    }

    function initializePricing() {
        const upgradeBtn = document.getElementById('upgrade-btn');
        if (!upgradeBtn) return;
        const keyId = upgradeBtn.dataset.razorpayKeyId;
        const isAuthenticated = upgradeBtn.dataset.userAuthenticated === '1';
        const planId = upgradeBtn.dataset.planId;
        if (!keyId) {
            upgradeBtn.disabled = true;
            ImageCraftApp.showFlashMessage('Payment temporarily unavailable. Please try again later.', 'error');
            return;
        }
        if (!isAuthenticated) {
            upgradeBtn.addEventListener('click', () => {
                window.location.href = `/login?next=${encodeURIComponent(location.pathname)}`;
            });
            return;
        }
        upgradeBtn.addEventListener('click', function() {
            setKeyId(keyId);
            createSubscription(planId, function() {}, function() {});
        });
    }

    return {
        setKeyId,
        createSubscription,
        cancelSubscription,
        reactivateSubscription,
        initializePricing,
    };
})();

document.addEventListener('DOMContentLoaded', function() {
    if (PaymentManager.initializePricing) {
        PaymentManager.initializePricing();
    }
});

window.PaymentManager = PaymentManager;
