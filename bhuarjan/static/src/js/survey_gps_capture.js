$(document).ready(function() {
    console.log('GPS Location Capture Script Loaded');
    
    function captureLocation() {
        if (navigator.geolocation) {
            console.log('Starting GPS capture...');
            
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    console.log('GPS captured:', position.coords);
                    
                    var lat = position.coords.latitude.toFixed(8);
                    var lon = position.coords.longitude.toFixed(8);
                    var acc = position.coords.accuracy.toFixed(2);
                    
                    console.log('Trying to update fields with values:', lat, lon, acc);
                    
                    // Try multiple ways to find and update latitude field
                    var latUpdated = false;
                    var $latField = $('input[name="latitude"]');
                    console.log('Latitude field found:', $latField.length);
                    
                    if ($latField.length > 0) {
                        $latField.val(lat).trigger('change').trigger('input');
                        console.log('Latitude updated via name selector');
                        latUpdated = true;
                    } else {
                        // Try alternative selectors
                        $('input').each(function() {
                            var $this = $(this);
                            var name = $this.attr('name');
                            var id = $this.attr('id');
                            if ((name && name.toLowerCase().includes('latitude')) || 
                                (id && id.toLowerCase().includes('latitude'))) {
                                $this.val(lat).trigger('change').trigger('input');
                                console.log('Latitude updated via alternative selector:', name || id);
                                latUpdated = true;
                                return false;
                            }
                        });
                    }
                    
                    // Try multiple ways to find and update longitude field
                    var lonUpdated = false;
                    var $lonField = $('input[name="longitude"]');
                    console.log('Longitude field found:', $lonField.length);
                    
                    if ($lonField.length > 0) {
                        $lonField.val(lon).trigger('change').trigger('input');
                        console.log('Longitude updated via name selector');
                        lonUpdated = true;
                    } else {
                        // Try alternative selectors
                        $('input').each(function() {
                            var $this = $(this);
                            var name = $this.attr('name');
                            var id = $this.attr('id');
                            if ((name && name.toLowerCase().includes('longitude')) || 
                                (id && id.toLowerCase().includes('longitude'))) {
                                $this.val(lon).trigger('change').trigger('input');
                                console.log('Longitude updated via alternative selector:', name || id);
                                lonUpdated = true;
                                return false;
                            }
                        });
                    }
                    
                    // Update accuracy field
                    var $accField = $('input[name="location_accuracy"]');
                    if ($accField.length > 0) {
                        $accField.val(acc).trigger('change').trigger('input');
                        console.log('Accuracy updated');
                    }
                    
                    // Update timestamp
                    var now = new Date();
                    var timestamp = now.getFullYear() + '-' + 
                                  String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                                  String(now.getDate()).padStart(2, '0') + ' ' + 
                                  String(now.getHours()).padStart(2, '0') + ':' + 
                                  String(now.getMinutes()).padStart(2, '0') + ':' + 
                                  String(now.getSeconds()).padStart(2, '0');
                    var $timeField = $('input[name="location_timestamp"]');
                    if ($timeField.length > 0) {
                        $timeField.val(timestamp).trigger('change').trigger('input');
                        console.log('Timestamp updated');
                    }
                    
                    // Show result
                    if (latUpdated && lonUpdated) {
                        alert('Location captured and updated: ' + lat + ', ' + lon);
                        console.log('Both latitude and longitude fields updated successfully');
                    } else {
                        alert('Location captured but fields not found: ' + lat + ', ' + lon);
                        console.log('Location captured but fields not updated - latUpdated:', latUpdated, 'lonUpdated:', lonUpdated);
                    }
                },
                function(error) {
                    console.log('GPS error:', error);
                    alert('Location capture failed: ' + error.message);
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        } else {
            alert('GPS not supported');
        }
    }
    
    // Auto-capture for mobile devices
    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    var isPWA = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
    var isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    
    if (isMobile || isPWA || isTouchDevice) {
        console.log('Auto-capturing location on form load');
        setTimeout(captureLocation, 1000); // Small delay to ensure form is loaded
    }
    
    // Manual capture button
    $('button[name="action_capture_location"]').click(function(e) {
        e.preventDefault();
        console.log('Capture location button clicked');
        
        // Debug: List all input fields
        console.log('=== DEBUGGING ALL INPUT FIELDS ===');
        $('input').each(function() {
            var $this = $(this);
            console.log('Input field:', {
                name: $this.attr('name'),
                id: $this.attr('id'),
                type: $this.attr('type'),
                value: $this.val(),
                visible: $this.is(':visible')
            });
        });
        console.log('=== END DEBUG ===');
        
        captureLocation();
    });
    
    // Capture when survey evidence tab is opened
    $('a[href*="survey_evidence"]').on('click', function() {
        setTimeout(function() {
            var $latField = $('input[name="latitude"]');
            var $lonField = $('input[name="longitude"]');
            
            if ($latField.length && $lonField.length && (!$latField.val() || !$lonField.val())) {
                console.log('Survey evidence tab opened - checking for empty location fields');
                captureLocation();
            }
        }, 500);
    });
    
    console.log('GPS Location Capture Script Initialized');
});
