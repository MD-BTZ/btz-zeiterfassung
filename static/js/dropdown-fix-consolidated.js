/**
 * CONSOLIDATED DROPDOWN MENU JAVASCRIPT FIX
 * Ensures dropdown functionality works across all browsers and devices
 * Resolves conflicts between multiple dropdown implementations
 */

(function() {
    'use strict';
    
    console.log('🔧 Loading consolidated dropdown menu fix...');
    
    // Wait for DOM to be ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }
    
    ready(function() {
        console.log('✅ DOM ready, initializing dropdown fixes...');
        
        // ===========================
        // DROPDOWN FUNCTIONALITY FIX
        // ===========================
        
        function initializeDropdowns() {
            const dropdownContainers = document.querySelectorAll('.dropdown-container, .menu-nav-item');
            
            console.log(`🔍 Found ${dropdownContainers.length} dropdown containers`);
            
            dropdownContainers.forEach((container, index) => {
                const trigger = container.querySelector('.menu-nav-link, .dropdown-trigger');
                const menu = container.querySelector('.dropdown-menu');
                const icon = container.querySelector('.dropdown-icon');
                
                if (!trigger || !menu) {
                    console.log(`⚠️ Skipping container ${index}: missing trigger or menu`);
                    return;
                }
                
                console.log(`✅ Setting up dropdown ${index}:`, {
                    trigger: trigger.textContent.trim(),
                    hasMenu: !!menu,
                    hasIcon: !!icon
                });
                
                // Remove any existing event listeners to prevent conflicts
                const newTrigger = trigger.cloneNode(true);
                trigger.parentNode.replaceChild(newTrigger, trigger);
                
                // Desktop hover functionality
                let hoverTimeout;
                
                container.addEventListener('mouseenter', function() {
                    clearTimeout(hoverTimeout);
                    if (window.innerWidth > 900) {
                        showDropdown(container, menu, icon);
                    }
                });
                
                container.addEventListener('mouseleave', function() {
                    if (window.innerWidth > 900) {
                        hoverTimeout = setTimeout(() => {
                            hideDropdown(container, menu, icon);
                        }, 150);
                    }
                });
                
                // Mobile click functionality
                newTrigger.addEventListener('click', function(e) {
                    if (window.innerWidth <= 900) {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        const isActive = container.classList.contains('active');
                        
                        // Close all other dropdowns
                        dropdownContainers.forEach(otherContainer => {
                            if (otherContainer !== container) {
                                hideDropdown(otherContainer, 
                                    otherContainer.querySelector('.dropdown-menu'),
                                    otherContainer.querySelector('.dropdown-icon'));
                            }
                        });
                        
                        // Toggle current dropdown
                        if (isActive) {
                            hideDropdown(container, menu, icon);
                        } else {
                            showDropdown(container, menu, icon);
                        }
                    }
                });
                
                // Keyboard accessibility
                newTrigger.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        const isActive = container.classList.contains('active');
                        if (isActive) {
                            hideDropdown(container, menu, icon);
                        } else {
                            showDropdown(container, menu, icon);
                        }
                    }
                    
                    if (e.key === 'Escape') {
                        hideDropdown(container, menu, icon);
                    }
                });
            });
        }
        
        function showDropdown(container, menu, icon) {
            console.log('📋 Showing dropdown for:', container);
            
            // Add active class
            container.classList.add('active');
            
            // Set ARIA attributes
            const trigger = container.querySelector('.menu-nav-link, .dropdown-trigger');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'true');
            }
            if (menu) {
                menu.setAttribute('aria-hidden', 'false');
            }
            
            // Show menu with CSS
            if (menu) {
                menu.style.opacity = '1';
                menu.style.visibility = 'visible';
                menu.style.transform = 'translateY(0) scale(1)';
                menu.style.maxHeight = window.innerWidth <= 900 ? '500px' : 'none';
            }
            
            // Rotate icon
            if (icon) {
                icon.style.transform = 'rotate(180deg)';
            }
        }
        
        function hideDropdown(container, menu, icon) {
            console.log('📋 Hiding dropdown for:', container);
            
            // Remove active class
            container.classList.remove('active');
            
            // Set ARIA attributes
            const trigger = container.querySelector('.menu-nav-link, .dropdown-trigger');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'false');
            }
            if (menu) {
                menu.setAttribute('aria-hidden', 'true');
            }
            
            // Hide menu with CSS
            if (menu) {
                menu.style.opacity = '0';
                menu.style.visibility = 'hidden';
                menu.style.transform = window.innerWidth <= 900 ? 
                    'translateY(0) scale(1)' : 'translateY(-10px) scale(0.95)';
                menu.style.maxHeight = window.innerWidth <= 900 ? '0' : 'none';
            }
            
            // Reset icon
            if (icon) {
                icon.style.transform = 'rotate(0deg)';
            }
        }
        
        // ===========================
        // MOBILE MENU FUNCTIONALITY
        // ===========================
        
        function initializeMobileMenu() {
            const menuToggle = document.getElementById('menu-toggle') || 
                             document.querySelector('.menu-toggle');
            const menuContainer = document.querySelector('.menu-nav-container') ||
                                document.querySelector('.menu-container');
            
            if (menuToggle && menuContainer) {
                console.log('📱 Setting up mobile menu toggle');
                
                menuToggle.addEventListener('click', function() {
                    const isActive = menuContainer.classList.contains('active');
                    
                    menuContainer.classList.toggle('active');
                    document.body.classList.toggle('menu-open', !isActive);
                    
                    menuToggle.setAttribute('aria-expanded', !isActive);
                    
                    // Update icon
                    const icon = menuToggle.querySelector('.menu-icon');
                    if (icon) {
                        icon.innerHTML = isActive ? '☰' : '✕';
                    }
                    
                    // Close all dropdowns when closing mobile menu
                    if (isActive) {
                        document.querySelectorAll('.dropdown-container, .menu-nav-item').forEach(container => {
                            hideDropdown(container,
                                container.querySelector('.dropdown-menu'),
                                container.querySelector('.dropdown-icon'));
                        });
                    }
                });
            }
        }
        
        // ===========================
        // CLOSE ON OUTSIDE CLICK
        // ===========================
        
        function initializeOutsideClick() {
            document.addEventListener('click', function(e) {
                const isInsideDropdown = e.target.closest('.dropdown-container, .menu-nav-item');
                const isMenuToggle = e.target.closest('.menu-toggle');
                
                if (!isInsideDropdown && !isMenuToggle) {
                    // Close all dropdowns
                    document.querySelectorAll('.dropdown-container, .menu-nav-item').forEach(container => {
                        hideDropdown(container,
                            container.querySelector('.dropdown-menu'),
                            container.querySelector('.dropdown-icon'));
                    });
                }
            });
        }
        
        // ===========================
        // RESIZE HANDLER
        // ===========================
        
        function initializeResizeHandler() {
            let resizeTimeout;
            
            window.addEventListener('resize', function() {
                clearTimeout(resizeTimeout);
                resizeTimeout = setTimeout(() => {
                    // Close all dropdowns on resize
                    document.querySelectorAll('.dropdown-container, .menu-nav-item').forEach(container => {
                        hideDropdown(container,
                            container.querySelector('.dropdown-menu'),
                            container.querySelector('.dropdown-icon'));
                    });
                    
                    // Close mobile menu if switching to desktop
                    if (window.innerWidth > 900) {
                        const menuContainer = document.querySelector('.menu-nav-container, .menu-container');
                        if (menuContainer) {
                            menuContainer.classList.remove('active');
                            document.body.classList.remove('menu-open');
                        }
                        
                        const menuToggle = document.getElementById('menu-toggle') || 
                                         document.querySelector('.menu-toggle');
                        if (menuToggle) {
                            menuToggle.setAttribute('aria-expanded', 'false');
                            const icon = menuToggle.querySelector('.menu-icon');
                            if (icon) {
                                icon.innerHTML = '☰';
                            }
                        }
                    }
                }, 250);
            });
        }
        
        // ===========================
        // INITIALIZATION
        // ===========================
        
        try {
            initializeDropdowns();
            initializeMobileMenu();
            initializeOutsideClick();
            initializeResizeHandler();
            
            console.log('✅ Consolidated dropdown menu fix loaded successfully!');
            
            // Debug info
            const dropdownCount = document.querySelectorAll('.dropdown-container, .menu-nav-item').length;
            const menuCount = document.querySelectorAll('.dropdown-menu').length;
            
            console.log(`📊 Menu debug info:`, {
                dropdownContainers: dropdownCount,
                dropdownMenus: menuCount,
                screenWidth: window.innerWidth,
                isMobile: window.innerWidth <= 900
            });
            
        } catch (error) {
            console.error('❌ Error initializing dropdown menu fix:', error);
        }
        
        // ===========================
        // GLOBAL DROPDOWN API
        // ===========================
        
        // Expose functions globally for debugging
        window.BTZDropdownAPI = {
            showDropdown: function(containerSelector) {
                const container = document.querySelector(containerSelector);
                if (container) {
                    showDropdown(container,
                        container.querySelector('.dropdown-menu'),
                        container.querySelector('.dropdown-icon'));
                }
            },
            hideDropdown: function(containerSelector) {
                const container = document.querySelector(containerSelector);
                if (container) {
                    hideDropdown(container,
                        container.querySelector('.dropdown-menu'),
                        container.querySelector('.dropdown-icon'));
                }
            },
            hideAllDropdowns: function() {
                document.querySelectorAll('.dropdown-container, .menu-nav-item').forEach(container => {
                    hideDropdown(container,
                        container.querySelector('.dropdown-menu'),
                        container.querySelector('.dropdown-icon'));
                });
            },
            debugInfo: function() {
                console.log('🔍 Dropdown Debug Info:', {
                    containers: document.querySelectorAll('.dropdown-container, .menu-nav-item').length,
                    menus: document.querySelectorAll('.dropdown-menu').length,
                    activeDropdowns: document.querySelectorAll('.dropdown-container.active, .menu-nav-item.active').length,
                    screenWidth: window.innerWidth,
                    isMobile: window.innerWidth <= 900
                });
            }
        };
    });
})();
