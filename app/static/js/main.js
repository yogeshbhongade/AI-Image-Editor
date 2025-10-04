// ============================================================
// MAIN APPLICATION JAVASCRIPT
// Common functions used across the entire application
// ============================================================

// Flash message handling
function showFlashMessage(message, type = 'info') {
    const flashContainer = document.getElementById('flash-messages') || createFlashContainer();
    
    const flashDiv = document.createElement('div');
    flashDiv.className = `flash-message flash-${type}`;
    flashDiv.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="flash-close">&times;</button>
    `;
    
    flashContainer.appendChild(flashDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (flashDiv.parentElement) {
            flashDiv.remove();
        }
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.id = 'flash-messages';
    container.className = 'flash-container';
    document.body.insertBefore(container, document.body.firstChild);
    return container;
}

// CSRF Token Management
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function setCSRFHeaders(headers) {
    headers['X-CSRFToken'] = getCSRFToken();
}

// Enhanced AJAX with CSRF, timeout, retry, and validation
function makeRequest(url, options = {}) {
    options.headers = options.headers || {};
    setCSRFHeaders(options.headers);
    options.timeout = options.timeout || 10000;
    return new Promise((resolve, reject) => {
        const controller = new AbortController();
        options.signal = controller.signal;
        const timeout = setTimeout(() => {
            controller.abort();
            reject(new Error('Request timed out'));
        }, options.timeout);
        fetch(url, options)
            .then(response => {
                clearTimeout(timeout);
                if (response.status === 429) {
                    showRateLimitWarning();
                    reject(new Error('Rate limit exceeded'));
                }
                if (!response.ok) throw response;
                return response.json();
            })
            .then(resolve)
            .catch(err => {
                handleSecurityError(err);
                reject(err);
            });
    });
}

function sanitizeInput(input) {
    const div = document.createElement('div');
    div.textContent = input;
    return div.innerHTML;
}

function validateFileInput(file) {
    const allowed = ['image/jpeg', 'image/png', 'image/gif'];
    if (!allowed.includes(file.type)) return false;
    if (file.size > 10 * 1024 * 1024) return false;
    return true;
}

function validateFormData(formData) {
    // Basic: check for empty required fields
    for (let [k, v] of formData.entries()) {
        if (!v) return false;
    }
    return true;
}

function handleSecurityError(error) {
    if (error && error.status === 403) showSecurityWarning('Security error: CSRF or permission denied.');
}

function logSecurityEvent(event) {
    // Optionally send to backend or log
    console.log('[SECURITY EVENT]', event);
}

function showSecurityWarning(message) {
    showFlashMessage(message, 'error');
}

function handleRateLimit(response) {
    showRateLimitWarning();
}

function showRateLimitWarning() {
    showFlashMessage('You are being rate limited. Please wait and try again.', 'warning');
}

function retryAfterDelay(request, delay) {
    setTimeout(request, delay);
}

// Form validation
function validateForm(formId, rules) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    
    for (const field in rules) {
        const input = form.querySelector(`[name="${field}"]`);
        if (!input) continue;
        
        const rule = rules[field];
        const value = input.value.trim();
        
        // Clear previous errors
        clearFieldError(input);
        
        // Required validation
        if (rule.required && !value) {
            showFieldError(input, `${rule.label || field} is required`);
            isValid = false;
            continue;
        }
        
        // Min length validation
        if (rule.minLength && value.length < rule.minLength) {
            showFieldError(input, `${rule.label || field} must be at least ${rule.minLength} characters`);
            isValid = false;
            continue;
        }
        
        // Email validation
        if (rule.email && value && !isValidEmail(value)) {
            showFieldError(input, 'Please enter a valid email address');
            isValid = false;
            continue;
        }
        
        // Custom validation
        if (rule.validate && value && !rule.validate(value)) {
            showFieldError(input, rule.message || 'Invalid value');
            isValid = false;
            continue;
        }
    }
    
    return isValid;
}

function showFieldError(input, message) {
    input.classList.add('error');
    
    // Remove existing error message
    const existingError = input.parentElement.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.textContent = message;
    input.parentElement.appendChild(errorDiv);
}

function clearFieldError(input) {
    input.classList.remove('error');
    const errorMsg = input.parentElement.querySelector('.field-error');
    if (errorMsg) {
        errorMsg.remove();
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Loading state management
function setLoading(element, loading = true) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (!element) return;
    
    if (loading) {
        element.classList.add('loading');
        element.disabled = true;
        const originalText = element.textContent;
        element.dataset.originalText = originalText;
        element.textContent = 'Loading...';
    } else {
        element.classList.remove('loading');
        element.disabled = false;
        if (element.dataset.originalText) {
            element.textContent = element.dataset.originalText;
            delete element.dataset.originalText;
        }
    }
}

// Modal handling
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        modal.classList.add('show');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        closeModal(event.target.id);
    }
});

// Navigation handling
function handleNavigation() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav a');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    handleNavigation();
    
    // Handle flash message close buttons
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('flash-close')) {
            event.target.parentElement.remove();
        }
    });
    
    // Handle dropdown menus only if present
    const dropdowns = document.querySelectorAll('.dropdown');
    if (dropdowns.length > 0) {
        dropdowns.forEach(dropdown => {
            const button = dropdown.querySelector('.dropbtn');
            const content = dropdown.querySelector('.dropdown-content');
            if (button && content) {
                button.addEventListener('click', function(e) {
                    e.stopPropagation();
                    content.classList.toggle('show');
                });
            }
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', function() {
            const dropdownContents = document.querySelectorAll('.dropdown-content');
            dropdownContents.forEach(content => content.classList.remove('show'));
        });
    }
});

// Export functions for use in other scripts
window.ImageCraftApp = {
    showFlashMessage,
    validateForm,
    makeRequest,
    setLoading,
    openModal,
    closeModal
};
if (window.ScriptLoader) {
    window.ScriptLoader.markLoaded('main.js');
    window.ScriptLoader.markLoaded('ImageCraftApp');
}
