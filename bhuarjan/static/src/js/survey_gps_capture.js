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
    
    // No auto-capture - only manual capture via button
    console.log('GPS capture available - click "Capture Location" button to capture coordinates');
    
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
    
    // No auto-capture on tab change - only manual capture via button
    
    // Camera capture functionality
    function captureImage() {
        console.log('Starting camera capture...');
        console.log('Browser info:', {
            userAgent: navigator.userAgent,
            hasMediaDevices: !!navigator.mediaDevices,
            hasGetUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            isSecureContext: window.isSecureContext
        });
        
        // Check if camera is supported
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            // Create a video element for camera preview
            var video = document.createElement('video');
            video.style.width = '100%';
            video.style.maxWidth = '400px';
            video.style.height = 'auto';
            video.setAttribute('autoplay', '');
            video.setAttribute('muted', '');
            
            // Create a canvas element for capturing the image
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            
            // Create modal for camera preview
            var modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                z-index: 10000;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            `;
            
            var modalContent = document.createElement('div');
            modalContent.style.cssText = `
                background: white;
                padding: 20px;
                border-radius: 10px;
                max-width: 90%;
                max-height: 90%;
                text-align: center;
            `;
            
            var title = document.createElement('h3');
            title.textContent = 'Camera Capture';
            title.style.marginBottom = '20px';
            
            var buttonContainer = document.createElement('div');
            buttonContainer.style.cssText = `
                margin-top: 20px;
                display: flex;
                gap: 10px;
                justify-content: center;
            `;
            
            var captureBtn = document.createElement('button');
            captureBtn.textContent = 'Capture Photo';
            captureBtn.style.cssText = `
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            `;
            
            var cancelBtn = document.createElement('button');
            cancelBtn.textContent = 'Cancel';
            cancelBtn.style.cssText = `
                background: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            `;
            
            // Assemble modal
            modalContent.appendChild(title);
            modalContent.appendChild(video);
            buttonContainer.appendChild(captureBtn);
            buttonContainer.appendChild(cancelBtn);
            modalContent.appendChild(buttonContainer);
            modal.appendChild(modalContent);
            document.body.appendChild(modal);
            
            // Start camera - optimized for both mobile and desktop
            var constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            // Try to use back camera on mobile, front camera on desktop
            if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
                constraints.video.facingMode = 'environment'; // Back camera on mobile
            } else {
                constraints.video.facingMode = 'user'; // Front camera on desktop
            }
            
            console.log('Camera constraints:', constraints);
            
            navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
                video.srcObject = stream;
                console.log('Camera started successfully');
                
                // Capture photo when button is clicked
                captureBtn.onclick = function() {
                    // Set canvas dimensions to match video
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    
                    // Draw video frame to canvas
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    // Convert canvas to blob
                    canvas.toBlob(function(blob) {
                        console.log('Image blob created, size:', blob.size);
                        
                        // Try multiple ways to find the survey_image field
                        var fileInput = null;
                        var selectors = [
                            'input[name="survey_image"]',
                            'input[data-field-name="survey_image"]',
                            '.o_field_image input',
                            'input[type="file"]'
                        ];
                        
                        for (var i = 0; i < selectors.length; i++) {
                            var $test = $(selectors[i]);
                            if ($test.length > 0) {
                                fileInput = $test;
                                console.log('Found survey_image field with selector:', selectors[i]);
                                break;
                            }
                        }
                        
                        if (fileInput && fileInput.length > 0) {
                            try {
                                // Create a File object from the blob
                                var file = new File([blob], 'survey_image_' + Date.now() + '.jpg', {
                                    type: 'image/jpeg',
                                    lastModified: Date.now()
                                });
                                
                                console.log('File created:', file.name, file.size, file.type);
                                
                                // Create a FileList-like object
                                var dataTransfer = new DataTransfer();
                                dataTransfer.items.add(file);
                                
                                // Set the file to the input
                                fileInput[0].files = dataTransfer.files;
                                fileInput.trigger('change');
                                fileInput.trigger('input');
                                
                                console.log('Image captured and set to survey_image field');
                                alert('Photo captured successfully!');
                            } catch (error) {
                                console.log('Error setting file to input:', error);
                                alert('Photo captured but could not save to form: ' + error.message);
                            }
                        } else {
                            console.log('Survey image field not found with any selector');
                            console.log('Available inputs:', $('input').map(function() { return $(this).attr('name'); }).get());
                            
                            // Try to save the image as a data URL to localStorage as fallback
                            try {
                                var dataURL = canvas.toDataURL('image/jpeg', 0.8);
                                localStorage.setItem('captured_survey_image', dataURL);
                                localStorage.setItem('captured_survey_image_timestamp', Date.now());
                                console.log('Image saved to localStorage as fallback');
                                alert('Photo captured! Please refresh the page to see the image.');
                            } catch (fallbackError) {
                                console.log('Fallback save also failed:', fallbackError);
                                alert('Photo captured but could not save to form - field not found');
                            }
                        }
                        
                        // Stop camera and close modal
                        stream.getTracks().forEach(function(track) {
                            track.stop();
                        });
                        document.body.removeChild(modal);
                    }, 'image/jpeg', 0.8);
                };
                
                // Cancel button
                cancelBtn.onclick = function() {
                    stream.getTracks().forEach(function(track) {
                        track.stop();
                    });
                    document.body.removeChild(modal);
                };
                
            }).catch(function(error) {
                console.log('Camera error:', error);
                console.log('Error details:', {
                    name: error.name,
                    message: error.message,
                    constraint: error.constraint
                });
                
                var errorMessage = 'Camera access failed: ';
                if (error.name === 'NotAllowedError') {
                    errorMessage += 'Camera access denied. Please allow camera access and try again.';
                } else if (error.name === 'NotFoundError') {
                    errorMessage += 'No camera found. Please connect a camera and try again.';
                } else if (error.name === 'NotReadableError') {
                    errorMessage += 'Camera is being used by another application. Please close other camera apps and try again.';
                } else if (error.name === 'OverconstrainedError') {
                    errorMessage += 'Camera constraints cannot be satisfied. Trying with basic settings...';
                    // Try with basic constraints
                    navigator.mediaDevices.getUserMedia({ video: true }).then(function(stream) {
                        video.srcObject = stream;
                        console.log('Camera started with basic constraints');
                    }).catch(function(basicError) {
                        console.log('Basic camera also failed:', basicError);
                        alert('Camera not available: ' + basicError.message);
                        document.body.removeChild(modal);
                    });
                    return;
                } else {
                    errorMessage += error.message;
                }
                
                alert(errorMessage);
                document.body.removeChild(modal);
            });
            
        } else {
            alert('Camera not supported on this device');
        }
    }
    
    // Add camera capture to image field click - multiple selectors
    $(document).on('click', function(e) {
        var target = $(e.target);
        var isImageField = false;
        
        // Check if clicked on survey image field or related elements
        if (target.is('input[name="survey_image"]') || 
            target.closest('input[name="survey_image"]').length > 0 ||
            target.is('.oe_avatar') || 
            target.closest('.oe_avatar').length > 0 ||
            target.is('.o_field_image') ||
            target.closest('.o_field_image').length > 0 ||
            target.is('[data-field-name="survey_image"]') ||
            target.closest('[data-field-name="survey_image"]').length > 0) {
            
            isImageField = true;
            console.log('Survey image area clicked - opening camera');
            e.preventDefault();
            e.stopPropagation();
            captureImage();
        }
    });
    
    // Also try to add click handler directly to the image field
    setTimeout(function() {
        var $imageField = $('input[name="survey_image"]');
        var $avatar = $('.oe_avatar');
        var $fieldImage = $('.o_field_image');
        
        console.log('Image field elements found:', {
            input: $imageField.length,
            avatar: $avatar.length,
            fieldImage: $fieldImage.length
        });
        
        // Add click handlers to all possible elements
        $imageField.on('click', function(e) {
            console.log('Direct input click - opening camera');
            e.preventDefault();
            captureImage();
        });
        
        $avatar.on('click', function(e) {
            console.log('Avatar click - opening camera');
            e.preventDefault();
            captureImage();
        });
        
        $fieldImage.on('click', function(e) {
            console.log('Field image click - opening camera');
            e.preventDefault();
            captureImage();
        });
    }, 1000);
    
    // Add a manual camera button for testing - more aggressive approach
    function addCameraButton() {
        console.log('Attempting to add camera button...');
        
        // Try multiple selectors to find the image section
        var $imageSection = null;
        var selectors = [
            '.oe_avatar',
            '[name="survey_image"]',
            '.o_field_image',
            '.oe_avatar + div'
        ];
        
        for (var i = 0; i < selectors.length; i++) {
            var $test = $(selectors[i]);
            if ($test.length > 0) {
                $imageSection = $test.closest('div, td, tr');
                console.log('Found image section with selector:', selectors[i], $imageSection.length);
                break;
            }
        }
        
        if ($imageSection && $imageSection.length > 0) {
            // Remove existing button if any
            $imageSection.find('.camera-capture-btn').remove();
            
            // Create camera button with better styling
            var cameraBtn = $('<button type="button" class="camera-capture-btn btn btn-primary" style="margin: 10px 0; padding: 10px; width: 100%; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold;">📷 Capture Photo with Camera</button>');
            
            cameraBtn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Manual camera button clicked');
                captureImage();
            });
            
            $imageSection.append(cameraBtn);
            console.log('Camera button added successfully');
            return true;
        } else {
            console.log('Could not find image section, trying alternative approach...');
            
            // Try to add button to the page body as a floating button
            if ($('.floating-camera-btn').length === 0) {
                var floatingBtn = $('<button type="button" class="floating-camera-btn" style="position: fixed; top: 20px; right: 20px; z-index: 9999; background: #007bff; color: white; border: none; padding: 15px; border-radius: 50px; cursor: pointer; font-size: 16px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">📷</button>');
                
                floatingBtn.on('click', function(e) {
                    e.preventDefault();
                    console.log('Floating camera button clicked');
                    captureImage();
                });
                
                $('body').append(floatingBtn);
                console.log('Floating camera button added');
                return true;
            }
        }
        return false;
    }
    
    // Try to add camera button multiple times with different delays
    setTimeout(addCameraButton, 1000);
    setTimeout(addCameraButton, 3000);
    setTimeout(addCameraButton, 5000);
    
    // Also try when tab is clicked
    $('a[href*="survey_evidence"]').on('click', function() {
        setTimeout(addCameraButton, 1000);
    });
    
    console.log('GPS Location Capture Script Initialized');
});
