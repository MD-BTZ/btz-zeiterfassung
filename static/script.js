document.addEventListener('DOMContentLoaded', function() {
    let breakTimer = null;
    let breakStartTime = null;
    let currentBreakDuration = 0;
    let breakSettings = null;
    
    // Initialize break settings if the elements exist
    const autoBreakDetection = document.getElementById('auto-break-detection');
    const autoBreakThreshold = document.getElementById('auto-break-threshold');
    const excludeBreaks = document.getElementById('exclude-breaks');
    const arbzgBreaksEnabled = document.getElementById('arbzg-breaks-enabled');
    
    if (autoBreakDetection && autoBreakThreshold && excludeBreaks) {
        // Load user settings via AJAX
        fetch('/get_user_settings')
            .then(response => response.json())
            .then(settings => {
                breakSettings = settings;
                autoBreakDetection.checked = settings.auto_break_detection;
                autoBreakThreshold.value = settings.auto_break_threshold;
                excludeBreaks.checked = settings.exclude_breaks;
                if (arbzgBreaksEnabled) {
                    arbzgBreaksEnabled.checked = settings.arbzg_breaks_enabled;
                }
                
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
    } else {
        // If we're not on the settings page, still load settings for break tracking
        fetch('/get_user_settings')
            .then(response => response.json())
            .then(settings => {
                breakSettings = settings;
                initializeBreakTracker();
            })
            .catch(error => {
                console.error('Error loading break settings:', error);
            });
    }
    
    // Toggle break settings container functionality removed - now using direct link instead
    // Local settings container functionality preserved for pages that might use it
    const settingsContainer = document.getElementById('break-settings-container');
    if (settingsContainer) {
        // Add toggle button for local container
        const containerParent = settingsContainer.parentNode;
        const toggleButton = document.createElement('button');
        toggleButton.textContent = 'Pauseneinstellungen anzeigen';
        toggleButton.className = 'btn btn-primary';
        toggleButton.style.marginBottom = '10px';
        
        toggleButton.addEventListener('click', function() {
            if (settingsContainer.style.display === 'none' || settingsContainer.style.display === '') {
                settingsContainer.style.display = 'block';
                toggleButton.textContent = 'Pauseneinstellungen ausblenden';
            } else {
                settingsContainer.style.display = 'none';
                toggleButton.textContent = 'Pauseneinstellungen anzeigen';
            }
        });
        
        // Insert toggle button before the container
        containerParent.insertBefore(toggleButton, settingsContainer);
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
            
            // Get additional fields
            const breakType = document.getElementById('break-type-select')?.value || 'regular';
            const breakDescription = document.getElementById('break-description')?.value || '';
            
            // Create form data for submission
            const formData = new FormData();
            formData.append('attendance_id', attendanceId);
            formData.append('start_time', startDateTime);
            formData.append('end_time', endDateTime);
            formData.append('is_excluded', isExcluded ? '1' : '0');
            formData.append('is_auto', '0');  // This is a manual entry
            formData.append('break_type', breakType);
            formData.append('description', breakDescription);
            
            // Send break data to server
            fetch('/add_break', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Clear form fields after successful submission
                document.getElementById('break-start').value = '';
                document.getElementById('break-end').value = '';
                document.getElementById('break-type-select').value = 'regular';
                document.getElementById('break-description').value = '';
                document.getElementById('break-excluded').checked = true;
                
                // Update breaks list to show the new break
                updateBreaksList(attendanceId);
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
    
    // Break tracker functions
    function initializeBreakTracker() {
        const userId = sessionStorage.getItem('user_id');
        if (!userId) return;
        
        // Create break tracker UI if not exists
        createBreakTrackerUI();
        
        // Check if user is currently checked in
        fetch(`/get_today_attendance/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.attendance && data.attendance.id && !data.attendance.check_out) {
                    // User is checked in, enable break tracking
                    const attendanceId = data.attendance.id;
                    sessionStorage.setItem('current_attendance_id', attendanceId);
                    
                    // Show the break tracker
                    const breakTracker = document.getElementById('break-tracker');
                    if (breakTracker) {
                        breakTracker.style.display = 'block';
                        updateBreaksList(attendanceId);
                    }
                }
            })
            .catch(error => {
                console.error('Error checking attendance for break tracking:', error);
            });
    }
    
    function createBreakTrackerUI() {
        // Use the existing break-tracker div if present
        let breakTracker = document.getElementById('break-tracker');
        if (!breakTracker) {
            // Fallback: create if not present (should not happen)
            const container = document.querySelector('.container');
            if (!container) return;
            breakTracker = document.createElement('div');
            breakTracker.id = 'break-tracker';
            breakTracker.className = 'break-tracker';
            breakTracker.style.display = 'none';
            // Insert after attendance forms if possible
            const attendanceForms = document.getElementById('attendance-forms');
            if (attendanceForms) {
                attendanceForms.parentNode.insertBefore(breakTracker, attendanceForms.nextSibling);
            } else {
                container.appendChild(breakTracker);
            }
        }
        breakTracker.className = 'break-tracker';
        breakTracker.style.display = 'none';
        breakTracker.innerHTML = `
            <h3>Pausenverwaltung</h3>
            <div class="break-actions">
                <button id="start-break" class="break-btn">Pause starten</button>
                <button id="end-break" class="break-btn" disabled>Pause beenden</button>
                <div class="break-timer" id="break-timer">00:00:00</div>
            </div>
            <div class="break-type-selection" id="break-type-selection" style="display: none;">
                <h4>Pausentyp:</h4>
                <select id="break-type">
                    <option value="lunch">Mittagspause</option>
                    <option value="coffee">Kaffeepause</option>
                    <option value="personal">Persönliche Zeit</option>
                    <option value="meeting">Besprechung</option>
                    <option value="other">Sonstiges</option>
                </select>
                <label class="checkbox-label">
                    <input type="checkbox" id="current-break-excluded" checked>
                    <span>Nicht abrechenbar</span>
                </label>
                <input type="text" id="break-description" placeholder="Beschreibung (optional)">
            </div>
            <div class="break-history" id="break-history">
                <h4>Heutige Pausen:</h4>
                <div id="breaks-list" class="breaks-list">
                    <p>Keine Pausen für heute.</p>
                </div>
                <div class="break-summary" id="break-summary">
                    Gesamtpausen: <span id="total-break-time">00:00</span>
                </div>
            </div>
        `;
        // Add event listeners for break buttons
        document.getElementById('start-break').addEventListener('click', startBreak);
        document.getElementById('end-break').addEventListener('click', endBreak);
        document.getElementById('break-type').addEventListener('change', function() {
            const isPersonal = this.value === 'personal' || this.value === 'coffee';
            document.getElementById('current-break-excluded').checked = isPersonal;
        });
        
        // Add styles for break tracker
        const styleElement = document.createElement('style');
        styleElement.textContent = `
            .break-tracker {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 5px;
                padding: 15px;
                margin-top: 20px;
            }
            .break-actions {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }
            .break-btn {
                padding: 8px 15px;
                margin-right: 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            #start-break {
                background-color: #28a745;
                color: white;
            }
            #start-break:hover {
                background-color: #218838;
            }
            #start-break:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
            #end-break {
                background-color: #dc3545;
                color: white;
            }
            #end-break:hover {
                background-color: #c82333;
            }
            #end-break:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
            .break-timer {
                font-size: 1.5em;
                font-weight: bold;
                margin-left: auto;
                color: #343a40;
            }
            .break-type-selection {
                margin-bottom: 15px;
                padding: 10px;
                background-color: #e9ecef;
                border-radius: 4px;
            }
            .break-type-selection select,
            .break-type-selection input[type="text"] {
                padding: 5px;
                margin-right: 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
            }
            .breaks-list {
                max-height: 200px;
                overflow-y: auto;
                margin-bottom: 10px;
            }
            .break-item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
            }
            .break-item:last-child {
                border-bottom: none;
            }
            .break-summary {
                font-weight: bold;
                text-align: right;
                border-top: 1px solid #dee2e6;
                padding-top: 10px;
            }
        `;
        document.head.appendChild(styleElement);
    }
    
    function startBreak() {
        breakStartTime = new Date();
        currentBreakDuration = 0;
        
        // Show break type selection
        document.getElementById('break-type-selection').style.display = 'block';
        
        // Disable start button, enable end button
        document.getElementById('start-break').disabled = true;
        document.getElementById('end-break').disabled = false;
        
        // Start timer
        breakTimer = setInterval(updateBreakTimer, 1000);
    }
    
    function updateBreakTimer() {
        if (!breakStartTime) return;
        
        const now = new Date();
        currentBreakDuration = Math.floor((now - breakStartTime) / 1000);
        
        // Format time as HH:MM:SS
        const hours = Math.floor(currentBreakDuration / 3600);
        const minutes = Math.floor((currentBreakDuration % 3600) / 60);
        const seconds = currentBreakDuration % 60;
        
        const formattedTime = 
            `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        document.getElementById('break-timer').textContent = formattedTime;
    }
    
    function endBreak() {
        if (!breakStartTime) return;
        
        clearInterval(breakTimer);
        const endTime = new Date();
        
        // Get current attendance ID
        const attendanceId = sessionStorage.getItem('current_attendance_id');
        if (!attendanceId) {
            alert('Keine aktive Anwesenheit gefunden. Die Pause kann nicht gespeichert werden.');
            resetBreakUI();
            return;
        }
        
        // Get break details
        const breakType = document.getElementById('break-type').value;
        const isExcluded = document.getElementById('current-break-excluded').checked;
        const description = document.getElementById('break-description').value || 
            document.getElementById('break-type').options[document.getElementById('break-type').selectedIndex].text;
        
        // Format times for server
        const startDateTime = breakStartTime.toISOString().substring(0, 10) + ' ' + 
            breakStartTime.toTimeString().substring(0, 8);
        const endDateTime = endTime.toISOString().substring(0, 10) + ' ' + 
            endTime.toTimeString().substring(0, 8);
        
        // Create form data for submission
        const formData = new FormData();
        formData.append('attendance_id', attendanceId);
        formData.append('start_time', startDateTime);
        formData.append('end_time', endDateTime);
        formData.append('is_excluded', isExcluded ? '1' : '0');
        formData.append('is_auto', '0');  // This is a manual entry
        formData.append('description', description);
        formData.append('break_type', breakType);
        
        // Send break data to server
        fetch('/add_break', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reset UI
                resetBreakUI();
                
                // Update breaks list
                updateBreaksList(attendanceId);
            } else {
                alert('Fehler beim Hinzufügen der Pause: ' + (data.message || 'Unbekannter Fehler'));
                resetBreakUI();
            }
        })
        .catch(error => {
            console.error('Error adding break:', error);
            alert('Fehler beim Hinzufügen der Pause. Bitte versuchen Sie es später erneut.');
            resetBreakUI();
        });
    }
    
    function resetBreakUI() {
        // Reset timer and UI elements
        clearInterval(breakTimer);
        breakStartTime = null;
        currentBreakDuration = 0;
        document.getElementById('break-timer').textContent = '00:00:00';
        document.getElementById('break-type-selection').style.display = 'none';
        document.getElementById('start-break').disabled = false;
        document.getElementById('end-break').disabled = true;
        document.getElementById('break-description').value = '';
    }
    
    function updateBreaksList(attendanceId) {
        if (!attendanceId) return;
        
        fetch(`/get_breaks/${attendanceId}`)
            .then(response => response.json())
            .then(data => {
                const breaksList = document.getElementById('breaks-list');
                if (!breaksList) return;
                
                if (!data.breaks || data.breaks.length === 0) {
                    breaksList.innerHTML = '<p>Keine Pausen für heute.</p>';
                    document.getElementById('total-break-time').textContent = '00:00';
                    return;
                }
                
                // Sort breaks by start time (newest first)
                data.breaks.sort((a, b) => {
                    return new Date(b.start_time) - new Date(a.start_time);
                });
                
                let totalBreakMinutes = 0;
                let html = '';
                
                data.breaks.forEach(breakItem => {
                    const startTime = new Date(breakItem.start_time);
                    const endTime = new Date(breakItem.end_time);
                    
                    const formattedStart = startTime.toTimeString().substring(0, 5);
                    const formattedEnd = endTime.toTimeString().substring(0, 5);
                    
                    // Determine break type and select appropriate styling
                    let breakTypeLabel = 'Manuell';
                    let breakTypeClass = '';
                    let breakIcon = '';
                    
                    if (breakItem.is_auto) {
                        if (breakItem.description && breakItem.description.includes('ArbZG')) {
                            if (breakItem.description.includes('Mittagspause')) {
                                breakTypeLabel = 'ArbZG Mittagspause';
                                breakTypeClass = 'arbzg-badge lunch-badge';
                                breakIcon = '<i class="fas fa-utensils" style="margin-right: 5px;"></i>';
                            } else {
                                breakTypeLabel = 'ArbZG Pause';
                                breakTypeClass = 'arbzg-badge';
                                breakIcon = '<i class="fas fa-clock" style="margin-right: 5px;"></i>';
                            }
                        } else {
                            breakTypeLabel = 'Automatische Pause';
                            breakTypeClass = 'auto-detected-badge';
                            breakIcon = '<i class="fas fa-robot" style="margin-right: 5px;"></i>';
                        }
                    } else {
                        if (breakItem.description && breakItem.description.includes('ArbZG')) {
                            breakTypeClass = 'manual-arbzg-badge';
                            breakTypeLabel = 'ArbZG (manuell)';
                            breakIcon = '<i class="fas fa-user-clock" style="margin-right: 5px;"></i>';
                        } else if (breakItem.description && breakItem.description.includes('Mittagspause')) {
                            breakTypeClass = 'lunch-badge';
                            breakTypeLabel = 'Mittagspause';
                            breakIcon = '<i class="fas fa-utensils" style="margin-right: 5px;"></i>';
                        } else {
                            breakTypeClass = 'manual-badge';
                            breakIcon = '<i class="fas fa-user" style="margin-right: 5px;"></i>';
                        }
                    }
                    
                    // Use description if available, otherwise use the determined label
                    const displayText = breakItem.description || breakTypeLabel;
                    
                    html += `<div class="break-item">
                        <div>
                            <strong>${formattedStart} - ${formattedEnd}</strong>
                            <span class="break-type-label ${breakTypeClass}">${breakIcon}${displayText}</span>
                        </div>
                        <div>
                            <span class="break-duration">${breakItem.duration} Min</span>
                            <span class="${breakItem.is_excluded ? 'excluded-badge' : 'included-badge'}">
                                <i class="${breakItem.is_excluded ? 'fas fa-minus-circle' : 'fas fa-check-circle'}" style="margin-right: 3px;"></i>
                                ${breakItem.is_excluded ? 'Nicht abrechenbar' : 'Abrechenbar'}
                            </span>
                        </div>
                    </div>`;
                    
                    totalBreakMinutes += breakItem.duration;
                });
                
                breaksList.innerHTML = html;
                
                // Update total break time
                const hours = Math.floor(totalBreakMinutes / 60);
                const minutes = totalBreakMinutes % 60;
                document.getElementById('total-break-time').textContent = 
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
            })
            .catch(error => {
                console.error('Error loading breaks:', error);
            });
    }
    
    // Initialize break tracker if we're on the main page
    if (document.getElementById('attendance-forms')) {
        initializeBreakTracker();
    }
});
