odoo.define('bhuarjan.survey_auto_gps', ['web.FormController', 'web.core'], function (require) {
    'use strict';

    var FormController = require('web.FormController');
    var core = require('web.core');

    var _t = core._t;

    FormController.include({
        start: function () {
            var result = this._super.apply(this, arguments);
            
            // Only apply auto GPS capture for survey forms
            if (this.modelName === 'bhu.survey') {
                this._autoCaptureGPS();
                this._setupManualGPSButton();
            }
            
            return result;
        },

        _setupManualGPSButton: function () {
            var self = this;
            
            // Wait for the form to be fully loaded
            this.ready().then(function () {
                // Listen for manual GPS capture button clicks
                self.$el.on('click', 'button[name="action_capture_location"]', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    console.log('Manual GPS capture button clicked - preventing server action');
                    // Don't validate form - just capture location
                    self._captureLocation();
                    
                    return false;
                });
                
                console.log('Manual GPS button handler setup complete');
            });
        },

        _autoCaptureGPS: function () {
            var self = this;
            
            // Wait for the form to be fully loaded
            this.ready().then(function () {
                // Check if we're in edit mode and latitude/longitude fields exist
                if (self.mode === 'edit' && self.$('.o_field_float[name="latitude"]').length > 0) {
                    console.log('Auto GPS capture triggered');
                    // Add a small delay to ensure form is fully rendered
                    setTimeout(function() {
                        self._captureLocation();
                    }, 2000);
                } else {
                    console.log('Auto GPS capture skipped - mode:', self.mode, 'fields found:', self.$('.o_field_float[name="latitude"]').length);
                }
            });
        },

        _captureLocation: function () {
            var self = this;
            
            console.log('Starting GPS capture...');
            console.log('Form mode:', self.mode);
            console.log('Model name:', self.modelName);
            console.log('Available fields:', self.$('.o_field_float[name="latitude"]').length, self.$('.o_field_float[name="longitude"]').length);
            
            // Check if geolocation is supported
            if (!navigator.geolocation) {
                console.log('Geolocation is not supported by this browser.');
                self.do_notify(_t('GPS Error'), _t('Geolocation is not supported by this browser.'), 'warning');
                return;
            }

            // Show a subtle notification that GPS is being captured
            this.do_notify(_t('GPS Capture'), _t('Capturing your location automatically...'), 'info');

            // Get current position
            navigator.geolocation.getCurrentPosition(
                function (position) {
                    // Success callback
                    var latitude = position.coords.latitude;
                    var longitude = position.coords.longitude;
                    var accuracy = position.coords.accuracy;
                    var timestamp = new Date(position.timestamp);

                    console.log('GPS coordinates captured:', {
                        latitude: latitude,
                        longitude: longitude,
                        accuracy: accuracy,
                        timestamp: timestamp
                    });

                    // Update the form fields
                    self._updateLocationFields(latitude, longitude, accuracy, timestamp);
                    
                    // Show success notification
                    self.do_notify(_t('Location Captured'), _t('GPS coordinates have been automatically filled.'), 'success');
                },
                function (error) {
                    // Error callback
                    console.error('Error getting location:', error);
                    
                    var errorMessage = '';
                    switch (error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage = _t('Location access denied by user.');
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage = _t('Location information is unavailable.');
                            break;
                        case error.TIMEOUT:
                            errorMessage = _t('Location request timed out.');
                            break;
                        default:
                            errorMessage = _t('An unknown error occurred while retrieving location.');
                            break;
                    }
                    
                    // Show error notification
                    self.do_notify(_t('Location Error'), errorMessage, 'warning');
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        },

        _updateLocationFields: function (latitude, longitude, accuracy, timestamp) {
            var self = this;
            
            console.log('Updating location fields with:', {
                latitude: latitude,
                longitude: longitude,
                accuracy: accuracy,
                timestamp: timestamp
            });
            
            // Try multiple selectors for latitude field
            var $latitudeField = self.$('.o_field_float[name="latitude"] input, input[name="latitude"], .o_field_float input[data-name="latitude"], input[data-field-name="latitude"]');
            if ($latitudeField.length > 0) {
                $latitudeField.val(latitude.toFixed(6));
                $latitudeField.trigger('change');
                $latitudeField.trigger('input');
                $latitudeField.trigger('blur');
                $latitudeField.trigger('keyup');
                console.log('Updated latitude field:', $latitudeField.val());
            } else {
                console.log('Latitude field not found. Available inputs:', self.$('input').map(function() { return $(this).attr('name'); }).get());
            }

            // Try multiple selectors for longitude field
            var $longitudeField = self.$('.o_field_float[name="longitude"] input, input[name="longitude"], .o_field_float input[data-name="longitude"], input[data-field-name="longitude"]');
            if ($longitudeField.length > 0) {
                $longitudeField.val(longitude.toFixed(6));
                $longitudeField.trigger('change');
                $longitudeField.trigger('input');
                $longitudeField.trigger('blur');
                $longitudeField.trigger('keyup');
                console.log('Updated longitude field:', $longitudeField.val());
            } else {
                console.log('Longitude field not found. Available inputs:', self.$('input').map(function() { return $(this).attr('name'); }).get());
            }

            // Update accuracy field if it exists
            var $accuracyField = self.$('.o_field_float[name="location_accuracy"] input, input[name="location_accuracy"]');
            if ($accuracyField.length > 0) {
                $accuracyField.val(accuracy.toFixed(2));
                $accuracyField.trigger('change');
                $accuracyField.trigger('input');
                $accuracyField.trigger('blur');
                console.log('Updated accuracy field:', $accuracyField.val());
            }

            // Update timestamp field if it exists
            var $timestampField = self.$('.o_field_datetime[name="location_timestamp"] input, input[name="location_timestamp"]');
            if ($timestampField.length > 0) {
                var formattedTimestamp = timestamp.toISOString().replace('T', ' ').substring(0, 19);
                $timestampField.val(formattedTimestamp);
                $timestampField.trigger('change');
                $timestampField.trigger('input');
                $timestampField.trigger('blur');
                console.log('Updated timestamp field:', $timestampField.val());
            }

            // Try to update the record directly using Odoo's field system
            try {
                if (self.model && self.handle) {
                    self.model.updateRecord(self.handle, {
                        latitude: latitude,
                        longitude: longitude,
                        location_accuracy: accuracy,
                        location_timestamp: timestamp
                    });
                    console.log('Updated record via model');
                }
            } catch (e) {
                console.log('Could not update via model:', e);
            }

            // Trigger form change to mark as dirty
            try {
                self.trigger('field_changed', {
                    dataPointID: self.handle,
                    changes: {
                        latitude: latitude,
                        longitude: longitude,
                        location_accuracy: accuracy,
                        location_timestamp: timestamp
                    }
                });
                console.log('Triggered field_changed event');
            } catch (e) {
                console.log('Could not trigger field_changed:', e);
            }

            console.log('Location fields update completed');
        }
    });
});
