// ============================================================
// IMAGE EDITOR JAVASCRIPT - FIXED
// Handles image editing functionality and tools
// ============================================================

document.addEventListener('DOMContentLoaded', async function () {
    // Ensure ImageCraftApp global exists early
    if (typeof window.ImageCraftApp === 'undefined') {
        window.ImageCraftApp = {
            showFlashMessage: function (msg, type) {
                console.log(`${type ? type.toUpperCase() + ': ' : ''}${msg}`);
                alert(`${type ? type.toUpperCase() + ': ' : ''}${msg}`);
            },
            setLoading: function (btn, state) {
                if (!btn) return;
                btn.disabled = state;
                btn.textContent = state ? 'Processing...' : 'Apply';
            },
            makeRequest: async function (url, options = {}) {
                const res = await fetch(url, options);
                return res.json();
            }
        };
        console.warn("⚠️ ImageCraftApp placeholder initialized.");
    }

    // Initialize usageManager
    window.usageManager = new window.UsageManager();

    try {
        const res = await fetch('/limits/current');
        const data = await res.json();
        if (data.subscription_status && window.usageManager) {
            window.usageManager.subscription = data.subscription_status;
            console.log("Subscription status:", data.subscription_status);
        }
    } catch (err) {
        console.error('Failed to load subscription info:', err);
    }

    // Initialize editor UI and controls
    initializeEditor();

    // Upload button binding
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtnHero');
    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length) fileInput.form.submit();
        });
    }
});



// --- History Manager ---
class HistoryManager {
    constructor() {
        this.sessionId = null;
        this.position = 0;
        this.length = 1;
        this.history = [];
        this.subscriptionStatus = null;
    }
    setSubscriptionStatus(status) {
        this.subscriptionStatus = status;
    }
    startSession(sessionId) {
        this.sessionId = sessionId;
        this.position = 0;
        this.length = 1;
        this.history = [];
        this.updateStatus();
    }
    addOperation(operation, result) {
        if (!this.sessionId) return;
        const entry = {
            operation,
            processed_filename: result.processed_filename,
            params: result.params || {},
            sequence: typeof result.sequence === 'number' ? result.sequence : this.position + 1,
            history_id: result.history_id || null,
            edit_status: result.edit_status || 'temporary',
            expires_at: result.expires_at || null
        };
        // Truncate redo history if needed
        if (this.position < this.history.length - 1) {
            this.history = this.history.slice(0, this.position + 1);
        }
        this.history.push(entry);
        this.position = this.history.length - 1;
        this.length = this.history.length;
        this.updateStatus();
        this.updateButtons();
    }
    canUndo() { return this.position > 0; }
    canRedo() { return this.position < this.length - 1; }
    undo() {
        if (!this.canUndo()) return;
        this.navigate(this.position - 1, 'undo');
    }
    redo() {
        if (!this.canRedo()) return;
        this.navigate(this.position + 1, 'redo');
    }
    getCurrentState() {
        return this.history[this.position] || null;
    }
    loadHistory() {
        if (!this.sessionId) return;
        ImageCraftApp.makeRequest(`/history/${this.sessionId}`)
            .then(res => {
                if (res.success && Array.isArray(res.history)) {
                    this.history = res.history;
                    this.length = res.history.length;
                    this.position = this.length - 1;
                    this.updateStatus();
                    this.updateButtons();
                }
            });
    }
    navigate(pos, type) {
        if (!this.sessionId) return;
        showEditorLoading(true, type === 'undo' ? 'Undoing...' : 'Redoing...');
        ImageCraftApp.makeRequest(`/history/navigate/${this.sessionId}/${pos}`)
            .then(res => {
                showEditorLoading(false);
                if (res.success && res.state) {
                    this.position = res.state.sequence;
                    this.length = Math.max(this.length, this.position + 1);
                    this.updateStatus();
                    this.updateButtons();
                    // Update canvas
                    const canvasImg = document.querySelector('.canvas-image');
                    if (canvasImg) {
                        canvasImg.src = `/processed/${res.state.processed_filename}?t=${Date.now()}`;
                    }
                    ImageCraftApp.showFlashMessage(type === 'undo' ? 'Undo successful!' : 'Redo successful!', 'success');
                } else {
                    ImageCraftApp.showFlashMessage(res.error || 'History navigation failed', 'error');
                }
            })
            .catch(() => {
                showEditorLoading(false);
                ImageCraftApp.showFlashMessage('History navigation failed', 'error');
            });
    }
    updateStatus() {
        const status = getSessionIndicator('default');
        if (status) {
            let text = `Step ${this.position + 1} of ${this.length}`;
            const entry = this.history[this.position];
            if (entry) {
                if (entry.edit_status === 'permanent') {
                    text += ' | Permanent';
                    status.classList.add('permanent');
                    status.classList.remove('temporary');
                } else {
                    text += ' | Temporary';
                    status.classList.add('temporary');
                    status.classList.remove('permanent');
                    if (entry.expires_at) {
                        const exp = new Date(entry.expires_at);
                        const now = new Date();
                        const mins = Math.max(0, Math.round((exp - now) / 60000));
                        text += ` | Expires in ${mins} min`;
                    }
                }
            }
            if (this.subscriptionStatus) {
                text += ` | ${this.subscriptionStatus.charAt(0).toUpperCase() + this.subscriptionStatus.slice(1)}`;
            }
            status.innerText = text;
        }
    }
    updateButtons() {
        const undoBtn = document.getElementById('undo-btn');
        const redoBtn = document.getElementById('redo-btn');
        if (undoBtn) undoBtn.disabled = !this.canUndo();
        if (redoBtn) redoBtn.disabled = !this.canRedo();
    }
}

window.HistoryManager = new HistoryManager();

// --- Session Management ---
function getOrCreateSessionId(filename) {
    if (!filename) filename = getFilenameFromPath();
    const key = 'editorSessionId:' + filename;
    let sessionId = window.sessionStorage.getItem(key);
    if (!sessionId) {
        sessionId = 'sess_' + Math.random().toString(36).slice(2) + Date.now();
        window.sessionStorage.setItem(key, sessionId);
    }
    return sessionId;
}
function resetSession(filename) {
    if (!filename) filename = getFilenameFromPath();
    const key = 'editorSessionId:' + filename;
    window.sessionStorage.removeItem(key);
    window.HistoryManager.startSession(getOrCreateSessionId(filename));
}

function initializeEditor() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tab = button.getAttribute('data-tab');
            switchTab(tab, button);
        });
    });

    // File upload handling
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const uploadArea = document.querySelector('.upload-area');

    if (fileInput && uploadForm) {
        // File input change handler
        fileInput.addEventListener('change', handleFileSelection);

        // Drag and drop functionality
        if (uploadArea) {
            setupDragAndDrop(uploadArea, fileInput);
        }
    }

    // Tool button handlers
    setupToolButtons();

    // Filter sliders and controls
    setupFilterControls();

    // Download button
    setupDownloadButton();

    // Set subscription status for HistoryManager
    const container = document.querySelector('.editor-container');
    if (container) {
        const sub = container.getAttribute('data-subscription') || 'free';
        if (window.HistoryManager && typeof window.HistoryManager.setSubscriptionStatus === 'function') {
            window.HistoryManager.setSubscriptionStatus(sub);
        }
    }

    // Start session on load
    const filename = getFilenameFromPath();
    window.HistoryManager.startSession(getOrCreateSessionId(filename));
}

function switchTab(tabId, activeButton) {
    // Remove active class from all buttons and contents
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Add active class to clicked button and corresponding content
    activeButton.classList.add('active');
    const tabContent = document.getElementById(tabId);
    if (tabContent) {
        tabContent.classList.add('active');
    }
}

function handleFileSelection() {
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');

    if (fileInput.files && fileInput.files.length > 0) {
        const file = fileInput.files[0];

        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            ImageCraftApp.showFlashMessage('Please select a valid image file (PNG, JPG, JPEG, or GIF)', 'error');
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            ImageCraftApp.showFlashMessage('File size must be less than 10MB', 'error');
            return;
        }

        // Show loading state
        const submitBtn = uploadForm.querySelector('button');
        if (submitBtn) {
            ImageCraftApp.setLoading(submitBtn, true);
        }

        // Upload file via AJAX
        uploadFileAjax(file, uploadForm, submitBtn);
    }
}

function uploadFileAjax(file, form, submitBtn) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Get CSRF token
    const csrfToken = form.querySelector('input[name="csrf_token"]').value;
    formData.append('csrf_token', csrfToken);
    
    fetch('/api/images/upload', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Redirect to editing page with uploaded file
            window.location.href = `/editing/${data.filename}`;
        } else {
            ImageCraftApp.showFlashMessage(data.error || 'Upload failed', 'error');
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        ImageCraftApp.showFlashMessage('Upload failed. Please try again.', 'error');
    })
    .finally(() => {
        // Remove loading state
        if (submitBtn) {
            ImageCraftApp.setLoading(submitBtn, false);
        }
    });
}

function setupDragAndDrop(uploadArea, fileInput) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    uploadArea.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        uploadArea.classList.add('drag-over');
    }

    function unhighlight() {
        uploadArea.classList.remove('drag-over');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection();
        }
    }
}

// Configurable max dimension (sync with backend)
const MAX_DIM = (window.EDITOR_CONFIG && window.EDITOR_CONFIG.maxDim) || 5000;
let lastFocusedElement = null;

// --- Enhanced Crop Tool Modal ---
function openCropModal() {
    if (!getFilenameFromPath()) {
        ImageCraftApp.showFlashMessage('No image loaded. Please upload or select an image first.', 'error');
        return;
    }
    const modal = document.getElementById('crop-modal');
    const form = document.getElementById('crop-form');
    const currentDim = getCurrentImageDimensions();
    document.getElementById('crop-current-dim').textContent = formatDimensions(currentDim.width, currentDim.height);
    // Preset aspect ratios
    const presets = getAspectRatioPresets();
    const presetContainer = document.getElementById('crop-aspect-presets');
    presetContainer.innerHTML = '';
    presets.forEach(preset => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'preset-btn aspect-ratio-btn';
        btn.textContent = preset.label;
        btn.onclick = () => applyCropPreset(preset, currentDim);
        presetContainer.appendChild(btn);
    });
    // Set default values
    document.getElementById('crop-x').value = 0;
    document.getElementById('crop-y').value = 0;
    document.getElementById('crop-width').value = currentDim.width;
    document.getElementById('crop-height').value = currentDim.height;
    document.getElementById('crop-aspect-lock').checked = true;
    updateCropPreview();
    form.onsubmit = handleCropSubmit;
    ['crop-x', 'crop-y', 'crop-width', 'crop-height', 'crop-aspect-lock'].forEach(id => {
        document.getElementById(id).oninput = updateCropPreview;
    });
    // Accessibility: focus trap and esc
    lastFocusedElement = document.activeElement;
    modal.style.display = 'flex';
    setTimeout(() => { document.getElementById('crop-x').focus(); }, 100);
    modal.addEventListener('keydown', cropModalKeyHandler);
}
function closeCropModal() {
    const modal = document.getElementById('crop-modal');
    modal.style.display = 'none';
    modal.removeEventListener('keydown', cropModalKeyHandler);
    if (lastFocusedElement) lastFocusedElement.focus();
}
function cropModalKeyHandler(e) {
    if (e.key === 'Escape') closeCropModal();
    // Optionally trap focus
}
function applyCropPreset(preset, currentDim) {
    const aspect = preset.ratio;
    let w = currentDim.width, h = currentDim.height;
    if (aspect) {
        if (w / h > aspect) {
            w = Math.round(h * aspect);
        } else {
            h = Math.round(w / aspect);
        }
    }
    document.getElementById('crop-width').value = w;
    document.getElementById('crop-height').value = h;
    document.getElementById('crop-x').value = 0;
    document.getElementById('crop-y').value = 0;
    updateCropPreview();
}
function updateCropPreview(e) {
    const xInput = document.getElementById('crop-x');
    const yInput = document.getElementById('crop-y');
    const wInput = document.getElementById('crop-width');
    const hInput = document.getElementById('crop-height');
    let x = parseInt(xInput.value) || 0;
    let y = parseInt(yInput.value) || 0;
    let w = parseInt(wInput.value) || 0;
    let h = parseInt(hInput.value) || 0;
    const aspectLock = document.getElementById('crop-aspect-lock').checked;
    const currentDim = getCurrentImageDimensions();
    // Aspect ratio lock: auto-adjust paired field
    if (aspectLock && e && e.target) {
        const aspect = wInput.value && hInput.value ? w / h : currentDim.width / currentDim.height;
        if (e.target === wInput && h > 0) {
            h = Math.round(w / aspect);
            hInput.value = h;
        } else if (e.target === hInput && w > 0) {
            w = Math.round(h * aspect);
            wInput.value = w;
        }
    }
    let valid = validateCropInputs(x, y, w, h, currentDim);
    document.getElementById('crop-dim-preview').textContent = `Crop: ${w} x ${h} at (${x}, ${y})`;
    const errorEl = document.getElementById('crop-error');
    [xInput, yInput, wInput, hInput].forEach(input => {
        input.classList.remove('valid', 'invalid');
    });
    if (!valid) {
        errorEl.textContent = 'Invalid crop region.';
        [xInput, yInput, wInput, hInput].forEach(input => input.classList.add('invalid'));
        document.getElementById('crop-submit-btn').disabled = true;
    } else {
        errorEl.textContent = '';
        [xInput, yInput, wInput, hInput].forEach(input => input.classList.add('valid'));
        document.getElementById('crop-submit-btn').disabled = false;
    }
}
function validateCropInputs(x, y, w, h, currentDim) {
    if (x < 0 || y < 0 || w < 1 || h < 1) return false;
    if (x + w > currentDim.width || y + h > currentDim.height) return false;
    return true;
}
function handleCropSubmit(e) {
    e.preventDefault();
    if (!usageManager.canPerformOperation('crop')) {
        usageManager.showUpgradePrompt('Daily edit limit reached. Upgrade for unlimited edits.');
        return;
    }
    const x = parseInt(document.getElementById('crop-x').value) || 0;
    const y = parseInt(document.getElementById('crop-y').value) || 0;
    const w = parseInt(document.getElementById('crop-width').value) || 0;
    const h = parseInt(document.getElementById('crop-height').value) || 0;
    const currentDim = getCurrentImageDimensions();
    if (!validateCropInputs(x, y, w, h, currentDim)) {
        document.getElementById('crop-error').textContent = 'Invalid crop region.';
        return;
    }
    document.getElementById('crop-modal-loading').style.display = 'flex';
    const onComplete = () => {
        document.getElementById('crop-modal-loading').style.display = 'none';
        closeCropModal();
        document.removeEventListener('editor:operation-complete', onComplete);
    };
    document.addEventListener('editor:operation-complete', onComplete);
    runOperation('crop', { value: JSON.stringify({ x, y }), width: w, height: h });
}

// --- Enhanced Resize Tool Modal ---
function openResizeModal() {
    if (!getFilenameFromPath()) {
        ImageCraftApp.showFlashMessage('No image loaded. Please upload or select an image first.', 'error');
        return;
    }
    if (!usageManager.canPerformOperation('resize')) {
        usageManager.showUpgradePrompt('Daily edit limit reached. Upgrade for unlimited edits.');
        return;
    }
    const modal = document.getElementById('resize-modal');
    const form = document.getElementById('resize-form');
    const currentDim = getCurrentImageDimensions();
    document.getElementById('resize-current-dim').textContent = formatDimensions(currentDim.width, currentDim.height) + ` (max ${MAX_DIM})`;
    // Preset sizes
    const presets = getPresetSizes();
    const presetContainer = document.getElementById('resize-size-presets');
    presetContainer.innerHTML = '';
    presets.forEach(preset => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'preset-btn';
        btn.textContent = preset.label;
        btn.onclick = () => applyResizePreset(preset, currentDim);
        presetContainer.appendChild(btn);
    });
    document.getElementById('resize-width').value = currentDim.width;
    document.getElementById('resize-height').value = currentDim.height;
    document.getElementById('resize-aspect-lock').checked = true;
    document.querySelector('input[name="resize-method"][value="pixels"]').checked = true;
    updateResizePreview();
    form.onsubmit = handleResizeSubmit;
    ['resize-width', 'resize-height', 'resize-aspect-lock'].forEach(id => {
        document.getElementById(id).oninput = updateResizePreview;
    });
    document.querySelectorAll('input[name="resize-method"]').forEach(radio => {
        radio.onchange = updateResizePreview;
    });
    lastFocusedElement = document.activeElement;
    modal.style.display = 'flex';
    setTimeout(() => { document.getElementById('resize-width').focus(); }, 100);
    modal.addEventListener('keydown', resizeModalKeyHandler);
}
function closeResizeModal() {
    const modal = document.getElementById('resize-modal');
    modal.style.display = 'none';
    modal.removeEventListener('keydown', resizeModalKeyHandler);
    if (lastFocusedElement) lastFocusedElement.focus();
}
function resizeModalKeyHandler(e) {
    if (e.key === 'Escape') closeResizeModal();
}
function applyResizePreset(preset, currentDim) {
    document.getElementById('resize-width').value = preset.width;
    document.getElementById('resize-height').value = preset.height;
    updateResizePreview();
}
function updateResizePreview(e) {
    const wInput = document.getElementById('resize-width');
    const hInput = document.getElementById('resize-height');
    let w = parseInt(wInput.value) || 0;
    let h = parseInt(hInput.value) || 0;
    const aspectLock = document.getElementById('resize-aspect-lock').checked;
    const currentDim = getCurrentImageDimensions();
    const method = document.querySelector('input[name="resize-method"]:checked').value;
    let displayW = w, displayH = h;
    // Aspect ratio lock: auto-adjust paired field
    if (aspectLock && e && e.target) {
        const aspect = currentDim.width / currentDim.height;
        if (e.target === wInput && h > 0) {
            h = Math.round(w / aspect);
            hInput.value = h;
        } else if (e.target === hInput && w > 0) {
            w = Math.round(h * aspect);
            wInput.value = w;
        }
    }
    if (method === 'percent') {
        displayW = Math.round(currentDim.width * w / 100);
        displayH = Math.round(currentDim.height * h / 100);
    }
    let valid = validateResizeInputs(displayW, displayH, currentDim);
    document.getElementById('resize-dim-preview').textContent = method === 'percent'
        ? `Resize: ${w}% x ${h}% → ${displayW} x ${displayH}`
        : `Resize: ${w} x ${h}`;
    const errorEl = document.getElementById('resize-error');
    [wInput, hInput].forEach(input => {
        input.classList.remove('valid', 'invalid');
    });
    if (!valid) {
        errorEl.textContent = 'Invalid resize dimensions.';
        [wInput, hInput].forEach(input => input.classList.add('invalid'));
        document.getElementById('resize-submit-btn').disabled = true;
    } else {
        errorEl.textContent = '';
        [wInput, hInput].forEach(input => input.classList.add('valid'));
        document.getElementById('resize-submit-btn').disabled = false;
    }
}
function validateResizeInputs(w, h, currentDim) {
    if (w < 1 || h < 1) return false;
    if (w > MAX_DIM || h > MAX_DIM) return false;
    return true;
}
function handleResizeSubmit(e) {
    e.preventDefault();
    if (!usageManager.canPerformOperation('resize')) {
        usageManager.showUpgradePrompt('Daily edit limit reached. Upgrade for unlimited edits.');
        return;
    }
    const wInput = document.getElementById('resize-width');
    const hInput = document.getElementById('resize-height');
    let w = parseInt(wInput.value) || 0;
    let h = parseInt(hInput.value) || 0;
    const currentDim = getCurrentImageDimensions();
    const method = document.querySelector('input[name="resize-method"]:checked').value;
    if (method === 'percent') {
        w = Math.round(currentDim.width * w / 100);
        h = Math.round(currentDim.height * h / 100);
    }
    if (!validateResizeInputs(w, h, currentDim)) {
        document.getElementById('resize-error').textContent = 'Invalid resize dimensions.';
        return;
    }
    document.getElementById('resize-modal-loading').style.display = 'flex';
    const onComplete = () => {
        document.getElementById('resize-modal-loading').style.display = 'none';
        closeResizeModal();
        document.removeEventListener('editor:operation-complete', onComplete);
    };
    document.addEventListener('editor:operation-complete', onComplete);
    runOperation('resize', { width: w, height: h });
}

// --- Utility Functions ---
function getCurrentImageDimensions() {
    const img = document.querySelector('.canvas-image');
    if (img) {
        return { width: img.naturalWidth || 800, height: img.naturalHeight || 600 };
    }
    // Fallback
    return { width: 800, height: 600 };
}
function formatDimensions(w, h) {
    return `${w} x ${h}`;
}
function getPresetSizes() {
    return [
        { label: 'Small (800x600)', width: 800, height: 600 },
        { label: 'Medium (1200x900)', width: 1200, height: 900 },
        { label: 'Large (1920x1440)', width: 1920, height: 1440 },
    ];
}
function getAspectRatioPresets() {
    return [
        { label: '1:1', ratio: 1 },
        { label: '4:3', ratio: 4 / 3 },
        { label: '16:9', ratio: 16 / 9 },
        { label: 'Custom', ratio: null }
    ];
}

// --- Patch Tool Button Handlers ---
function setupToolButtons() {
    // Basic tool buttons (skip .tool-btn-full for resize)
    document.querySelectorAll('.tool-btn[data-op]').forEach(btn => {
        const op = btn.getAttribute('data-op');
        // Add lock badge for premium tools
        if (usageManager.isPremiumFeature(op)) {
            btn.classList.add('premium-tool');
            if (usageManager.subscription !== 'premium') {
                btn.insertAdjacentHTML('beforeend', '<span class="lock-badge" title="Premium"><i class="fa-solid fa-lock"></i></span>');
            }
        }
        btn.addEventListener('click', () => {
            if (!getFilenameFromPath()) {
                ImageCraftApp.showFlashMessage('No image loaded. Please upload or select an image first.', 'error');
                return;
            }
            if (!usageManager.canPerformOperation(op)) {
                if (usageManager.isPremiumFeature(op)) {
                    usageManager.previewPremiumFeature(op);
                } else {
                    usageManager.showUpgradePrompt('Daily edit limit reached. Upgrade for unlimited edits.');
                }
                return;
            }
            if (op === 'crop') {
                openCropModal();
                return;
            }
            if (op === 'resize') {
                openResizeModal();
                return;
            }
            const value = btn.getAttribute('data-value');
            runOperation(op, value ? { value } : {});
        });
    });
    // Quick filter buttons
    document.querySelectorAll('.btn-filter[data-op]').forEach(btn => {
        const op = btn.getAttribute('data-op');
        if (usageManager.isPremiumFeature(op)) {
            btn.classList.add('premium-tool');
            if (usageManager.subscription !== 'premium') {
                btn.insertAdjacentHTML('beforeend', '<span class="lock-badge" title="Premium"><i class="fa-solid fa-lock"></i></span>');
            }
        }
        btn.addEventListener('click', () => {
            if (!usageManager.canPerformOperation(op)) {
                if (usageManager.isPremiumFeature(op)) {
                    usageManager.previewPremiumFeature(op);
                } else {
                    usageManager.showUpgradePrompt('Daily edit limit reached. Upgrade for unlimited edits.');
                }
                return;
            }
            runOperation(op);
        });
    });
}

function setupFilterControls() {
    // Filter range sliders
    document.querySelectorAll('.filter-group').forEach(group => {
        const slider = group.querySelector('input[type="range"]');
        const label = group.querySelector('.filter-label');
        const applyBtn = group.querySelector('.apply-btn[data-op]');
        if (slider && label && applyBtn) {
            // Update label on slider change
            slider.addEventListener('input', () => {
                const operation = applyBtn.getAttribute('data-op');
                const value = slider.value;
                label.textContent = `${operation.charAt(0).toUpperCase() + operation.slice(1)}: ${value}`;
            });
            // Apply filter on button click
            applyBtn.addEventListener('click', () => {
                const operation = applyBtn.getAttribute('data-op');
                const value = slider.value;
                ImageCraftApp.setLoading(applyBtn, true);
                runOperation(operation, { value });
                // Reset loading state after AJAX completes
                const resetLoading = () => ImageCraftApp.setLoading(applyBtn, false);
                // Patch runOperation to call resetLoading in .then/.catch/finally
                // We'll use a global event for this instance
                document.addEventListener('editor:operation-complete', resetLoading, { once: true });
            });
        }
    });
}

function setupDownloadButton() {
    document.querySelectorAll('.btn-download').forEach(btn => {
        btn.addEventListener('click', () => {
            const ext = getDownloadExtension();
            if (!usageManager.canDownload(ext)) {
                usageManager.showUpgradePrompt('Download limit reached or format restricted. Upgrade for unlimited downloads and formats.');
                return;
            }
            handleDownload();
            refreshUsageCounters();
        });
    });
}

// --- Patch runOperation ---
function runOperation(operation, params = {}) {
    const filename = getFilenameFromPath();
    const processed = getProcessedFilename();
    if (!filename) {
        ImageCraftApp.showFlashMessage('No image selected for editing', 'error');
        return;
    }
    // Session
    const sessionId = getOrCreateSessionId(filename);
    params = { ...params, session_id: sessionId };
    if (processed) {
        params.processed = processed;
    }
    showEditorLoading(true);
    
    // Prepare request data for the new API
    const requestData = {
        operation: operation,
        filename: filename,
        ...params
    };
    
    fetch('/api/images/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
        },
        body: JSON.stringify(requestData)
    })
        .then(async res => {
            let data;
            try {
                data = await res.json();
            } catch (e) {
                data = { success: false, error: 'Server error: invalid response' };
            }
            if (!res.ok && !data.error) {
                data.error = `HTTP ${res.status}`;
            }
            return data;
        })
        .then(data => {
            if (data.upgrade_required) {
                usageManager.showUpgradePrompt(data.error || 'Upgrade required for this feature.');
                showEditorLoading(false);
                document.dispatchEvent(new Event('editor:operation-complete'));
                return;
            }
            if (data.job_id) {
                pollJobStatus(data.job_id, operation, sessionId);
                refreshUsageCounters();
            } else {
                showEditorLoading(false);
                document.dispatchEvent(new Event('editor:operation-complete'));
                ImageCraftApp.showFlashMessage(data.error || 'Failed to start edit', 'error');
            }
        })
        .catch(err => {
            showEditorLoading(false);
            document.dispatchEvent(new Event('editor:operation-complete'));
            ImageCraftApp.showFlashMessage('An error occurred while editing the image.', 'error');
            console.error('[editor.js] AJAX error:', err);
        });
}

function pollJobStatus(jobId, operation, sessionId, attempt = 0) {
    fetch(`/api/images/job-status/${jobId}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
        .then(async res => {
            let data;
            try {
                data = await res.json();
            } catch (e) {
                data = { status: 'error', error: 'Invalid response' };
            }
            return data;
        })
        .then(data => {
            let resultObj = data.result;
            if (typeof resultObj === 'string') {
                resultObj = { success: true, processed_filename: resultObj };
            }
            let statusText = '';
            if (data.status === 'queued' || data.status === 'deferred') {
                statusText = 'Queued...';
            } else if (data.status === 'started') {
                statusText = 'Processing...';
                if (data.progress) statusText += ` (${data.progress}%)`;
            }
            showEditorLoading(true, statusText);
            if (data.status === 'finished' && resultObj && resultObj.success) {
                showEditorLoading(false);
                document.dispatchEvent(new Event('editor:operation-complete'));
                // Update canvas image src
                const canvasImg = document.querySelector('.canvas-image');
                if (canvasImg) {
                    const newSrc = `/api/images/serve/processed/${resultObj.processed_filename}?t=${Date.now()}`;
                    canvasImg.src = newSrc;
                }
                // Update history
                if (resultObj.session_id) {
                    window.HistoryManager.sessionId = resultObj.session_id;
                }
                if (resultObj.edit_status) {
                    window.HistoryManager.addOperation(operation, resultObj);
                } else {
                    window.HistoryManager.addOperation(operation, resultObj);
                }
                if (resultObj.edit_status === 'permanent') {
                    ImageCraftApp.showFlashMessage(resultObj.message || 'Permanent edit applied!', 'success');
                } else {
                    let msg = resultObj.message || 'Edit applied!';
                    if (resultObj.expires_at) {
                        const exp = new Date(resultObj.expires_at);
                        const now = new Date();
                        const mins = Math.max(0, Math.round((exp - now) / 60000));
                        msg += ` (Expires in ${mins} min)`;
                    }
                    ImageCraftApp.showFlashMessage(msg, 'info');
                }
                refreshUsageCounters();
            } else if (data.status === 'failed') {
                showEditorLoading(false);
                document.dispatchEvent(new Event('editor:operation-complete'));
                ImageCraftApp.showFlashMessage(data.error || 'Edit failed', 'error');
            } else if (data.status === 'queued' || data.status === 'started' || data.status === 'deferred') {
                setTimeout(() => pollJobStatus(jobId, operation, sessionId, attempt + 1), 800);
            } else {
                showEditorLoading(false);
                document.dispatchEvent(new Event('editor:operation-complete'));
                ImageCraftApp.showFlashMessage('Unknown job status', 'error');
            }
        })
        .catch(err => {
            showEditorLoading(false);
            document.dispatchEvent(new Event('editor:operation-complete'));
            ImageCraftApp.showFlashMessage('Error polling job status', 'error');
            console.error('[editor.js] Poll error:', err);
        });
}

// --- Undo/Redo ---
function undoLastOperation() {
    window.HistoryManager.undo();
}
function redoLastOperation() {
    window.HistoryManager.redo();
}

// --- Keyboard Shortcuts ---
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        undoLastOperation();
    } else if (((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z')))) {
        e.preventDefault();
        redoLastOperation();
    }
});

function showEditorLoading(show, statusText = null) {
    let overlay = document.getElementById('editor-loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'editor-loading-overlay';
        overlay.innerHTML = '<div class="editor-spinner" aria-label="Processing..."></div><div class="editor-status" aria-live="polite"></div>';
        document.body.appendChild(overlay);
    }
    overlay.style.display = show ? 'flex' : 'none';
    const statusDiv = overlay.querySelector('.editor-status');
    if (statusDiv) {
        statusDiv.innerText = statusText || '';
    }
}

function getFilenameFromPath() {
    const path = window.location.pathname;
    const matches = path.match(/\/editing\/([^\/]+)/);
    return matches ? matches[1] : null;
}

function getProcessedFilename() {
    // Get processed filename from the page context
    const processedImg = document.querySelector('.canvas-image');
    if (processedImg && (processedImg.src.includes('/processed/') || processedImg.src.includes('/api/images/serve/processed/'))) {
        try {
            const url = new URL(processedImg.src, window.location.origin);
            const parts = url.pathname.split('/');
            return parts[parts.length - 1];
        } catch (e) {
            // fallback: split on ?
            const src = processedImg.src.split('/').pop();
            return src.split('?')[0];
        }
    }
    return null;
}

function getDownloadExtension() {
    const select = document.getElementById('download-format');
    if (select && select.value) return select.value.toLowerCase();
    return 'jpg'; // default fallback
}



function handleDownload() {
    const processedFilename = getProcessedFilename();

    if (processedFilename) {
        const downloadUrl = `/api/images/download/${processedFilename}`;

        // Create temporary link and click it
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = processedFilename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        ImageCraftApp.showFlashMessage('Download started!', 'success');
        refreshUsageCounters();
    } else {
        ImageCraftApp.showFlashMessage('No processed image to download', 'error');
    }
}

// Reset image to original
function resetImage() {
    const filename = getFilenameFromPath();
    if (filename) {
        window.location.href = `/editing/${filename}`;
    }
}

// Crop tool functionality
function initializeCropTool() {
    // This would initialize a crop selection overlay
    ImageCraftApp.showFlashMessage('Interactive crop tool coming soon!', 'info');
}

// Resize tool with custom dimensions
function showResizeDialog() {
    const width = prompt('Enter width (pixels):');
    const height = prompt('Enter height (pixels):');

    if (width && height) {
        const widthNum = parseInt(width);
        const heightNum = parseInt(height);

        if (widthNum > 0 && heightNum > 0 && widthNum <= 5000 && heightNum <= 5000) {
            runOperation('resize', { width: widthNum, height: heightNum });
        } else {
            ImageCraftApp.showFlashMessage('Please enter valid dimensions (1-5000 pixels)', 'error');
        }
    }
}

// --- Session Reset on New Image ---
window.addEventListener('DOMContentLoaded', function () {
    // If new image uploaded, reset session for this image only
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function () {
            resetSession(getFilenameFromPath());
        });
    }
});

// --- AI Edit Integration ---
function setupAIEdit() {
    const aiBtn = document.querySelector('.btn-ai-edit');
    const aiPrompt = document.getElementById('ai-command');
    const aiStrength = document.getElementById('ai-strength');
    const aiSteps = document.getElementById('ai-steps');
    const aiCounter = document.getElementById('ai-char-count');
    if (!aiBtn || !aiPrompt) return;
    aiBtn.disabled = false;
    aiBtn.innerText = 'AI Edit';
    aiPrompt.addEventListener('input', function () {
        if (aiCounter) aiCounter.innerText = `${aiPrompt.value.length}/250`;
        aiBtn.disabled = aiPrompt.value.trim().length === 0;
    });
    aiBtn.addEventListener('click', function () {
        if (!usageManager.canUseAI()) {
            usageManager.showUpgradePrompt('AI edit limit reached. Upgrade for unlimited AI edits.');
            return;
        }
        const prompt = aiPrompt.value.trim();
        if (!prompt) return;
        const filename = getFilenameFromPath();
        if (!filename) {
            aiBtn.disabled = true;
            aiBtn.title = 'Upload an image first';
        }
        aiBtn.disabled = true;
        aiBtn.innerText = 'Processing...';
        const processed = getProcessedFilename();
        const sessionId = getOrCreateSessionId(filename);
        const strength = aiStrength ? parseFloat(aiStrength.value) : 0.75;
        const steps = aiSteps ? parseInt(aiSteps.value) : 30;
        showEditorLoading(true, 'AI editing...');
        fetch('/api/ai/edit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            },
            body: JSON.stringify({
                filename: filename,
                prompt: prompt,
                processed: processed,
                session_id: sessionId,
                strength: strength,
                steps: steps
            })
        })
            .then(async res => {
                let data;
                try { data = await res.json(); } catch (e) { data = { success: false, error: 'Server error' }; }
                if (!res.ok && !data.error) data.error = `HTTP ${res.status}`;
                return data;
            })
            .then(data => {
                if (data.upgrade_required) {
                    usageManager.showUpgradePrompt(data.error || 'Upgrade required for this feature.');
                    showEditorLoading(false);
                    document.dispatchEvent(new Event('editor:operation-complete'));
                    return;
                }
                if (data.job_id) {
                    pollJobStatus(data.job_id, 'ai_edit', sessionId);
                    refreshUsageCounters();
                } else {
                    showEditorLoading(false);
                    aiBtn.disabled = false;
                    aiBtn.innerText = 'AI Edit';
                    ImageCraftApp.showFlashMessage(data.error || 'Failed to start AI edit', 'error');
                }
            })
            .catch(err => {
                showEditorLoading(false);
                aiBtn.disabled = false;
                aiBtn.innerText = 'AI Edit';
                ImageCraftApp.showFlashMessage('An error occurred while starting AI edit.', 'error');
                console.error('[editor.js] AI AJAX error:', err);
            });
    });
}

function setupAIControls() {
    const strengthSlider = document.getElementById('ai-strength');
    const stepsInput = document.getElementById('ai-steps');
    const aiEditBtn = document.querySelector('.btn-ai-edit');
    if (!strengthSlider || !stepsInput || !aiEditBtn) return;
    function clamp(val, min, max) {
        return Math.max(min, Math.min(max, val));
    }
    function updateAIControls() {
        if (usageManager.subscription !== 'premium') {
            strengthSlider.min = '0.3';
            strengthSlider.max = '0.7';
            stepsInput.min = '10';
            stepsInput.max = '20';
            // Clamp values
            strengthSlider.value = clamp(parseFloat(strengthSlider.value), 0.3, 0.7);
            stepsInput.value = clamp(parseInt(stepsInput.value), 10, 20);
        } else {
            strengthSlider.min = '0.1';
            strengthSlider.max = '1.0';
            stepsInput.min = '10';
            stepsInput.max = '50';
            // Clamp values
            strengthSlider.value = clamp(parseFloat(strengthSlider.value), 0.1, 1.0);
            stepsInput.value = clamp(parseInt(stepsInput.value), 10, 50);
        }
        aiEditBtn.disabled = !usageManager.canUseAI();
    }
    strengthSlider.addEventListener('input', updateAIControls);
    stepsInput.addEventListener('input', updateAIControls);
    updateAIControls();
    aiEditBtn.addEventListener('click', () => {
        if (!usageManager.canUseAI()) {
            usageManager.showUpgradePrompt('AI edit limit reached. Upgrade for unlimited AI edits.');
            return;
        }
        // ...existing AI edit logic...
    });
    // Listen for usage refresh events to update controls
    document.addEventListener('usage:refresh', updateAIControls);
}

function refreshUsageCounters() {
    if (window.usageManager && typeof window.usageManager.refresh === 'function') {
        window.usageManager.refresh();
        document.dispatchEvent(new Event('usage:refresh'));
    }
}

document.addEventListener('DOMContentLoaded', setupAIControls);

function getHistoryPanel(tab) {
    if (tab === 'ai') {
        return document.getElementById('history-panel-ai');
    }
    return document.getElementById('history-panel');
}

function getSessionIndicator(tab) {
    if (tab === 'ai') {
        return document.getElementById('session-indicator-ai');
    }
    return document.getElementById('session-indicator');
}

// --- Session Reset on New Image ---
window.addEventListener('DOMContentLoaded', function () {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function () {
            resetSession(getFilenameFromPath());
        });
    }
});

// --- AI setup ---
window.addEventListener('DOMContentLoaded', function () {
    setupAIEdit();
    setupAIControls();
});

// Export all major editor methods
window.ImageEditor = {
    openCropModal,
    closeCropModal,
    openResizeModal,
    closeResizeModal,
    undoLastOperation,
    redoLastOperation,
    runOperation
};
