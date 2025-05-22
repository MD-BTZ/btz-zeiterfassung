// Enhanced mobile menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const menuContainer = document.getElementById('menu-container');
    const menuItems = document.getElementById('menu-items');
    
    if (menuToggle && menuContainer) {
        // Toggle menu when hamburger icon is clicked
        menuToggle.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            document.body.classList.toggle('menu-open');
            menuContainer.classList.toggle('active');
            menuToggle.setAttribute('aria-expanded', menuContainer.classList.contains('active'));
            
            // Toggle accessibility attributes
            if (menuContainer.classList.contains('active')) {
                menuToggle.innerHTML = '✕'; // Change to X when open
                menuToggle.setAttribute('aria-label', 'Menü schließen');
            } else {
                menuToggle.innerHTML = '☰'; // Change back to hamburger icon when closed
                menuToggle.setAttribute('aria-label', 'Menü öffnen');
            }
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInsideMenu = menuContainer.contains(event.target) || menuToggle.contains(event.target);
            if (!isClickInsideMenu && menuContainer.classList.contains('active')) {
                menuContainer.classList.remove('active');
                document.body.classList.remove('menu-open');
                menuToggle.innerHTML = '☰';
                menuToggle.setAttribute('aria-expanded', 'false');
                menuToggle.setAttribute('aria-label', 'Menü öffnen');
            }
        });
        
        // Add click handlers for menu sections on mobile
        const menuSections = document.querySelectorAll('.menu-section-title');
        menuSections.forEach(section => {
            section.addEventListener('click', function() {
                // Only apply this behavior on mobile
                if (window.innerWidth <= 768) {
                    this.parentElement.classList.toggle('expanded');
                }
            });
        });
        
        // Handle window resize - reset menu state when transitioning to desktop
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                if (window.innerWidth > 768 && menuContainer.classList.contains('active')) {
                    menuContainer.classList.remove('active');
                    document.body.classList.remove('menu-open');
                    menuToggle.innerHTML = '☰';
                    menuToggle.setAttribute('aria-expanded', 'false');
                }
                
                // Ensure menu is visible and properly positioned after resize
                if (window.innerWidth > 768) {
                    menuContainer.style.right = '';
                }
            }, 100);
        });
    }
});
