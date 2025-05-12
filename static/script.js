document.addEventListener('DOMContentLoaded', function() {
    // Initialize break settings if the elements exist
    const autoBreakDetection = document.getElementById('auto-break-detection');
    const autoBreakThreshold = document.getElementById('auto-break-threshold');
    const excludeBreaks = document.getElementById('exclude-breaks-from-billing');
    
    if (autoBreakDetection && autoBreakThreshold && excludeBreaks) {
        // Load user settings via AJAX
        fetch('/get_user_settings')
            .then(response => response.json())
            .then(settings => {
                autoBreakDetection.checked = settings.auto_break_detection;
                autoBreakThreshold.value = settings.auto_break_threshold;
                excludeBreaks.checked = settings.exclude_breaks;
                
                // Toggle the threshold input based on auto detection setting
                toggleThresholdVisibility();
            })
            .catch(error => {
                console.error('Error loading user settings:', error);
            });
        
        // Toggle threshold input visibility based on checkbox state
        autoBreakDetection.addEventListener('change', toggleThresholdVisibility);
        
        function toggleThresholdVisibility() {
            const thresholdContainer = document.getElementById('threshold-container');
            if (thresholdContainer) {
                thresholdContainer.style.display = autoBreakDetection.checked ? 'block' : 'none';
            }
        }
    }
    
    // Toggle break settings container visibility
    const toggleBreakSettings = document.getElementById('toggle-break-settings');
    if (toggleBreakSettings) {
        toggleBreakSettings.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Check if we're on the break settings page already
            if (window.location.pathname === '/break_settings') {
                return;
            }
            
            // If we're on a different page, check if there's a local container
            const settingsContainer = document.getElementById('break-settings-container');
            if (settingsContainer) {
                // We're on a page with a local settings container
                if (settingsContainer.style.display === 'none' || settingsContainer.style.display === '') {
                    settingsContainer.style.display = 'block';
                    toggleBreakSettings.textContent = 'Pauseneinstellungen ausblenden';
                } else {
                    settingsContainer.style.display = 'none';
                    toggleBreakSettings.textContent = 'Pauseneinstellungen anzeigen';
                }
            } else {
                // No local container, navigate to the break settings page
                window.location.href = '/break_settings';
            }
        });
    }
    
    // Handle manual break entry
    const addBreakForm = document.getElementById('add-break-form');
    const addBreakBtn = document.getElementById('add-break-btn');
    const breakAttendanceId = document.getElementById('break-attendance-id');
    const breakStart = document.getElementById('break-start');
    const breakEnd = document.getElementById('break-end');
    const breakExcluded = document.getElementById('break-excluded');
    
    if (addBreakForm && addBreakBtn) {
        // Find today's active attendance record
        const userId = sessionStorage.getItem('user_id');
        if (userId) {
            // Get today's attendance to enable manual break entry
            fetch(`/get_today_attendance/${userId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.attendance && data.attendance.id) {
                        breakAttendanceId.value = data.attendance.id;
                        document.getElementById('manual-break-entry').style.display = 'block';
                    } else {
                        document.getElementById('manual-break-entry').style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error checking attendance:', error);
                    document.getElementById('manual-break-entry').style.display = 'none';
                });
        }
        
        // Add break button click handler
        addBreakBtn.addEventListener('click', function() {
            const attendanceId = breakAttendanceId.value;
            const startTime = breakStart.value;
            const endTime = breakEnd.value;
            const isExcluded = breakExcluded.checked;
            
            if (!attendanceId) {
                alert('Keine aktive Anwesenheit gefunden. Bitte erst einchecken.');
                return;
            }
            
            if (!startTime || !endTime) {
                alert('Bitte Start- und Endzeit angeben.');
                return;
            }
            
            // Convert time inputs to datetime
            const today = new Date().toISOString().substring(0, 10);
            const startDateTime = `${today} ${startTime}:00`;
            const endDateTime = `${today} ${endTime}:00`;
            
            // Validate end time is after start time
            if (endTime <= startTime) {
                alert('Die Endzeit muss nach der Startzeit liegen.');
                return;
            }
            
            // Create form data for submission
            const formData = new FormData();
            formData.append('attendance_id', attendanceId);
            formData.append('start_time', startDateTime);
            formData.append('end_time', endDateTime);
            formData.append('is_excluded', isExcluded ? '1' : '0');
            formData.append('is_auto', '0');  // This is a manual entry
            
            // Send break data to server
            fetch('/add_break', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Clear form and show success message
                    breakStart.value = '';
                    breakEnd.value = '';
                    breakExcluded.checked = false;
                    alert('Pause wurde erfolgreich hinzugefügt.');
                } else {
                    alert('Fehler beim Hinzufügen der Pause: ' + (data.message || 'Unbekannter Fehler'));
                }
            })
            .catch(error => {
                console.error('Error adding break:', error);
                alert('Fehler beim Hinzufügen der Pause. Bitte versuchen Sie es später erneut.');
            });
        });
    }
});
