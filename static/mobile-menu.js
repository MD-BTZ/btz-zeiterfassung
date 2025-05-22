// Enhanced mobile and desktop menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const menuContainer = document.getElementById('menu-container');
    const menuItems = document.getElementById('menu-items');
    
    // Expand the first menu section by default on desktop
    function setDefaultExpandedSection() {
        if (window.innerWidth > 768) {
            const firstSection = document.querySelector('.menu-items > .menu-section:first-child');
            if (firstSection && !firstSection.classList.contains('expanded')) {
                firstSection.classList.add('expanded');
            }
        }
    }
    
    // Initialize the menu sections
    function initMenuSections() {
        const menuSections = document.querySelectorAll('.menu-section');
        menuSections.forEach(section => {
            // Don't auto-collapse the Account section (bottom)
            if (!section.classList.contains('menu-bottom')) {
                section.classList.remove('expanded');
            }
        });
        
        // Expand first section by default
        setDefaultExpandedSection();
    }
    
    if (menuToggle && menuContainer) {
        // Initialize sections
        initMenuSections();
        
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
                
                // For dropdown menu, scroll to top to show all options
                if (window.innerWidth <= 768) {
                    menuContainer.scrollTop = 0;
                    
                    // Expand the first section by default on mobile
                    const firstSection = document.querySelector('.menu-items > .menu-section:first-child');
                    if (firstSection && !firstSection.classList.contains('expanded')) {
                        firstSection.classList.add('expanded');
                    }
                }
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
                
                // When using dropdown menu, allow page to scroll again
                document.body.style.overflow = '';
            }
        });
        
        // Add click handlers for menu sections on both mobile and desktop
        const menuSectionTitles = document.querySelectorAll('.menu-section-title');
        menuSectionTitles.forEach(title => {
            title.addEventListener('click', function(event) {
                const section = this.parentElement;
                
                // Don't toggle if clicking on a link inside the title
                if (event.target.tagName === 'A') {
                    return;
                }
                
                // Toggle the expanded class
                section.classList.toggle('expanded');
                
                // On desktop, collapse other sections when one is expanded
                if (window.innerWidth > 768) {
                    const allSections = document.querySelectorAll('.menu-section');
                    allSections.forEach(otherSection => {
                        if (otherSection !== section && !otherSection.classList.contains('menu-bottom')) {
                            otherSection.classList.remove('expanded');
                        }
                    });
                } else {
                    // On mobile with dropdown menu, scroll the section into view
                    if (section.classList.contains('expanded')) {
                        const sectionTop = section.getBoundingClientRect().top;
                        const menuContainerTop = menuContainer.getBoundingClientRect().top;
                        const offset = sectionTop - menuContainerTop - 10; // 10px padding
                        
                        if (offset > 0) {
                            menuContainer.scrollBy({
                                top: offset,
                                behavior: 'smooth'
                            });
                        }
                    }
                }
            });
        });
        
        // Handle window resize - reset menu state when transitioning to desktop
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                if (window.innerWidth > 768) {
                    // Close mobile menu if open when transitioning to desktop
                    if (menuContainer.classList.contains('active')) {
                        menuContainer.classList.remove('active');
                        document.body.classList.remove('menu-open');
                        menuToggle.innerHTML = '☰';
                        menuToggle.setAttribute('aria-expanded', 'false');
                    }
                    
                    // Reset any mobile-specific styles
                    document.body.style.overflow = '';
                    menuContainer.style.right = '';
                    menuContainer.style.maxHeight = '';
                    menuContainer.style.opacity = '';
                    
                    // Set default expanded section on desktop
                    setDefaultExpandedSection();
                } else {
                    // On mobile, ensure menu is positioned correctly if open
                    if (menuContainer.classList.contains('active')) {
                        // For dropdown menu, reset scroll position
                        menuContainer.scrollTop = 0;
                    }
                }
            }, 100);
        });
    }
});
