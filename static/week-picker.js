document.addEventListener('DOMContentLoaded', function() {
    // Check if we have the necessary elements
    const weekPicker = document.getElementById('week-picker');
    const reportWeekInput = document.getElementById('report-week');
    const selectedWeekDisplay = document.getElementById('selected-week-display');
    
    if (weekPicker && reportWeekInput) {
        // Initialize jQuery UI Datepicker for week selection
        $(function() {
            // Configure the datepicker
            $("#week-picker").datepicker({
                showOtherMonths: true,
                selectOtherMonths: true,
                showWeek: true,
                weekHeader: 'KW',
                firstDay: 1, // Monday as first day
                onSelect: function(dateText, inst) {
                    // Get the date object
                    const date = $(this).datepicker('getDate');
                    
                    // Skip if no date is selected
                    if (!date) return;
                    
                    // Get the year
                    const year = date.getFullYear();
                    
                    // Calculate the week number properly (ISO 8601 standard)
                    // Get the day of the week (0-6, where 0 is Sunday)
                    const dayOfWeek = date.getDay();
                    // Thursday in current week decides the year
                    const thursday = new Date(date.getTime() + (3 - ((dayOfWeek + 6) % 7)) * 86400000);
                    // The first Thursday of the year
                    const firstThursday = new Date(thursday.getFullYear(), 0, 1);
                    if (firstThursday.getDay() !== 4) {
                      firstThursday.setMonth(0, 1 + ((4 - firstThursday.getDay()) + 7) % 7);
                    }
                    // Calculate week number: Number of weeks between target Thursday and first Thursday
                    const weekNum = 1 + Math.ceil((thursday - firstThursday) / (7 * 86400000));
                    
                    // Format ISO week string
                    const weekString = year + '-W' + (weekNum < 10 ? '0' + weekNum : weekNum);
                    reportWeekInput.value = weekString;
                    
                    // Format display if element exists
                    if (selectedWeekDisplay) {
                        selectedWeekDisplay.textContent = 'KW ' + weekNum + ', ' + year;
                    }
                    
                    // Clear other inputs (except week)
                    if (typeof clearDateInputs === 'function') {
                        clearDateInputs('week');
                    } else {
                        // Default clearing behavior if function is not defined
                        const dateInput = document.getElementById('report-date');
                        const monthInput = document.getElementById('report-month');
                        if (dateInput) dateInput.value = '';
                        if (monthInput) monthInput.value = '';
                        
                        const reportMonthSelect = document.getElementById('report-month-select');
                        if (reportMonthSelect) reportMonthSelect.selectedIndex = 0;
                        
                        // Uncheck entire period checkbox if it exists
                        const entirePeriodCheckbox = document.getElementById('entire-period');
                        const reportEntirePeriodInput = document.getElementById('report-entire-period');
                        if (entirePeriodCheckbox) entirePeriodCheckbox.checked = false;
                        if (reportEntirePeriodInput) reportEntirePeriodInput.value = '0';
                    }
                    
                    // Create a custom event to notify other scripts that week was changed
                    const weekChangedEvent = new Event('weekPickerChanged');
                    document.dispatchEvent(weekChangedEvent);
                    
                    // Close the datepicker
                    $(this).datepicker('hide');
                },
                beforeShowDay: function(date) {
                    // Check if this date is part of currently selected week
                    const currentValue = reportWeekInput.value;
                    if (currentValue) {
                        const [yearStr, weekStr] = currentValue.split('-W');
                        const year = parseInt(yearStr);
                        const week = parseInt(weekStr);
                        
                        // Calculate the ISO week number of this date
                        const dateYear = date.getFullYear();
                        const firstDayOfYear = new Date(dateYear, 0, 1);
                        const firstThursday = new Date(dateYear, 0, 1 + ((11 - firstDayOfYear.getDay()) % 7));
                        const dayDiff = (date - firstThursday) / 86400000;
                        const dateWeek = Math.floor(dayDiff / 7) + 1;
                        
                        // If this date is in the selected week/year, highlight it
                        if (dateYear === year && dateWeek === week) {
                            return [true, 'ui-week-highlight'];
                        }
                    }
                    return [true, ''];
                },
                
                // Add custom German localization
                monthNames: ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'],
                monthNamesShort: ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'],
                dayNames: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
                dayNamesMin: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
                dayNamesShort: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
            });
        });
    }
});
