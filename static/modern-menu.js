/**
 * Copyright © 2025 Michal Kopecki - BTZ Zeiterfassung
 * Alle Rechte vorbehalten. Unerlaubte Nutzung, Vervielfältigung oder Verbreitung ist untersagt.
 */

/**
 * Modern Professional Menu JavaScript
 * Handles responsive behavior, accessibility, and smooth interactions
 */

class ModernMenu {
    constructor() {
        this.navbar = document.querySelector('.modern-navbar');
        this.menuToggle = document.querySelector('.mobile-menu-toggle');
        this.navbarMenu = document.querySelector('.navbar-menu');
        this.dropdownToggles = document.querySelectorAll('.dropdown-toggle');
        this.dropdownMenus = document.querySelectorAll('.dropdown-menu');
        this.navLinks = document.querySelectorAll('.nav-link');
        
        this.isMenuOpen = false;
        this.activeDropdown = null;
        this.scrollThreshold = 20;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupAccessibility();
        this.setupScrollBehavior();
        this.setupKeyboardNavigation();
        this.markActiveNavItem();
        this.initEnhancedFeatures();
    }
    
    setupEventListeners() {
        // Mobile menu toggle
        if (this.menuToggle && this.navbarMenu) {
            this.menuToggle.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleMobileMenu();
            });
        }
        
        // Dropdown toggles
        this.dropdownToggles.forEach(toggle => {
            // Mouse events for desktop
            toggle.addEventListener('mouseenter', () => {
                if (window.innerWidth > 768) {
                    this.openDropdown(toggle);
                }
            });
            
            toggle.parentElement.addEventListener('mouseleave', () => {
                if (window.innerWidth > 768) {
                    this.closeDropdown(toggle);
                }
            });
            
            // Click events for mobile
            toggle.addEventListener('click', (e) => {
                if (window.innerWidth <= 768) {
                    e.preventDefault();
                    this.toggleDropdown(toggle);
                }
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.navbar.contains(e.target)) {
                this.closeMobileMenu();
                this.closeAllDropdowns();
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize();
        });
        
        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeMobileMenu();
                this.closeAllDropdowns();
            }
        });
    }
    
    setupScrollBehavior() {
        let ticking = false;
        
        const updateNavbar = () => {
            const scrollY = window.scrollY;
            
            if (scrollY > this.scrollThreshold) {
                this.navbar.classList.add('scrolled');
            } else {
                this.navbar.classList.remove('scrolled');
            }
            
            ticking = false;
        };
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateNavbar);
                ticking = true;
            }
        });
    }
    
    setupAccessibility() {
        // Set initial ARIA states
        this.dropdownToggles.forEach(toggle => {
            toggle.setAttribute('aria-expanded', 'false');
            const menu = toggle.nextElementSibling;
            if (menu) {
                menu.setAttribute('aria-hidden', 'true');
            }
        });
        
        if (this.menuToggle) {
            this.menuToggle.setAttribute('aria-expanded', 'false');
        }
    }
    
    setupKeyboardNavigation() {
        // Handle arrow key navigation in dropdowns
        this.dropdownMenus.forEach(menu => {
            const items = menu.querySelectorAll('.dropdown-item');
            
            items.forEach((item, index) => {
                item.addEventListener('keydown', (e) => {
                    switch (e.key) {
                        case 'ArrowDown':
                            e.preventDefault();
                            const nextIndex = (index + 1) % items.length;
                            items[nextIndex].focus();
                            break;
                        case 'ArrowUp':
                            e.preventDefault();
                            const prevIndex = (index - 1 + items.length) % items.length;
                            items[prevIndex].focus();
                            break;
                        case 'Home':
                            e.preventDefault();
                            items[0].focus();
                            break;
                        case 'End':
                            e.preventDefault();
                            items[items.length - 1].focus();
                            break;
                    }
                });
            });
        });
    }
    
    markActiveNavItem() {
        const currentPath = window.location.pathname;
        
        this.navLinks.forEach(link => {
            const href = link.getAttribute('href');
            
            // Remove existing active class
            link.classList.remove('active');
            
            // Add active class if paths match
            if (href === currentPath || 
                (currentPath !== '/' && href !== '/' && currentPath.startsWith(href))) {
                link.classList.add('active');
            }
            
            // Special case for home page
            if (currentPath === '/' && href === '/') {
                link.classList.add('active');
            }
        });
    }
    
    toggleMobileMenu() {
        this.isMenuOpen = !this.isMenuOpen;
        
        if (this.isMenuOpen) {
            this.openMobileMenu();
        } else {
            this.closeMobileMenu();
        }
    }
    
    openMobileMenu() {
        this.isMenuOpen = true;
        this.navbarMenu.classList.add('active');
        this.menuToggle.setAttribute('aria-expanded', 'true');
        
        // Prevent body scroll when menu is open
        document.body.style.overflow = 'hidden';
        
        // Focus first nav item
        const firstNavLink = this.navbarMenu.querySelector('.nav-link');
        if (firstNavLink) {
            setTimeout(() => firstNavLink.focus(), 150);
        }
    }
    
    closeMobileMenu() {
        this.isMenuOpen = false;
        this.navbarMenu.classList.remove('active');
        this.menuToggle.setAttribute('aria-expanded', 'false');
        
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Close all dropdowns when closing mobile menu
        this.closeAllDropdowns();
    }
    
    toggleDropdown(toggle) {
        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        
        if (isExpanded) {
            this.closeDropdown(toggle);
        } else {
            this.closeAllDropdowns();
            this.openDropdown(toggle);
        }
    }
    
    openDropdown(toggle) {
        const menu = toggle.nextElementSibling;
        if (!menu) return;
        
        // Close other dropdowns first
        this.closeAllDropdowns();
        
        toggle.setAttribute('aria-expanded', 'true');
        menu.setAttribute('aria-hidden', 'false');
        this.activeDropdown = toggle;
        
        // Focus first item in dropdown for keyboard users
        if (document.activeElement === toggle) {
            const firstItem = menu.querySelector('.dropdown-item');
            if (firstItem) {
                setTimeout(() => firstItem.focus(), 50);
            }
        }
    }
    
    closeDropdown(toggle) {
        const menu = toggle.nextElementSibling;
        if (!menu) return;
        
        toggle.setAttribute('aria-expanded', 'false');
        menu.setAttribute('aria-hidden', 'true');
        
        if (this.activeDropdown === toggle) {
            this.activeDropdown = null;
        }
    }
    
    closeAllDropdowns() {
        this.dropdownToggles.forEach(toggle => {
            this.closeDropdown(toggle);
        });
    }
    
    // Enhanced features
    
    /**
     * Enhanced Features for Modern Menu
     */
    
    // Add notification badges to admin menu items
    addNotificationBadges() {
        const adminItems = document.querySelectorAll('[href="/deletion_requests"], [href="/user_management"]');
        adminItems.forEach(item => {
            const navItem = item.closest('.nav-item');
            if (navItem) {
                navItem.classList.add('has-notification');
            }
        });
    }
    
    // Enhanced loading states
    showLoadingState(element) {
        if (element) {
            element.classList.add('loading');
            element.setAttribute('aria-busy', 'true');
        }
    }
    
    hideLoadingState(element) {
        if (element) {
            element.classList.remove('loading');
            element.removeAttribute('aria-busy');
        }
    }
    
    // Page transition loading
    startPageTransition() {
        this.navbar.classList.add('page-loading');
    }
    
    endPageTransition() {
        this.navbar.classList.remove('page-loading');
    }
    
    // Enhanced touch interaction for mobile
    setupTouchInteractions() {
        if ('ontouchstart' in window) {
            const navLinks = document.querySelectorAll('.nav-link');
            
            navLinks.forEach(link => {
                let touchStartTime = 0;
                
                link.addEventListener('touchstart', (e) => {
                    touchStartTime = Date.now();
                    link.style.transform = 'scale(0.98)';
                }, { passive: true });
                
                link.addEventListener('touchend', (e) => {
                    const touchDuration = Date.now() - touchStartTime;
                    
                    setTimeout(() => {
                        link.style.transform = '';
                    }, 100);
                    
                    // Handle quick tap vs long press
                    if (touchDuration < 200) {
                        // Quick tap - proceed with navigation
                        if (link.tagName === 'A' && !e.defaultPrevented) {
                            this.startPageTransition();
                        }
                    }
                }, { passive: true });
                
                link.addEventListener('touchcancel', () => {
                    link.style.transform = '';
                }, { passive: true });
            });
        }
    }
    
    // Auto-hide mobile menu on orientation change
    handleOrientationChange() {
        if (window.innerWidth > 768 && this.isMenuOpen) {
            this.closeMobileMenu();
        }
    }
    
    // Enhanced keyboard navigation with arrow keys
    setupAdvancedKeyboardNavigation() {
        const navItems = this.navLinks;
        let currentIndex = -1;
        
        document.addEventListener('keydown', (e) => {
            if (!this.navbar.contains(document.activeElement)) return;
            
            switch (e.key) {
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    currentIndex = Math.min(currentIndex + 1, navItems.length - 1);
                    navItems[currentIndex]?.focus();
                    break;
                    
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    currentIndex = Math.max(currentIndex - 1, 0);
                    navItems[currentIndex]?.focus();
                    break;
                    
                case 'Home':
                    e.preventDefault();
                    currentIndex = 0;
                    navItems[currentIndex]?.focus();
                    break;
                    
                case 'End':
                    e.preventDefault();
                    currentIndex = navItems.length - 1;
                    navItems[currentIndex]?.focus();
                    break;
            }
        });
    }
    
    // Performance optimization: debounced resize handler
    handleResize() {
        clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => {
            this.handleOrientationChange();
            this.closeAllDropdowns();
            
            // Update mobile menu visibility
            if (window.innerWidth > 768 && this.isMenuOpen) {
                this.closeMobileMenu();
            }
        }, 150);
    }
    
    // Initialize all enhanced features
    initEnhancedFeatures() {
        this.addNotificationBadges();
        this.setupTouchInteractions();
        this.setupAdvancedKeyboardNavigation();
        
        // Add admin badges
        const adminOnlyItems = document.querySelectorAll('[href="/admin"], [href="/user_management"], [href="/break_settings"]');
        adminOnlyItems.forEach(item => {
            const navItem = item.closest('.nav-item');
            if (navItem) {
                navItem.classList.add('admin-only');
            }
        });
        
        // Mark current page
        const currentPath = window.location.pathname;
        const currentLink = document.querySelector(`a[href="${currentPath}"]`);
        if (currentLink) {
            currentLink.setAttribute('aria-current', 'page');
        }
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.startPageTransition();
        });
        
        // Handle page load completion
        window.addEventListener('load', () => {
            this.endPageTransition();
        });
    }
}

// Enhanced smooth scrolling for anchor links
function setupSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            
            if (target) {
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
                
                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Initialize menu when DOM is ready
function initializeMenu() {
    const menu = new ModernMenu();
    setupSmoothScrolling();
    
    // Make menu instance available globally for debugging/external access
    window.modernMenu = menu;
    
    return menu;
}

// Auto-initialize if DOM is already loaded, otherwise wait for DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMenu);
} else {
    initializeMenu();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ModernMenu, initializeMenu };
}
