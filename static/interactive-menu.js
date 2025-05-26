/**
 * Enhanced Interactive Menu System
 * Provides smooth animations, keyboard navigation, and better accessibility
 */

class InteractiveMenu {
    constructor() {
        this.init();
        this.bindEvents();
        this.setupKeyboardNavigation();
        this.setupMobileMenu();
    }

    init() {
        // Add menu state data attributes
        document.querySelectorAll('.dropdown-trigger').forEach(trigger => {
            trigger.setAttribute('aria-expanded', 'false');
            trigger.setAttribute('role', 'button');
            trigger.setAttribute('tabindex', '0');
        });

        // Add unique IDs to dropdowns for accessibility
        document.querySelectorAll('.dropdown-menu').forEach((menu, index) => {
            menu.setAttribute('id', `dropdown-menu-${index}`);
            menu.setAttribute('role', 'menu');
            menu.setAttribute('aria-hidden', 'true');
        });

        // Link triggers to their menus
        document.querySelectorAll('.dropdown-trigger').forEach((trigger, index) => {
            trigger.setAttribute('aria-controls', `dropdown-menu-${index}`);
        });
    }

    bindEvents() {
        // Enhanced hover handling with delays
        let hoverTimeout;
        
        document.querySelectorAll('.dropdown-container').forEach(container => {
            const trigger = container.querySelector('.dropdown-trigger');
            const menu = container.querySelector('.dropdown-menu');
            
            if (!trigger || !menu) return;

            // Mouse enter with delay
            container.addEventListener('mouseenter', () => {
                clearTimeout(hoverTimeout);
                this.showDropdown(trigger, menu);
            });

            // Mouse leave with delay
            container.addEventListener('mouseleave', () => {
                hoverTimeout = setTimeout(() => {
                    this.hideDropdown(trigger, menu);
                }, 150); // 150ms delay for better UX
            });

            // Click handling for mobile/touch devices
            trigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isVisible = menu.getAttribute('aria-hidden') === 'false';
                
                if (isVisible) {
                    this.hideDropdown(trigger, menu);
                } else {
                    // Close all other dropdowns first
                    this.closeAllDropdowns();
                    this.showDropdown(trigger, menu);
                }
            });

            // Enhanced menu item interactions
            menu.querySelectorAll('.dropdown-item').forEach((item, itemIndex) => {
                item.setAttribute('role', 'menuitem');
                item.setAttribute('tabindex', '-1');
                
                // Add ripple effect on click
                item.addEventListener('click', (e) => {
                    this.createRippleEffect(e, item);
                });

                // Enhanced hover effects
                item.addEventListener('mouseenter', () => {
                    item.classList.add('active');
                    item.style.transform = 'translateX(4px)';
                });

                item.addEventListener('mouseleave', () => {
                    item.classList.remove('active');
                    item.style.transform = 'translateX(0)';
                });
            });
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown-container')) {
                this.closeAllDropdowns();
            }
        });

        // Close dropdowns on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllDropdowns();
            }
        });
    }

    showDropdown(trigger, menu) {
        // Update ARIA attributes
        trigger.setAttribute('aria-expanded', 'true');
        menu.setAttribute('aria-hidden', 'false');

        // Add active classes
        trigger.classList.add('dropdown-active');
        menu.classList.add('dropdown-visible');

        // Animate the dropdown icon
        const icon = trigger.querySelector('.dropdown-icon');
        if (icon) {
            icon.style.transform = 'rotate(180deg)';
        }

        // Focus management
        const firstItem = menu.querySelector('.dropdown-item');
        if (firstItem && document.activeElement === trigger) {
            firstItem.focus();
        }

        // Add subtle animation delay for staggered effect
        const items = menu.querySelectorAll('.dropdown-item');
        items.forEach((item, index) => {
            item.style.transitionDelay = `${index * 30}ms`;
            item.classList.add('animate-in');
        });
    }

    hideDropdown(trigger, menu) {
        // Update ARIA attributes
        trigger.setAttribute('aria-expanded', 'false');
        menu.setAttribute('aria-hidden', 'true');

        // Remove active classes
        trigger.classList.remove('dropdown-active');
        menu.classList.remove('dropdown-visible');

        // Reset dropdown icon
        const icon = trigger.querySelector('.dropdown-icon');
        if (icon) {
            icon.style.transform = 'rotate(0deg)';
        }

        // Reset animation classes
        const items = menu.querySelectorAll('.dropdown-item');
        items.forEach(item => {
            item.style.transitionDelay = '0ms';
            item.classList.remove('animate-in');
        });
    }

    closeAllDropdowns() {
        document.querySelectorAll('.dropdown-container').forEach(container => {
            const trigger = container.querySelector('.dropdown-trigger');
            const menu = container.querySelector('.dropdown-menu');
            if (trigger && menu) {
                this.hideDropdown(trigger, menu);
            }
        });
    }

    setupKeyboardNavigation() {
        document.querySelectorAll('.dropdown-container').forEach(container => {
            const trigger = container.querySelector('.dropdown-trigger');
            const menu = container.querySelector('.dropdown-menu');
            const items = menu.querySelectorAll('.dropdown-item');
            
            trigger.addEventListener('keydown', (e) => {
                switch (e.key) {
                    case 'Enter':
                    case ' ':
                        e.preventDefault();
                        this.showDropdown(trigger, menu);
                        if (items.length > 0) {
                            items[0].focus();
                        }
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.showDropdown(trigger, menu);
                        if (items.length > 0) {
                            items[0].focus();
                        }
                        break;
                }
            });

            items.forEach((item, index) => {
                item.addEventListener('keydown', (e) => {
                    switch (e.key) {
                        case 'ArrowDown':
                            e.preventDefault();
                            const nextItem = items[index + 1] || items[0];
                            nextItem.focus();
                            break;
                        case 'ArrowUp':
                            e.preventDefault();
                            const prevItem = items[index - 1] || items[items.length - 1];
                            prevItem.focus();
                            break;
                        case 'Home':
                            e.preventDefault();
                            items[0].focus();
                            break;
                        case 'End':
                            e.preventDefault();
                            items[items.length - 1].focus();
                            break;
                        case 'Escape':
                            e.preventDefault();
                            this.hideDropdown(trigger, menu);
                            trigger.focus();
                            break;
                        case 'Tab':
                            // Allow normal tab behavior
                            this.hideDropdown(trigger, menu);
                            break;
                    }
                });
            });
        });
    }

    setupMobileMenu() {
        const mobileMenuButton = document.querySelector('.mobile-menu-button');
        const mobileMenu = document.querySelector('.mobile-menu');
        
        if (mobileMenuButton && mobileMenu) {
            mobileMenuButton.addEventListener('click', () => {
                const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
                
                mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
                mobileMenu.classList.toggle('hidden');
                
                // Animate hamburger icon
                const bars = mobileMenuButton.querySelectorAll('.bar');
                bars.forEach((bar, index) => {
                    if (!isExpanded) {
                        bar.style.transform = index === 0 ? 'rotate(45deg) translate(6px, 6px)' :
                                            index === 1 ? 'opacity(0)' :
                                            'rotate(-45deg) translate(6px, -6px)';
                    } else {
                        bar.style.transform = 'none';
                        bar.style.opacity = '1';
                    }
                });
            });
        }
    }

    createRippleEffect(event, element) {
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(59, 130, 246, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple-animation 0.6s ease-out;
            pointer-events: none;
            z-index: 1;
        `;
        
        // Add ripple animation keyframes if not already added
        if (!document.querySelector('#ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'ripple-styles';
            style.textContent = `
                @keyframes ripple-animation {
                    to {
                        transform: scale(2);
                        opacity: 0;
                    }
                }
                .dropdown-item {
                    position: relative;
                    overflow: hidden;
                }
                .dropdown-item.animate-in {
                    animation: slideInDown 0.3s ease-out forwards;
                }
                @keyframes slideInDown {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    // Method to programmatically trigger dropdown
    openDropdown(dropdownId) {
        const container = document.querySelector(`[data-dropdown="${dropdownId}"]`);
        if (container) {
            const trigger = container.querySelector('.dropdown-trigger');
            const menu = container.querySelector('.dropdown-menu');
            if (trigger && menu) {
                this.showDropdown(trigger, menu);
            }
        }
    }

    // Method to add notification badges
    addNotificationBadge(menuItemSelector, count = 0) {
        const menuItem = document.querySelector(menuItemSelector);
        if (menuItem && count > 0) {
            let badge = menuItem.querySelector('.notification-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'notification-badge';
                badge.style.cssText = `
                    position: absolute;
                    top: -2px;
                    right: -2px;
                    background: #ef4444;
                    color: white;
                    border-radius: 50%;
                    width: 18px;
                    height: 18px;
                    font-size: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                `;
                menuItem.style.position = 'relative';
                menuItem.appendChild(badge);
            }
            badge.textContent = count > 99 ? '99+' : count;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.interactiveMenu = new InteractiveMenu();
    
    // Example of adding notification badges (uncomment to test)
    // window.interactiveMenu.addNotificationBadge('a[href="/my_attendance"]', 3);
    // window.interactiveMenu.addNotificationBadge('a[href="/break_management"]', 1);
});

// Export for external use
window.InteractiveMenu = InteractiveMenu;
