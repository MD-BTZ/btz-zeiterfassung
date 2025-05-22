/**
 * Improved Check-in/Check-out functionality for BTZ Zeiterfassung
 */
document.addEventListener('DOMContentLoaded', function() {
    const userSelector = document.getElementById('user-selector');
    const checkinUserIdField = document.getElementById('checkin-user-id');
    const checkoutUserIdField = document.getElementById('checkout-user-id');
    const checkinBtn = document.getElementById('checkin-btn');
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkinCard = document.querySelector('.attendance-button-card.checkin');
    const checkoutCard = document.querySelector('.attendance-button-card.checkout');
    const checkinStatus = document.getElementById('checkin-status');
    const checkoutStatus = document.getElementById('checkout-status');
    
    // Initialize user ID for forms
    function updateUserIds() {
        const selectedUserId = userSelector.value;
        if (selectedUserId) {
            checkinUserIdField.value = selectedUserId;
            checkoutUserIdField.value = selectedUserId;
            checkinBtn.disabled = false;
            checkoutBtn.disabled = false;
            
            // Check attendance status for the selected user
            checkAttendanceStatus(selectedUserId);
        } else {
            checkinBtn.disabled = true;
            checkoutBtn.disabled = true;
            updateStatusDisplay(false, false);
        }
    }
    
    // Update visual status indicators
    function updateStatusDisplay(isCheckedIn, isCheckedOut) {
        if (isCheckedIn) {
            checkinCard.classList.add('active');
            checkinStatus.innerHTML = '<i class="fas fa-check-circle"></i> Eingestempelt';
            checkinStatus.classList.add('status-active');
        } else {
            checkinCard.classList.remove('active');
            checkinStatus.innerHTML = 'Nicht eingestempelt';
            checkinStatus.classList.remove('status-active');
        }
        
        if (isCheckedOut) {
            checkoutCard.classList.add('active');
            checkoutStatus.innerHTML = '<i class="fas fa-check-circle"></i> Ausgestempelt';
            checkoutStatus.classList.add('status-active');
        } else {
            checkoutCard.classList.remove('active');
            checkoutStatus.innerHTML = 'Nicht ausgestempelt';
            checkoutStatus.classList.remove('status-active');
        }
    }
    
    // Check the user's attendance status
    function checkAttendanceStatus(userId) {
        // Simple fetch to an API endpoint that returns attendance status
        fetch('/get_attendance_status?user_id=' + userId)
            .then(response => response.json())
            .then(data => {
                updateStatusDisplay(data.is_checked_in, data.is_checked_out);
            })
            .catch(error => {
                console.error('Error checking attendance status:', error);
                // Default to both inactive if we can't get the status
                updateStatusDisplay(false, false);
            });
    }
    
    // Add button press effect
    function addButtonPressEffect(button) {
        button.addEventListener('mousedown', function() {
            this.style.transform = 'scale(0.97)';
        });
        
        button.addEventListener('mouseup', function() {
            this.style.transform = '';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    }
    
    // For admin dropdown, listen for changes
    if (userSelector.tagName === 'SELECT') {
        userSelector.addEventListener('change', updateUserIds);
    }
    
    // Add press effect to buttons
    if (checkinBtn) addButtonPressEffect(checkinBtn);
    if (checkoutBtn) addButtonPressEffect(checkoutBtn);
    
    // Initial setup
    updateUserIds();
    
    // Handle form submission
    const checkinForm = checkinBtn.closest('form');
    const checkoutForm = checkoutBtn.closest('form');
    
    if (checkinForm) {
        checkinForm.addEventListener('submit', function(event) {
            // You could add validation here if needed
            checkinBtn.classList.add('submitting');
            // Let the form submit normally
        });
    }
    
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function(event) {
            // You could add validation here if needed
            checkoutBtn.classList.add('submitting');
            // Let the form submit normally
        });
    }
});
