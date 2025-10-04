// ============================================================
// AUTHENTICATION JAVASCRIPT
// Handles login, register, and authentication forms
// ============================================================

if (window.ScriptLoader) window.ScriptLoader.markLoaded('auth.js');

document.addEventListener('DOMContentLoaded', function() {
    console.log('[auth.js] Initializing authentication forms...');
    
    // Simple form submission - no complex validation
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        console.log('[auth.js] Setting up login form...');
        loginForm.addEventListener('submit', function(e) {
            console.log('[auth.js] Login form submitted');
            console.log('[auth.js] Form action:', loginForm.action);
            console.log('[auth.js] Form method:', loginForm.method);
            console.log('[auth.js] Form data:', new FormData(loginForm));
            // Allow normal form submission - no preventDefault()
        });
        
        // Show/hide password functionality
        const passwordToggle = document.getElementById('toggle-password');
        const passwordField = document.getElementById('password');
        
        if (passwordToggle && passwordField) {
            passwordToggle.addEventListener('click', function() {
                const type = passwordField.type === 'password' ? 'text' : 'password';
                passwordField.type = type;
                
                const icon = passwordToggle.querySelector('i');
                if (icon) {
                    icon.className = type === 'password' ? 'fa fa-eye' : 'fa fa-eye-slash';
                }
            });
        }
    }
    
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        console.log('[auth.js] Setting up register form...');
        registerForm.addEventListener('submit', function(e) {
            console.log('[auth.js] Register form submitted');
            // Allow normal form submission - no preventDefault()
        });
    }
});

// Check username availability
function checkUsernameAvailability(username, field) {
    // This would typically make an AJAX request to check availability
    // For now, we'll just do client-side validation
    
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        field.classList.add('error');
        return;
    }
    
    field.classList.remove('error');
    
    // You can implement an actual availability check here
    // ImageCraftApp.makeRequest('/check-username', {
    //     method: 'POST',
    //     body: JSON.stringify({ username: username })
    // }).then(response => {
    //     if (!response.available) {
    //         showFieldError(field, 'Username is already taken');
    //     }
    // }).catch(error => {
    //     console.error('Username check failed:', error);
    // });
}

// Password strength indicator
function updatePasswordStrength(passwordField) {
    let strengthIndicator = passwordField.parentElement.querySelector('.password-strength');
    
    if (!strengthIndicator) {
        strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'password-strength';
        passwordField.parentElement.appendChild(strengthIndicator);
    }
    
    const password = passwordField.value;
    const strength = calculatePasswordStrength(password);
    
    strengthIndicator.className = `password-strength strength-${strength.level}`;
    strengthIndicator.innerHTML = `
        <div class="strength-bar">
            <div class="strength-fill" style="width: ${strength.score}%"></div>
        </div>
        <span class="strength-text">${strength.text}</span>
    `;
}

// Calculate password strength
function calculatePasswordStrength(password) {
    if (!password) return { level: 'none', score: 0, text: '' };
    
    let score = 0;
    const checks = {
        length: password.length >= 8,
        lowercase: /[a-z]/.test(password),
        uppercase: /[A-Z]/.test(password),
        numbers: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    // Calculate score
    Object.values(checks).forEach(check => {
        if (check) score += 20;
    });
    
    // Determine level and text
    let level, text;
    if (score < 40) {
        level = 'weak';
        text = 'Weak';
    } else if (score < 60) {
        level = 'fair';
        text = 'Fair';
    } else if (score < 80) {
        level = 'good';
        text = 'Good';
    } else {
        level = 'strong';
        text = 'Strong';
    }
    
    return { level, score, text };
}

// Show/hide password toggle
function togglePassword(toggleBtn, passwordFieldId) {
    const passwordField = document.getElementById(passwordFieldId);
    const icon = toggleBtn.querySelector('i');
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        icon.className = 'fa fa-eye-slash';
    } else {
        passwordField.type = 'password';
        icon.className = 'fa fa-eye';
    }
}
