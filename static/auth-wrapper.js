// Authentication check wrapper for script.js
// This prevents 401 errors from get_user_settings calls on login page

(function() {
    'use strict';
    
    // Store the original fetch function
    const originalFetch = window.fetch;
    
    // Override fetch to check authentication for user settings
    window.fetch = function(url, options) {
        // If this is a call to get_user_settings and user is not authenticated, skip it silently
        if (url === '/get_user_settings' && !sessionStorage.getItem('user_id')) {
            console.log('Skipping get_user_settings call - user not authenticated');
            // Return a rejected promise that won't log as an error
            return Promise.reject(new Error('Authentication required'));
        }
        
        // Otherwise, use the original fetch
        return originalFetch.apply(this, arguments);
    };
    
    // Override console.error to suppress auth-related errors
    const originalConsoleError = console.error;
    console.error = function(...args) {
        const message = args.join(' ');
        if (message.includes('Error loading break settings') && message.includes('User not authenticated')) {
            // Suppress this specific authentication error
            return;
        }
        originalConsoleError.apply(this, args);
    };
})();
