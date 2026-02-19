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
            console.log("KML Viewer: Mounting...");
            try {
                this.state.isLoading = true;
                await this.loadDependencies();
                console.log("KML Viewer: Dependencies loaded.");

                // Slight delay to ensure DOM is ready
                setTimeout(() => {
                    this.initializeMap();
                    this.renderKml();
                    this.state.isLoading = false;
                }, 100);
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
                    if (this.map) this.map.invalidateSize();
                }, 200);
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
            throw new Error("Failed to load map libraries (Leaflet/JSZip). Check internet connection.");
        }
    }

    initializeMap() {
        if (!this.mapContainer.el) {
            console.error("Map container element not found!");
            return;
        }
        if (this.map) return;

        console.log("KML Viewer: Initializing map...");
        // Default view (India)
        this.map = L.map(this.mapContainer.el).setView([20.5937, 78.9629], 5);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);

        // Force resize
        setTimeout(() => {
            if (this.map) this.map.invalidateSize();
        }, 500);
    }

    async renderKml() {
        if (!this.map || !window.omnivore || !window.JSZip) {
            this.state.status = "Missing dependencies for render.";
            return;
        }

        const kmlData = this.props.record.data[this.props.name];
        // Filename check removed to rely on content parsing

        if (this.layer) {
            this.map.removeLayer(this.layer);
            this.layer = null;
        }

        if (kmlData) {
            this.state.status = "Decoding data...";
            console.log("KML Viewer: Rendering data...");
            try {
                // Clean base64 string (remove newlines/spaces)
                const cleanKmlData = kmlData.replace(/\s/g, '');

                // Decode Base64 to binary string
                let binaryString;
                try {
                    binaryString = atob(cleanKmlData);
                } catch (e) {
                    console.error("Base64 decode error:", e);
                    throw new Error("Invalid Base64 data.");
                }

                let kmlString = "";
                let isKmz = false;

                // Simple check for ZIP signature (PK)
                if (binaryString.startsWith("PK")) {
                    isKmz = true;
                }

                if (isKmz) {
                    this.state.status = "Processing KMZ Archive...";
                    // Check if JSZip is loaded
                    if (typeof JSZip === 'undefined') {
                        throw new Error("JSZip library not loaded.");
                    }

                    const zip = new JSZip();
                    // Load zip from binary string
                    const loadedZip = await zip.loadAsync(binaryString);

                    // Find the .kml file inside
                    const kmlFiles = Object.keys(loadedZip.files).filter(filename => filename.toLowerCase().endsWith('.kml'));

                    let kmlFile = null;
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
                    this.state.status = "Processing KML Content...";
                    // KML Text Handling with standard decoding
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

                if (!kmlString) {
                    this.state.status = "Empty content.";
                    return;
                }

                this.state.status = "Parsing geometry...";
                // Parse using omnivore
                const layer = omnivore.kml.parse(kmlString);

                layer.addTo(this.map);
                this.layer = layer;

                const adjustBounds = () => {
                    if (layer.getBounds().isValid()) {
                        this.map.fitBounds(layer.getBounds());
                        this.state.status = "Rendered successfully.";
                    } else {
                        this.state.status = "Map loaded (No bounds found).";
                    }
                };

                layer.on('ready', adjustBounds);
                // Also try immediately
                adjustBounds();

            } catch (e) {
                console.error("Error parsing KML/KMZ data", e);
                this.state.error = "Error parsing file: " + e.message;
                this.state.status = "Failed to parse.";
            }
        } else {
            this.state.status = "No data uploaded.";
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
