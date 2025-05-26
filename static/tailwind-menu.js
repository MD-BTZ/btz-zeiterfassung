document.addEventListener('DOMContentLoaded', function() {
  // Check if Alpine.js is loaded, if not add it (needed for dropdowns)
  if (typeof window.Alpine === 'undefined') {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/gh/alpinejs/alpine@v2.8.2/dist/alpine.min.js';
    script.defer = true;
    document.head.appendChild(script);
  }

  // Mobile menu toggle
  const mobileMenuButton = document.querySelector('.mobile-menu-button');
  const mobileMenu = document.querySelector('.mobile-menu');

  if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', function() {
      // Toggle mobile menu visibility
      mobileMenu.classList.toggle('hidden');
      
      // Toggle between menu and close icons
      const menuIcon = this.querySelector('.block');
      const closeIcon = this.querySelector('.hidden');
      
      menuIcon.classList.toggle('hidden');
      closeIcon.classList.toggle('hidden');
    });
  }

  // Add scroll event for sticky behavior
  window.addEventListener('scroll', function() {
    const nav = document.querySelector('nav');
    if (window.scrollY > 10) {
      nav.classList.add('shadow-md');
      nav.classList.add('bg-white/95');
      nav.classList.add('backdrop-blur-sm');
      nav.classList.remove('bg-white');
    } else {
      nav.classList.remove('shadow-md');
      nav.classList.remove('bg-white/95');
      nav.classList.remove('backdrop-blur-sm');
      nav.classList.add('bg-white');
    }
  });

  // Highlight current page in navigation
  const highlightCurrentPage = () => {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
      const linkPath = new URL(link.href).pathname;
      if (linkPath === currentPath) {
        // For desktop
        if (link.classList.contains('border-b-2')) {
          link.classList.remove('border-transparent', 'text-gray-500');
          link.classList.add('border-indigo-500', 'text-indigo-600');
        }
        // For mobile
        else if (link.classList.contains('border-l-4')) {
          link.classList.remove('border-transparent', 'text-gray-600');
          link.classList.add('border-indigo-500', 'text-indigo-600');
        }
        // For dropdowns
        else if (link.classList.contains('block')) {
          link.classList.add('text-indigo-600', 'bg-indigo-50');
        }
      }
    });
  };

  highlightCurrentPage();

  // Add keyboard navigation for accessibility
  const setupKeyboardNav = () => {
    const dropdownButtons = document.querySelectorAll('[aria-expanded]');
    
    dropdownButtons.forEach(button => {
      button.addEventListener('keydown', function(e) {
        // Open dropdown on Enter or Space
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          
          const isExpanded = this.getAttribute('aria-expanded') === 'true';
          this.setAttribute('aria-expanded', !isExpanded);
          
          // Find the dropdown menu
          const dropdownId = this.getAttribute('aria-controls');
          const dropdown = dropdownId ? 
            document.getElementById(dropdownId) : 
            this.nextElementSibling;
          
          if (dropdown) {
            if (!isExpanded) {
              dropdown.classList.remove('hidden');
              // Focus the first menu item
              const firstItem = dropdown.querySelector('a');
              if (firstItem) firstItem.focus();
            } else {
              dropdown.classList.add('hidden');
            }
          }
        }
        
        // Close dropdown on Escape
        if (e.key === 'Escape') {
          this.setAttribute('aria-expanded', 'false');
          const dropdown = this.nextElementSibling;
          if (dropdown) dropdown.classList.add('hidden');
          this.focus();
        }
      });
    });
    
    // Handle keyboard navigation within dropdowns
    const dropdownMenus = document.querySelectorAll('[role="menu"]');
    
    dropdownMenus.forEach(menu => {
      const items = menu.querySelectorAll('[role="menuitem"]');
      
      items.forEach((item, index) => {
        item.addEventListener('keydown', function(e) {
          // Move focus to next item on ArrowDown
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextItem = items[index + 1] || items[0];
            nextItem.focus();
          }
          
          // Move focus to previous item on ArrowUp
          if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prevItem = items[index - 1] || items[items.length - 1];
            prevItem.focus();
          }
          
          // Close dropdown and return focus to button on Escape
          if (e.key === 'Escape') {
            e.preventDefault();
            const button = menu.previousElementSibling;
            button.setAttribute('aria-expanded', 'false');
            menu.classList.add('hidden');
            button.focus();
          }
        });
      });
    });
  };
  
  setupKeyboardNav();

  // Close dropdowns when clicking outside
  document.addEventListener('click', function(event) {
    const dropdown = document.querySelector('[role="menu"]:not(.hidden)');
    if (dropdown) {
      const isClickInside = dropdown.contains(event.target);
      const isClickOnToggle = event.target.closest('[aria-expanded]');
      
      if (!isClickInside && !isClickOnToggle) {
        const button = dropdown.previousElementSibling;
        button.setAttribute('aria-expanded', 'false');
        dropdown.classList.add('hidden');
      }
    }
  });
});
