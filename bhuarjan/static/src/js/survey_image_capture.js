/**
 * Image Capture Script for Survey Forms
 * Handles camera capture and gallery upload for survey images
 */

$(document).ready(function() {
    console.log('Image Capture Script Loading...');
    
    // Image Capture Functions
    function captureImage() {
        console.log('Starting image capture...');
        
        // Check if camera is supported
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.log('Camera not supported');
            if (window.odoo && window.odoo.notification) {
                odoo.notification.add('Camera not supported by this browser', {type: 'warning'});
            } else {
                alert('Camera not supported by this browser');
            }
            return;
        }
        
        // Create modal
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
            justify-content: center;
            align-items: center;
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
        title.textContent = '📷 Capture Survey Photo';
        title.style.cssText = `
            margin: 0 0 20px 0;
            color: #333;
        `;
        
        var video = document.createElement('video');
        video.style.cssText = `
            width: 100%;
            max-width: 500px;
            height: auto;
            border-radius: 5px;
            margin-bottom: 20px;
        `;
        video.autoplay = true;
        video.muted = true;
        video.playsInline = true;
        
        var canvas = document.createElement('canvas');
        var ctx = canvas.getContext('2d');
        
        var buttonContainer = document.createElement('div');
        buttonContainer.style.cssText = `
            display: flex;
            gap: 10px;
            justify-content: center;
        `;
        
        var captureBtn = document.createElement('button');
        captureBtn.textContent = '📷 Capture Photo';
        captureBtn.style.cssText = `
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        `;
        
        var galleryBtn = document.createElement('button');
        galleryBtn.textContent = '📁 Choose from Gallery';
        galleryBtn.style.cssText = `
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
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
        buttonContainer.appendChild(galleryBtn);
        buttonContainer.appendChild(cancelBtn);
        modalContent.appendChild(buttonContainer);
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Start camera - optimized for both mobile and desktop
        var constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ? 'environment' : 'user'
            }
        };
        
        navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
            video.srcObject = stream;
            console.log('Camera started successfully');
            
            // Capture photo when button is clicked
            captureBtn.onclick = function() {
                console.log('Capture button clicked');
                
                // Disable button to prevent multiple clicks
                captureBtn.disabled = true;
                captureBtn.textContent = 'Processing...';
                
                // Set canvas dimensions to match video
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                // Draw video frame to canvas
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // Add timeout to force close modal if it gets stuck
                var forceCloseTimeout = setTimeout(function() {
                    console.log('Force closing modal due to timeout');
                    try {
                        stream.getTracks().forEach(function(track) {
                            track.stop();
                        });
                        if (document.body.contains(modal)) {
                            document.body.removeChild(modal);
                        }
                    } catch (e) {
                        console.log('Error in force close:', e);
                    }
                }, 10000); // 10 second timeout
                
                // Convert canvas to blob
                canvas.toBlob(function(blob) {
                    console.log('Image blob created, size:', blob.size);
                    
                    // Find the survey image field using multiple selectors
                    var fileInput = $('input[name="survey_image"], input[data-field-name="survey_image"], .o_field_binary input, .o_field_image input').filter(function() {
                        return $(this).attr('name') === 'survey_image' || 
                               $(this).attr('data-field-name') === 'survey_image' ||
                               $(this).closest('.o_field_binary, .o_field_image').length > 0;
                    });
                    
                    if (fileInput && fileInput.length > 0) {
                        try {
                            console.log('Found input field:', fileInput[0]);
                            console.log('Input field type:', fileInput[0].type);
                            console.log('Input field name:', fileInput[0].name);
                            
                            // Create a File object from the blob
                            var file = new File([blob], 'survey_image_' + Date.now() + '.jpg', {
                                type: 'image/jpeg',
                                lastModified: Date.now()
                            });
                            
                            console.log('File created:', file.name, file.size, file.type);
                            
                            // Method 1: Try DataTransfer approach
                            try {
                                var dataTransfer = new DataTransfer();
                                dataTransfer.items.add(file);
                                fileInput[0].files = dataTransfer.files;
                                console.log('DataTransfer method applied');
                            } catch (dtError) {
                                console.log('DataTransfer failed:', dtError);
                            }
                            
                            // Method 2: Try direct file assignment
                            try {
                                fileInput[0].files = [file];
                                console.log('Direct file assignment applied');
                            } catch (directError) {
                                console.log('Direct assignment failed:', directError);
                            }
                            
                // Method 3: Try setting value as data URL (DISABLED - causes InvalidStateError)
                // This method is disabled because it causes InvalidStateError when DOM elements become invalid
                // The file assignment methods above should be sufficient for most cases
                console.log('Data URL method skipped to prevent InvalidStateError');
                            
                            // Trigger events
                            fileInput.trigger('change');
                            fileInput.trigger('input');
                            fileInput.trigger('blur');
                            
                            // Force form update
                            if (window.odoo && window.odoo.__WOWL_DEBUG__) {
                                console.log('Triggering Odoo field update');
                                fileInput.trigger('odoo_field_changed');
                            }
                            
                            // Method 4: Try Odoo-specific approach
                            try {
                                // Find the Odoo field widget and update it directly
                                var $fieldWidget = fileInput.closest('.o_field_binary, .o_field_image');
                                if ($fieldWidget.length > 0) {
                                    console.log('Found Odoo field widget');
                                    // Try to trigger the field's change event
                                    $fieldWidget.trigger('change');
                                    $fieldWidget.find('input').trigger('change');
                                }
                            } catch (odooError) {
                                console.log('Odoo field update failed:', odooError);
                            }
                            
                            console.log('Image captured and set to survey_image field');
                            
                            // Close modal immediately
                            try {
                                clearTimeout(forceCloseTimeout);
                                stream.getTracks().forEach(function(track) {
                                    track.stop();
                                });
                                document.body.removeChild(modal);
                                console.log('Modal closed successfully');
                            } catch (closeError) {
                                console.log('Error closing modal:', closeError);
                            }
                            
                            // Verify the assignment worked (without blocking modal close)
                            setTimeout(function() {
                                if (fileInput[0].files && fileInput[0].files.length > 0) {
                                    console.log('File assignment verified:', fileInput[0].files[0].name);
                                    alert('Photo captured and saved successfully!');
                                } else {
                                    console.log('File assignment verification failed');
                                    alert('Photo captured but may not be saved properly. Please try again.');
                                }
                            }, 100);
                            
                        } catch (error) {
                            console.log('Error setting file to input:', error);
                            
                            // Close modal even on error
                            try {
                                clearTimeout(forceCloseTimeout);
                                stream.getTracks().forEach(function(track) {
                                    track.stop();
                                });
                                document.body.removeChild(modal);
                            } catch (closeError) {
                                console.log('Error closing modal on error:', closeError);
                            }
                            
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
                        
                        // Close modal immediately
                        try {
                            clearTimeout(forceCloseTimeout);
                            stream.getTracks().forEach(function(track) {
                                track.stop();
                            });
                            document.body.removeChild(modal);
                            console.log('Modal closed in fallback case');
                        } catch (closeError) {
                            console.log('Error closing modal in fallback:', closeError);
                        }
                    }
                }, 'image/jpeg', 0.8);
            };
            
            // Gallery upload button
            galleryBtn.onclick = function() {
                console.log('Gallery upload clicked');
                
                // Create file input
                var fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.accept = 'image/*';
                fileInput.style.display = 'none';
                
                fileInput.onchange = function(event) {
                    var file = event.target.files[0];
                    if (file) {
                        console.log('File selected:', file.name, file.size, file.type);
                        
                        // Close modal first
                        try {
                            stream.getTracks().forEach(function(track) {
                                track.stop();
                            });
                            document.body.removeChild(modal);
                            console.log('Modal closed for gallery upload');
                        } catch (closeError) {
                            console.log('Error closing modal for gallery:', closeError);
                        }
                        
                        // Assign file to survey image field
                        assignFileToSurveyField(file);
                    }
                };
                
                // Trigger file selection
                document.body.appendChild(fileInput);
                fileInput.click();
                document.body.removeChild(fileInput);
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
                errorMessage += 'Camera permission denied. Please allow camera access and try again.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found. Please connect a camera and try again.';
            } else if (error.name === 'NotReadableError') {
                errorMessage += 'Camera is being used by another application. Please close other camera apps and try again.';
            } else {
                errorMessage += error.message;
            }
            
            console.log(errorMessage);
            if (window.odoo && window.odoo.notification) {
                odoo.notification.add(errorMessage, {type: 'danger'});
            } else {
                alert(errorMessage);
            }
            
            // Remove modal on error
            document.body.removeChild(modal);
        });
    }
    
    // Function to assign file to survey image field
    function assignFileToSurveyField(file) {
        console.log('Assigning file to survey field:', file.name);
        
        // Find the survey image field using multiple selectors
        var fileInput = $('input[name="survey_image"], input[data-field-name="survey_image"], .o_field_binary input, .o_field_image input, input[type="file"]').filter(function() {
            var $this = $(this);
            return $this.attr('name') === 'survey_image' || 
                   $this.attr('data-field-name') === 'survey_image' ||
                   $this.closest('.o_field_binary, .o_field_image').length > 0 ||
                   ($this.attr('type') === 'file' && $this.closest('form').length > 0);
        });
        
        console.log('Found file inputs:', fileInput.length);
        console.log('File input details:', fileInput.map(function() { 
            return {
                name: $(this).attr('name'),
                type: $(this).attr('type'),
                id: $(this).attr('id'),
                class: $(this).attr('class')
            };
        }).get());
        
        if (fileInput && fileInput.length > 0) {
            try {
                console.log('Found input field:', fileInput[0]);
                console.log('Input field type:', fileInput[0].type);
                console.log('Input field name:', fileInput[0].name);
                
                // Method 1: Try DataTransfer approach
                try {
                    if (typeof DataTransfer !== 'undefined') {
                        var dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        fileInput[0].files = dataTransfer.files;
                        console.log('DataTransfer method applied');
                    } else {
                        console.log('DataTransfer not supported, trying direct assignment');
                    }
                } catch (dtError) {
                    console.log('DataTransfer failed:', dtError);
                }
                
                // Method 2: Try direct file assignment
                try {
                    fileInput[0].files = [file];
                    console.log('Direct file assignment applied');
                } catch (directError) {
                    console.log('Direct assignment failed:', directError);
                }
                
                // Method 2.5: Try setting files property with FileList
                try {
                    var fileList = {
                        0: file,
                        length: 1,
                        item: function(index) { return index === 0 ? file : null; }
                    };
                    fileInput[0].files = fileList;
                    console.log('FileList assignment applied');
                } catch (fileListError) {
                    console.log('FileList assignment failed:', fileListError);
                }
                
                // Method 3: Try setting value as data URL (DISABLED - causes InvalidStateError)
                // This method is disabled because it causes InvalidStateError when DOM elements become invalid
                // The file assignment methods above should be sufficient for most cases
                console.log('Data URL method skipped to prevent InvalidStateError');
                
                // Trigger events with error handling and multiple approaches
                try {
                    // Native DOM events
                    var changeEvent = new Event('change', { bubbles: true, cancelable: true });
                    fileInput[0].dispatchEvent(changeEvent);
                    console.log('Native change event dispatched');
                } catch (e) {
                    console.log('Error dispatching native change event:', e);
                }
                
                try {
                    // jQuery events
                    fileInput.trigger('change');
                    console.log('jQuery change event triggered');
                } catch (e) {
                    console.log('Error triggering jQuery change event:', e);
                }
                
                try {
                    // Input event
                    var inputEvent = new Event('input', { bubbles: true, cancelable: true });
                    fileInput[0].dispatchEvent(inputEvent);
                    fileInput.trigger('input');
                    console.log('Input events triggered');
                } catch (e) {
                    console.log('Error triggering input events:', e);
                }
                
                try {
                    // Blur event
                    fileInput.trigger('blur');
                    console.log('Blur event triggered');
                } catch (e) {
                    console.log('Error triggering blur event:', e);
                }
                
                // Additional events for Odoo
                try {
                    fileInput.trigger('focus');
                    fileInput.trigger('keyup');
                    fileInput.trigger('keydown');
                    console.log('Additional Odoo events triggered');
                } catch (e) {
                    console.log('Error triggering additional events:', e);
                }
                
                // Force form update with error handling
                if (window.odoo && window.odoo.__WOWL_DEBUG__) {
                    console.log('Triggering Odoo field update');
                    try {
                        fileInput.trigger('odoo_field_changed');
                    } catch (e) {
                        console.log('Error triggering Odoo field update:', e);
                    }
                }
                
                // Method 4: Try Odoo-specific approach
                try {
                    // Find the Odoo field widget and update it directly
                    var $fieldWidget = fileInput.closest('.o_field_binary, .o_field_image, .o_field_widget');
                    if ($fieldWidget.length > 0) {
                        console.log('Found Odoo field widget');
                        // Try to trigger the field's change event
                        $fieldWidget.trigger('change');
                        $fieldWidget.find('input').trigger('change');
                        
                        // Try to find and update the field value directly
                        var $hiddenInput = $fieldWidget.find('input[type="hidden"]');
                        if ($hiddenInput.length > 0) {
                            console.log('Found hidden input, updating value');
                            $hiddenInput.val('uploaded');
                        }
                        
                        // Try to find and update any display elements
                        var $displayElement = $fieldWidget.find('.o_field_binary_file, .o_field_image_file');
                        if ($displayElement.length > 0) {
                            console.log('Found display element, updating');
                            $displayElement.text('File uploaded: ' + file.name);
                        }
                    }
                    
                    // Try to find the parent form and trigger its change event
                    var $form = fileInput.closest('form');
                    if ($form.length > 0) {
                        console.log('Found parent form, triggering change');
                        $form.trigger('change');
                    }
                } catch (odooError) {
                    console.log('Odoo field update failed:', odooError);
                }
                
                // Method 5: Try replacing the input element entirely
                try {
                    console.log('Attempting input replacement method');
                    var newInput = fileInput[0].cloneNode(true);
                    newInput.files = [file];
                    fileInput[0].parentNode.replaceChild(newInput, fileInput[0]);
                    console.log('Input replacement method applied');
                } catch (replaceError) {
                    console.log('Input replacement failed:', replaceError);
                }
                
                console.log('File assigned to survey_image field');
                
                // Verify the assignment worked
                setTimeout(function() {
                    var currentInput = $('input[name="survey_image"], input[data-field-name="survey_image"]').first();
                    if (currentInput.length > 0 && currentInput[0].files && currentInput[0].files.length > 0) {
                        console.log('File assignment verified:', currentInput[0].files[0].name);
                        alert('Photo uploaded and saved successfully!');
                    } else {
                        console.log('File assignment verification failed');
                        console.log('Current input files:', currentInput[0] ? currentInput[0].files : 'No input found');
                        alert('Photo uploaded but may not be saved properly. Please try again.');
                    }
                }, 1000);
                
            } catch (error) {
                console.log('Error setting file to input:', error);
                alert('Photo uploaded but could not save to form: ' + error.message);
            }
        } else {
            console.log('Survey image field not found with any selector');
            console.log('Available inputs:', $('input').map(function() { return $(this).attr('name'); }).get());
            
            // Try to save the image as a data URL to localStorage as fallback (without FileReader)
            try {
                // Use canvas to convert blob to data URL without FileReader
                var canvas = document.createElement('canvas');
                var ctx = canvas.getContext('2d');
                var img = new Image();
                
                img.onload = function() {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    var dataURL = canvas.toDataURL('image/jpeg', 0.8);
                    localStorage.setItem('captured_survey_image', dataURL);
                    localStorage.setItem('captured_survey_image_timestamp', Date.now());
                    console.log('Image saved to localStorage as fallback');
                    alert('Photo uploaded! Please refresh the page to see the image.');
                };
                
                img.onerror = function() {
                    console.log('Failed to load image for localStorage fallback');
                    alert('Photo uploaded but could not save to form - field not found');
                };
                
                // Create object URL for the image
                var objectURL = URL.createObjectURL(file);
                img.src = objectURL;
                
                // Clean up object URL after use
                setTimeout(function() {
                    URL.revokeObjectURL(objectURL);
                }, 1000);
                
            } catch (fallbackError) {
                console.log('Fallback save also failed:', fallbackError);
                alert('Photo uploaded but could not save to form - field not found');
            }
        }
    }
    
    function addImageButtons() {
        console.log('Attempting to add image buttons...');
        
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
            // Remove existing buttons if any
            $imageSection.find('.camera-capture-btn, .gallery-upload-btn').remove();
            
            // Create camera button with improved styling
            var cameraBtn = $('<button type="button" class="camera-capture-btn btn btn-primary" style="margin: 10px 0; padding: 12px 20px; width: 100%; background: linear-gradient(135deg, #007bff, #0056b3); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 4px 8px rgba(0,123,255,0.3); transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 8px;">📷 Capture Photo with Camera</button>');
            
            // Create gallery upload button with improved styling
            var galleryBtn = $('<button type="button" class="gallery-upload-btn btn btn-success" style="margin: 10px 0; padding: 12px 20px; width: 100%; background: linear-gradient(135deg, #28a745, #1e7e34); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 4px 8px rgba(40,167,69,0.3); transition: all 0.3s ease; display: flex; align-items: center; justify-content: center; gap: 8px;">📁 Choose from Gallery</button>');
            
            // Add hover effects
            cameraBtn.on('mouseenter', function() {
                $(this).css('transform', 'translateY(-2px)');
                $(this).css('box-shadow', '0 6px 12px rgba(0,123,255,0.4)');
            }).on('mouseleave', function() {
                $(this).css('transform', 'translateY(0)');
                $(this).css('box-shadow', '0 4px 8px rgba(0,123,255,0.3)');
            });
            
            galleryBtn.on('mouseenter', function() {
                $(this).css('transform', 'translateY(-2px)');
                $(this).css('box-shadow', '0 6px 12px rgba(40,167,69,0.4)');
            }).on('mouseleave', function() {
                $(this).css('transform', 'translateY(0)');
                $(this).css('box-shadow', '0 4px 8px rgba(40,167,69,0.3)');
            });
            
            cameraBtn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Camera button clicked');
                captureImage();
            });
            
            galleryBtn.on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Gallery upload button clicked');
                
                // Create file input
                var fileInput = $('<input type="file" accept="image/*" style="display: none;">');
                
                fileInput.on('change', function(event) {
                    var file = event.target.files[0];
                    if (file) {
                        console.log('File selected from gallery:', file.name, file.size, file.type);
                        assignFileToSurveyField(file);
                    }
                });
                
                // Trigger file selection
                $('body').append(fileInput);
                fileInput[0].click();
                fileInput.remove();
            });
            
            $imageSection.append(cameraBtn);
            $imageSection.append(galleryBtn);
            console.log('Image buttons added successfully');
            return true;
        } else {
            console.log('Could not find image section, trying alternative approach...');
            
            // Try to add buttons to the page body as floating buttons
            if ($('.floating-camera-btn').length === 0) {
                var floatingCameraBtn = $('<button type="button" class="floating-camera-btn" style="position: fixed; top: 20px; right: 20px; z-index: 9999; background: linear-gradient(135deg, #007bff, #0056b3); color: white; border: none; padding: 15px; border-radius: 50px; cursor: pointer; font-size: 18px; box-shadow: 0 4px 12px rgba(0,123,255,0.4); transition: all 0.3s ease; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center;" title="Capture Photo with Camera">📷</button>');
                
                var floatingGalleryBtn = $('<button type="button" class="floating-gallery-btn" style="position: fixed; top: 90px; right: 20px; z-index: 9999; background: linear-gradient(135deg, #28a745, #1e7e34); color: white; border: none; padding: 15px; border-radius: 50px; cursor: pointer; font-size: 18px; box-shadow: 0 4px 12px rgba(40,167,69,0.4); transition: all 0.3s ease; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center;" title="Choose from Gallery">📁</button>');
                
                // Add hover effects to floating buttons
                floatingCameraBtn.on('mouseenter', function() {
                    $(this).css('transform', 'scale(1.1)');
                    $(this).css('box-shadow', '0 6px 16px rgba(0,123,255,0.5)');
                }).on('mouseleave', function() {
                    $(this).css('transform', 'scale(1)');
                    $(this).css('box-shadow', '0 4px 12px rgba(0,123,255,0.4)');
                });
                
                floatingGalleryBtn.on('mouseenter', function() {
                    $(this).css('transform', 'scale(1.1)');
                    $(this).css('box-shadow', '0 6px 16px rgba(40,167,69,0.5)');
                }).on('mouseleave', function() {
                    $(this).css('transform', 'scale(1)');
                    $(this).css('box-shadow', '0 4px 12px rgba(40,167,69,0.4)');
                });
                
                floatingCameraBtn.on('click', function(e) {
                    e.preventDefault();
                    console.log('Floating camera button clicked');
                    captureImage();
                });
                
                floatingGalleryBtn.on('click', function(e) {
                    e.preventDefault();
                    console.log('Floating gallery button clicked');
                    
                    // Create file input
                    var fileInput = $('<input type="file" accept="image/*" style="display: none;">');
                    
                    fileInput.on('change', function(event) {
                        var file = event.target.files[0];
                        if (file) {
                            console.log('File selected from floating gallery:', file.name, file.size, file.type);
                            assignFileToSurveyField(file);
                        }
                    });
                    
                    // Trigger file selection
                    $('body').append(fileInput);
                    fileInput[0].click();
                    fileInput.remove();
                });
                
                $('body').append(floatingCameraBtn);
                $('body').append(floatingGalleryBtn);
                console.log('Floating image buttons added');
                return true;
            }
        }
        return false;
    }
    
    // Try to add image buttons multiple times with different delays
    setTimeout(addImageButtons, 1000);
    setTimeout(addImageButtons, 3000);
    setTimeout(addImageButtons, 5000);
    
    // Also try when tab is clicked
    $('a[href*="survey_evidence"]').on('click', function() {
        setTimeout(addImageButtons, 1000);
    });
    
    console.log('Image Capture Script Initialized');
});
