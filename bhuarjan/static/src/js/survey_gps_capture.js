/**
 * GPS Location Capture Script for Survey Forms
 * Handles automatic and manual GPS location capture
 */

$(document).ready(function() {
    console.log('GPS Location Capture Script Loading...');
    
    // GPS Capture Functions
    function captureLocation() {
        console.log('Starting GPS capture...');
        
        if (!navigator.geolocation) {
            console.log('Geolocation not supported');
            if (window.odoo && window.odoo.notification) {
                odoo.notification.add('Geolocation not supported by this browser', {type: 'warning'});
            } else {
                alert('Geolocation not supported by this browser');
            }
            return;
        }
        
        var options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        };
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                console.log('GPS coordinates captured:', position.coords);
                
                var latitude = position.coords.latitude;
                var longitude = position.coords.longitude;
                var accuracy = position.coords.accuracy;
                var timestamp = new Date(position.timestamp);
                
                console.log('Latitude:', latitude);
                console.log('Longitude:', longitude);
                console.log('Accuracy:', accuracy, 'meters');
                console.log('Timestamp:', timestamp);
                
                // Update form fields
                updateLocationFields(latitude, longitude, accuracy, timestamp);
                
                // Show success notification
                if (window.odoo && window.odoo.notification) {
                    odoo.notification.add('Location captured successfully!', {type: 'success'});
                } else {
                    alert('Location captured successfully!');
                }
            },
            function(error) {
                console.log('GPS capture error:', error);
                var errorMessage = 'Location capture failed: ';
                
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage += 'Permission denied. Please allow location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage += 'Location information unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMessage += 'Location request timed out.';
                        break;
                    default:
                        errorMessage += 'Unknown error occurred.';
                        break;
                }
                
                console.log(errorMessage);
                if (window.odoo && window.odoo.notification) {
                    odoo.notification.add(errorMessage, {type: 'danger'});
                } else {
                    alert(errorMessage);
                }
            },
            options
        );
    }
    
    function updateLocationFields(latitude, longitude, accuracy, timestamp) {
        console.log('Updating location fields...');
        
        // Find and update latitude field
        var latField = $('input[name="latitude"], input[data-field-name="latitude"]');
        if (latField.length > 0) {
            latField.val(latitude);
            latField.trigger('input');
            latField.trigger('change');
            console.log('Latitude field updated:', latitude);
        } else {
            console.log('Latitude field not found');
        }
        
        // Find and update longitude field
        var lngField = $('input[name="longitude"], input[data-field-name="longitude"]');
        if (lngField.length > 0) {
            lngField.val(longitude);
            lngField.trigger('input');
            lngField.trigger('change');
            console.log('Longitude field updated:', longitude);
        } else {
            console.log('Longitude field not found');
        }
        
        // Find and update accuracy field
        var accField = $('input[name="location_accuracy"], input[data-field-name="location_accuracy"]');
        if (accField.length > 0) {
            accField.val(accuracy);
            accField.trigger('input');
            accField.trigger('change');
            console.log('Accuracy field updated:', accuracy);
        } else {
            console.log('Accuracy field not found');
        }
        
        // Find and update timestamp field
        var timeField = $('input[name="location_timestamp"], input[data-field-name="location_timestamp"]');
        if (timeField.length > 0) {
            timeField.val(timestamp.toISOString());
            timeField.trigger('input');
            timeField.trigger('change');
            console.log('Timestamp field updated:', timestamp.toISOString());
        } else {
            console.log('Timestamp field not found');
        }
    }
    
    function addGPSButton() {
        console.log('Attempting to add GPS button...');
        
        // Try multiple selectors to find the location section
        var $locationSection = null;
        var selectors = [
            'input[name="latitude"]',
            'input[name="longitude"]',
            '.o_field_float[name="latitude"]',
            '.o_field_float[name="longitude"]'
        ];
        
        for (var i = 0; i < selectors.length; i++) {
            var $test = $(selectors[i]);
            if ($test.length > 0) {
                $locationSection = $test.closest('div, td, tr, fieldset');
                console.log('Found location section with selector:', selectors[i], $locationSection.length);
                break;
            }
        }
        
        if ($locationSection && $locationSection.length > 0) {
            // Remove existing button if any
            $locationSection.find('.gps-capture-btn').remove();
            
            // Create GPS button with improved styling
            var gpsBtn = $('<button type="button" class="gps-capture-btn btn btn-info" style="margin: 10px 0; padding: 12px 20px; width: 100%; background: linear-gradient(135deg, #17a2b8, #138496); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 4px 8px rgba(23,162,184,0.3); transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 8px;">📍 Capture GPS Location</button>');
            
            // Add hover effects
            gpsBtn.on('mouseenter', function() {
                $(this).css('transform', 'translateY(-2px)');
                $(this).css('box-shadow', '0 6px 12px rgba(23,162,184,0.4)');
            }).on('mouseleave', function() {
                $(this).css('transform', 'translateY(0)');
                $(this).css('box-shadow', '0 4px 8px rgba(23,162,184,0.3)');
            });
            
            gpsBtn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('GPS button clicked');
                captureLocation();
            });
            
            $locationSection.append(gpsBtn);
            console.log('GPS button added successfully');
            return true;
        } else {
            console.log('Could not find location section, trying alternative approach...');
            
            // Try to add button to the page body as a floating button
            if ($('.floating-gps-btn').length === 0) {
                var floatingBtn = $('<button type="button" class="floating-gps-btn" style="position: fixed; top: 160px; right: 20px; z-index: 9999; background: linear-gradient(135deg, #17a2b8, #138496); color: white; border: none; padding: 15px; border-radius: 50px; cursor: pointer; font-size: 18px; box-shadow: 0 4px 12px rgba(23,162,184,0.4); transition: all 0.3s ease; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center;" title="Capture GPS Location">📍</button>');
                
                // Add hover effects to floating GPS button
                floatingBtn.on('mouseenter', function() {
                    $(this).css('transform', 'scale(1.1)');
                    $(this).css('box-shadow', '0 6px 16px rgba(23,162,184,0.5)');
                }).on('mouseleave', function() {
                    $(this).css('transform', 'scale(1)');
                    $(this).css('box-shadow', '0 4px 12px rgba(23,162,184,0.4)');
                });
                
                floatingBtn.on('click', function(e) {
                    e.preventDefault();
                    console.log('Floating GPS button clicked');
                    captureLocation();
                });
                
                $('body').append(floatingBtn);
                console.log('Floating GPS button added');
                return true;
            }
        }
        return false;
    }
    
    // Try to add GPS button multiple times with different delays
    setTimeout(addGPSButton, 1000);
    setTimeout(addGPSButton, 3000);
    setTimeout(addGPSButton, 5000);
    
    // Also try when tab is clicked
    $('a[href*="survey_details"]').on('click', function() {
        setTimeout(addGPSButton, 1000);
    });
    
    console.log('GPS Location Capture Script Initialized');
});