// Universal Glass Morphism Animations for BTZ Zeiterfassung
// This script provides consistent animations and interactions across all pages

document.addEventListener('DOMContentLoaded', function() {
    console.log('Glass Morphism Animation System Loaded');
    
    // Add entrance animation to containers
    function addEntranceAnimations() {
        const containers = document.querySelectorAll('.container, .main-container, .content-wrapper, .glass-container');
        
        containers.forEach((container, index) => {
            // Skip if already animated or is menu container
            if (container.classList.contains('menu-panel') || container.hasAttribute('data-animated')) {
                return;
            }
            
            container.style.opacity = '0';
            container.style.transform = 'translateY(30px) scale(0.95)';
            
            setTimeout(() => {
                container.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                container.style.opacity = '1';
                container.style.transform = 'translateY(0) scale(1)';
                container.setAttribute('data-animated', 'true');
            }, 100 + (index * 100)); // Stagger animations for multiple containers
        });
    }
    
    // Add hover effects to cards
    function addCardHoverEffects() {
        const cards = document.querySelectorAll('.card, .info-box, .form-section, .glass-card, .dashboard-card');
        
        cards.forEach(card => {
            // Skip menu elements
            if (card.closest('.menu-panel')) {
                return;
            }
            
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    }
    
    // Add ripple effect to buttons
    function addRippleEffects() {
        const buttons = document.querySelectorAll('button:not(.menu button), .btn:not(.menu .btn), input[type="submit"]:not(.menu input[type="submit"]), .glass-button');
        
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Don't add ripple if it's a menu button or login form button
                if (this.closest('.menu-panel') || this.closest('.login-form')) {
                    return;
                }
                
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.cssText = `
                    position: absolute;
                    left: ${x}px;
                    top: ${y}px;
                    width: ${size}px;
                    height: ${size}px;
                    background: rgba(255, 255, 255, 0.3);
                    border-radius: 50%;
                    transform: scale(0);
                    animation: ripple 0.6s ease-out;
                    pointer-events: none;
                    z-index: 1000;
                `;
                
                this.style.position = 'relative';
                this.style.overflow = 'hidden';
                this.appendChild(ripple);
                
                setTimeout(() => {
                    if (ripple.parentNode) {
                        ripple.remove();
                    }
                }, 600);
            });
        });
    }
    
    // Enhanced form interactions
    function enhanceFormInteractions() {
        const forms = document.querySelectorAll('form:not(.login-form):not(.menu form)');
        
        forms.forEach(form => {
            const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
            
            if (submitButton) {
                form.addEventListener('submit', function(e) {
                    submitButton.classList.add('loading');
                    submitButton.style.pointerEvents = 'none';
                    
                    // Reset after 3 seconds if still loading (fallback)
                    setTimeout(() => {
                        submitButton.classList.remove('loading');
                        submitButton.style.pointerEvents = 'auto';
                    }, 3000);
                });
            }
        });
    }
    
    // Add floating label effects for inputs
    function addFloatingLabels() {
        const inputs = document.querySelectorAll('input[type="text"]:not(.menu input), input[type="password"]:not(.menu input), input[type="email"]:not(.menu input), input[type="number"]:not(.menu input), textarea:not(.menu textarea)');
        
        inputs.forEach(input => {
            // Skip if already has floating label or is in login form
            if (input.closest('.login-form') || input.hasAttribute('data-floating-label')) {
                return;
            }
            
            const placeholder = input.getAttribute('placeholder');
            if (!placeholder) return;
            
            // Create floating label
            const label = document.createElement('label');
            label.textContent = placeholder;
            label.style.cssText = `
                position: absolute;
                left: 1rem;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(255, 255, 255, 0.1);
                padding: 0 0.5rem;
                color: rgba(255, 255, 255, 0.7);
                font-size: 1rem;
                pointer-events: none;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                border-radius: 4px;
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
            `;
            
            // Wrap input in container for positioning
            const container = document.createElement('div');
            container.style.position = 'relative';
            input.parentNode.insertBefore(container, input);
            container.appendChild(input);
            container.appendChild(label);
            
            // Remove placeholder to avoid conflict
            input.removeAttribute('placeholder');
            input.setAttribute('data-floating-label', 'true');
            
            // Handle focus/blur events
            const updateLabel = () => {
                if (input.value || input === document.activeElement) {
                    label.style.top = '0';
                    label.style.transform = 'translateY(-50%) scale(0.85)';
                    label.style.color = 'rgba(255, 255, 255, 0.9)';
                    label.style.background = 'rgba(255, 255, 255, 0.2)';
                } else {
                    label.style.top = '50%';
                    label.style.transform = 'translateY(-50%)';
                    label.style.color = 'rgba(255, 255, 255, 0.7)';
                    label.style.background = 'rgba(255, 255, 255, 0.1)';
                }
            };
            
            input.addEventListener('focus', updateLabel);
            input.addEventListener('blur', updateLabel);
            input.addEventListener('input', updateLabel);
            
            // Initial check
            updateLabel();
        });
    }
    
    // Add smooth scroll to anchor links
    function addSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]:not(.menu a)');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
    
    // Initialize all animations and effects
    function initializeGlassMorphism() {
        addEntranceAnimations();
        addCardHoverEffects();
        addRippleEffects();
        enhanceFormInteractions();
        addFloatingLabels();
        addSmoothScrolling();
    }
    
    // Run initialization
    initializeGlassMorphism();
    
    // Re-run for dynamically added content
    const observer = new MutationObserver(function(mutations) {
        let shouldReinit = false;
        
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.matches('.container, .card, .form-section, button, input, textarea') ||
                            node.querySelector('.container, .card, .form-section, button, input, textarea')) {
                            shouldReinit = true;
                        }
                    }
                });
            }
        });
        
        if (shouldReinit) {
            setTimeout(initializeGlassMorphism, 100);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Add keyboard navigation enhancements
    document.addEventListener('keydown', function(e) {
        // ESC key to close modals or overlays
        if (e.key === 'Escape') {
            const loadingElements = document.querySelectorAll('.loading');
            loadingElements.forEach(el => {
                el.classList.remove('loading');
                el.style.pointerEvents = 'auto';
            });
        }
    });
    
    // Add focus management for better accessibility
    const focusableElements = 'button:not(.menu button), [href]:not(.menu a), input:not(.menu input), select:not(.menu select), textarea:not(.menu textarea), [tabindex]:not([tabindex="-1"])';
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const focusable = Array.from(document.querySelectorAll(focusableElements))
                .filter(el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));
            
            const firstFocusable = focusable[0];
            const lastFocusable = focusable[focusable.length - 1];
            
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
    });
});

// Add CSS for animations if not already present
if (!document.querySelector('#glass-morphism-animations-css')) {
    const style = document.createElement('style');
    style.id = 'glass-morphism-animations-css';
    style.textContent = `
        /* Glass Morphism Animation Styles */
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Loading state enhancements */
        .loading {
            position: relative;
            pointer-events: none;
            opacity: 0.7;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            margin: -10px 0 0 -10px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top: 2px solid rgba(255, 255, 255, 0.8);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            z-index: 1000;
        }
        
        /* Focus indicators for accessibility */
        button:focus:not(.menu button),
        input:focus:not(.menu input),
        select:focus:not(.menu select),
        textarea:focus:not(.menu textarea),
        a:focus:not(.menu a) {
            outline: 2px solid rgba(255, 255, 255, 0.8);
            outline-offset: 2px;
        }
        
        /* Smooth transitions for all interactive elements */
        button:not(.menu button),
        input:not(.menu input),
        select:not(.menu select),
        textarea:not(.menu textarea),
        .card, .info-box, .form-section, .glass-card {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
    `;
    document.head.appendChild(style);
}
