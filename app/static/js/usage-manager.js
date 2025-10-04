// UsageManager: handles usage/limits, premium gating, UI updates, upgrade prompts
class UsageManager {
    constructor() {
        this.limits = null;
        this.usage = null;
        this.subscription = 'free';
        this.init();
    }
    async init() {
        await Promise.all([this.fetchLimits(), this.fetchUsage()]);
        this.updateUsageDisplay();
    }
    async fetchLimits() {
        const res = await fetch('/limits/current');
        const data = await res.json();
        this.limits = data;
        if ('subscription_status' in data) {
            this.subscription = data.subscription_status;
        } else {
            this.subscription = this.limits.premium_tools ? 'premium' : 'free';
        }
    }
    async fetchUsage() {
        const res = await fetch('/usage/check');
        this.usage = await res.json();
    }
    async refresh() {
        await this.fetchLimits();
        await this.fetchUsage();
        this.updateUsageDisplay();
    }
    checkDailyLimits(type) {
        if (!this.limits || !this.usage) return true;
        if (this.subscription === 'premium') return true;
        return (this.usage[type] || 0) < (this.limits[type + '_daily'] || 0);
    }
    isPremiumOperation(op) {
        // Sync with backend premium features
        return ['emboss', 'edges', 'enhance', 'batch', 'bulk_download'].includes(op);
    }
    updateUsageDisplay() {
        if (!this.limits || !this.usage) return;
        const editEl = document.getElementById('usage-edit-count');
        const aiEl = document.getElementById('usage-ai-count');
        const dlEl = document.getElementById('usage-download-count');
        if (this.subscription === 'premium') {
            if (editEl) editEl.textContent = 'Unlimited';
            if (aiEl) aiEl.textContent = 'Unlimited';
            if (dlEl) dlEl.textContent = 'Unlimited';
        } else {
            if (editEl) editEl.textContent = `${this.usage.edit || 0}/${this.limits.edit_daily}`;
            if (aiEl) aiEl.textContent = `${this.usage.ai || 0}/${this.limits.ai_daily}`;
            if (dlEl) dlEl.textContent = `${this.usage.download || 0}/${this.limits.download_daily}`;
        }
    }
    showUpgradePrompt(msg) {
        // Show modal with upgrade info
        const modal = document.getElementById('upgrade-modal');
        const modalMsg = document.getElementById('upgrade-modal-msg');
        if (modal && modalMsg) {
            modalMsg.textContent = msg || 'Unlock premium features and unlimited usage!';
            modal.style.display = 'block';
        }
    }
    previewPremiumFeature(op) {
        // Fetch and show premium feature preview
        fetch(`/features/premium-preview/${op}`)
            .then(res => res.json())
            .then(data => {
                this.showUpgradePrompt(data.benefits || 'Upgrade for advanced features!');
            });
    }
    canPerformOperation(op) {
        if (this.isPremiumOperation(op) && this.subscription !== 'premium') return false;
        return this.checkDailyLimits('edit');
    }
    canUseAI() {
        return this.checkDailyLimits('ai');
    }
    canDownload(ext) {
        if (this.subscription === 'premium') return true;
        if (!this.checkDailyLimits('download')) return false;
        return ['jpg', 'jpeg'].includes(ext.toLowerCase());
    }
    isPremiumFeature(op) {
        return this.isPremiumOperation(op);
    }
}
window.UsageManager = UsageManager;
