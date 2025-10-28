/** @odoo-module **/

import { registry } from "@odoo/web";
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

// Patch FormController to add red asterisk styling
patch(FormController.prototype, {
    setup() {
        super.setup();
        this._addMandatoryFieldStyling();
    },

    _addMandatoryFieldStyling() {
        // Add CSS class to the form view
        const formElement = document.querySelector('.o_form_view');
        if (formElement) {
            formElement.classList.add('bhuarjan_form');
        }

        // Style mandatory field labels
        this._styleMandatoryFields();
    },

    _styleMandatoryFields() {
        // Find all field labels that contain asterisk
        const labels = document.querySelectorAll('.o_field_label');
        labels.forEach(label => {
            if (label.textContent.includes('*')) {
                label.style.color = '#dc3545';
                label.style.fontWeight = 'bold';
            }
        });

        // Also style labels with required modifier
        const requiredLabels = document.querySelectorAll('.o_required_modifier .o_field_label');
        requiredLabels.forEach(label => {
            label.style.color = '#dc3545';
            label.style.fontWeight = 'bold';
            
            // Add red asterisk if not already present
            if (!label.textContent.includes('*')) {
                label.innerHTML += ' <span style="color: #dc3545; font-weight: bold;">*</span>';
            }
        });
    },

    async onRecordSaved() {
        await super.onRecordSaved();
        // Re-apply styling after record save
        setTimeout(() => this._styleMandatoryFields(), 100);
    },

    async onRecordChanged() {
        await super.onRecordChanged();
        // Re-apply styling after record change
        setTimeout(() => this._styleMandatoryFields(), 100);
    }
});

// Also patch the form renderer to ensure styling is applied
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this._applyMandatoryFieldStyling();
    },

    _applyMandatoryFieldStyling() {
        // Use MutationObserver to watch for DOM changes
        const observer = new MutationObserver(() => {
            this._styleMandatoryFields();
        });

        // Start observing
        const formElement = document.querySelector('.o_form_view');
        if (formElement) {
            observer.observe(formElement, {
                childList: true,
                subtree: true,
                characterData: true
            });
        }
    },

    _styleMandatoryFields() {
        // Find all field labels that contain asterisk
        const labels = document.querySelectorAll('.o_field_label');
        labels.forEach(label => {
            if (label.textContent.includes('*')) {
                label.style.color = '#dc3545';
                label.style.fontWeight = 'bold';
            }
        });

        // Style required field labels
        const requiredLabels = document.querySelectorAll('.o_required_modifier .o_field_label');
        requiredLabels.forEach(label => {
            label.style.color = '#dc3545';
            label.style.fontWeight = 'bold';
            
            // Add red asterisk if not already present
            if (!label.textContent.includes('*')) {
                const asterisk = document.createElement('span');
                asterisk.textContent = ' *';
                asterisk.style.color = '#dc3545';
                asterisk.style.fontWeight = 'bold';
                label.appendChild(asterisk);
            }
        });
    }
});
