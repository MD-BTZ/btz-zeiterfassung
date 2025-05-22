// Enhanced dropdown menu functionality for both mobile and desktop
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const menuToggle = document.getElementById('menu-toggle');
    const menuNavContainer = document.querySelector('.menu-nav-container');
    const menuNavItems = document.querySelectorAll('.menu-nav-item');
    
    // Toggle mobile menu
    function toggleMenu() {
        const isExpanded = menuNavContainer.classList.contains('active');
        menuNavContainer.classList.toggle('active');
        document.body.classList.toggle('menu-open', !isExpanded);
        
        if (menuToggle) {
            menuToggle.setAttribute('aria-expanded', !isExpanded);
            
            // Animate menu icon
            if (!isExpanded) {
                menuToggle.querySelector('.menu-icon').innerHTML = '✕';
                menuToggle.setAttribute('aria-label', 'Menü schließen');
            } else {
                menuToggle.querySelector('.menu-icon').innerHTML = '☰';
                menuToggle.setAttribute('aria-label', 'Menü öffnen');
            }
        }
        
        // Reset any active dropdowns when closing the menu
        if (isExpanded) {
            menuNavItems.forEach(item => item.classList.remove('active'));
        }
    }
    
    // Mobile: Toggle dropdown menus
    function setupMobileDropdowns() {
        menuNavItems.forEach(item => {
            const link = item.querySelector('.menu-nav-link');
            
            if (link) {
                link.addEventListener('click', function(e) {
                    // Only for mobile
                    if (window.innerWidth <= 900) {
                        e.preventDefault();
                        
                        const wasActive = item.classList.contains('active');
                        
                        // Close other dropdowns
                        menuNavItems.forEach(otherItem => {
                            otherItem.classList.remove('active');
                        });
                        
                        // Toggle this dropdown only if it wasn't already active
                        if (!wasActive) {
                            item.classList.add('active');
                        }
                    }
                });
            }
        });
    }
    
    // Add keyboard navigation for accessibility
    function setupKeyboardNavigation() {
        // For main nav items
        menuNavItems.forEach(item => {
            const link = item.querySelector('.menu-nav-link');
            
            if (link) {
                link.addEventListener('keydown', function(e) {
                    // Enter or Space opens the dropdown menu
                    if (e.key === 'Enter' || e.key === ' ') {
                        if (window.innerWidth <= 900) {
                            e.preventDefault();
                            item.classList.toggle('active');
                        }
                    }
                });
            }
        });
    }
    
    // Initialization function
    function init() {
        if (menuToggle && menuNavContainer) {
            // Setup mobile dropdowns
            setupMobileDropdowns();
            
            // Setup keyboard navigation
            setupKeyboardNavigation();
            
            // Toggle menu on button click
            menuToggle.addEventListener('click', function(e) {
                e.preventDefault();
                toggleMenu();
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', function(event) {
                if (window.innerWidth <= 900 && 
                    menuNavContainer.classList.contains('active') && 
                    !event.target.closest('.menu-panel') && 
                    event.target !== menuToggle) {
                    toggleMenu();
                }
            });
            
            // Close menu on Escape key
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape') {
                    if (menuNavContainer.classList.contains('active')) {
                        toggleMenu();
                    } else {
                        // If menu is closed, close any open dropdowns
                        menuNavItems.forEach(item => item.classList.remove('active'));
                    }
                }
            });
            
            // Update menu display on resize
            window.addEventListener('resize', function() {
                if (window.innerWidth > 900) {
                    menuNavContainer.classList.remove('active');
                    
                    if (menuToggle) {
                        menuToggle.querySelector('.menu-icon').innerHTML = '☰';
                        menuToggle.setAttribute('aria-expanded', 'false');
                    }
                    
                    // Remove body class
                    document.body.classList.remove('menu-open');
                    
                    // Remove all active states from mobile view
                    menuNavItems.forEach(item => item.classList.remove('active'));
                }
            });
        }
    }
    
    // Initialize the menu
    init();
});
