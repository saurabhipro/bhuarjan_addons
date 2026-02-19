/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useEffect, useState } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

export class KmlViewer extends Component {
    static template = "bhuarjan.KmlViewer";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.layer = null;
        this.state = useState({
            isLoading: true,
            error: null,
        });

        onMounted(async () => {
            try {
                await this.loadDependencies();
                this.initializeMap();
                await this.renderKml();
                this.state.isLoading = false;
            } catch (e) {
                console.error("Setup error:", e);
                this.state.error = "Error initializing map: " + e.message;
                this.state.isLoading = false;
            }
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
                this.map = null;
            }
        });

        useEffect(() => {
            if (!this.state.isLoading && this.map) {
                this.renderKml();
                // Ensure map invalidates size when data changes or component updates
                setTimeout(() => {
                    this.map.invalidateSize();
                }, 100);
            }
        }, () => [this.props.record.data[this.props.name]]);
    }

    async loadDependencies() {
        try {
            await loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
            await loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
            // Omnivore for KML parsing
            await loadJS("https://api.tiles.mapbox.com/mapbox.js/plugins/leaflet-omnivore/v0.3.1/leaflet-omnivore.min.js");
            // JSZip for KMZ extraction
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js");
        } catch (e) {
            console.error("Failed to load map dependencies", e);
            throw e;
        }
    }

    initializeMap() {
        if (!this.mapContainer.el || this.map) return;

        // Default view (India)
        this.map = L.map(this.mapContainer.el).setView([20.5937, 78.9629], 5);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Fix for map not rendering correctly initially
        setTimeout(() => {
            if (this.map) this.map.invalidateSize();
        }, 500);
    }

    async renderKml() {
        if (!this.map || !window.omnivore || !window.JSZip) return;

        const kmlData = this.props.record.data[this.props.name];

        if (this.layer) {
            this.map.removeLayer(this.layer);
            this.layer = null;
        }

        if (kmlData) {
            try {
                // Determine file type from filename or try to detect
                // Since we only hold data, let's try KML first, then KMZ if zip signature or if filename ends in .kmz
                // We don't have filename in props reliably unless we fetch it from another field
                // But generally users upload .kmz or .kml

                // Decode Base64 to binary string
                const binaryString = atob(kmlData);

                let kmlString = "";
                let isKmz = false;

                // Simple check for ZIP signature (PK)
                if (binaryString.startsWith("PK")) {
                    isKmz = true;
                }

                if (isKmz) {
                    // Check if JSZip is loaded
                    if (typeof JSZip === 'undefined') {
                        throw new Error("JSZip library not loaded.");
                    }

                    const zip = new JSZip();
                    // Load zip from binary string
                    const loadedZip = await zip.loadAsync(binaryString);

                    // Find the .kml file inside
                    // KMZ usually contains a doc.kml at root, but can be any .kml
                    let kmlFile = null;

                    // Search for .kml files
                    const kmlFiles = Object.keys(loadedZip.files).filter(filename => filename.toLowerCase().endsWith('.kml'));

                    if (kmlFiles.length > 0) {
                        // Prioritize doc.kml if exists, else take first
                        kmlFile = kmlFiles.find(name => name.toLowerCase() === 'doc.kml') || kmlFiles[0];
                    }

                    if (kmlFile) {
                        kmlString = await loadedZip.file(kmlFile).async("string");
                    } else {
                        throw new Error("No KML file found inside KMZ archive.");
                    }
                } else {
                    // Assume KML text
                    // Decode properly for utf-8 characters if needed
                    // atob handles base64 to binary string (latin1), we need to decode to utf-8 text
                    try {
                        const uint8Array = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            uint8Array[i] = binaryString.charCodeAt(i);
                        }
                        const decoder = new TextDecoder('utf-8');
                        kmlString = decoder.decode(uint8Array);
                    } catch (e) {
                        // Fallback
                        kmlString = binaryString;
                    }
                }

                if (!kmlString) return;

                // Parse using omnivore
                const layer = omnivore.kml.parse(kmlString);

                layer.addTo(this.map);
                this.layer = layer;

                // Wait for layer to be ready to get bounds
                layer.on('ready', () => {
                    if (layer.getBounds().isValid()) {
                        this.map.fitBounds(layer.getBounds());
                    }
                });

                // Also handle immediate bounds if already parsed synchronously (sometimes omnivore is sync for strings)
                if (layer.getBounds().isValid()) {
                    this.map.fitBounds(layer.getBounds());
                }

            } catch (e) {
                console.error("Error parsing KML/KMZ data", e);
                this.state.error = "Error parsing file: " + e.message;
            }
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
