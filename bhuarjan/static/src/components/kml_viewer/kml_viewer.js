/** @odoo-module **/
/* version: v5-google-maps */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useEffect, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

// REPLACE THIS WITH YOUR ACTUAL GOOGLE MAPS API KEY
const GOOGLE_MAPS_API_KEY = "YOUR_API_KEY_HERE";

export class KmlViewer extends Component {
    static template = "bhuarjan.KmlViewer";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.state = useState({
            isLoading: true,
            error: null,
            status: "Starting v5...",
        });

        onMounted(async () => {
            console.log("KML Viewer v5: Mounted");
            try {
                this.state.status = "Loading libraries...";
                await this.loadDependencies();
                console.log("KML Viewer v5: Libraries loaded");
                this.state.status = "Initializing map...";

                // Poll until google maps is ready
                let tries = 0;
                const checkGoogle = setInterval(() => {
                    tries++;
                    if (window.google && window.google.maps) {
                        clearInterval(checkGoogle);
                        this.initializeMap();
                        this.renderKml();
                        this.state.isLoading = false;
                    } else if (tries > 50) {
                        clearInterval(checkGoogle);
                        this.state.error = "Google Maps failed to load. Check API key.";
                        this.state.isLoading = false;
                    }
                }, 200);
            } catch (e) {
                console.error("KML Viewer v5 error:", e);
                this.state.error = "Setup error: " + e.message;
                this.state.status = "Failed.";
                this.state.isLoading = false;
            }
        });

        onWillUnmount(() => {
            this.map = null;
        });

        useEffect(() => {
            if (!this.state.isLoading && this.map) {
                this.renderKml();
            }
        }, () => [this.props.record.data[this.props.name]]);
    }

    async loadDependencies() {
        // JSZip for KMZ extraction
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js");
        // toGeoJSON for KML -> GeoJSON conversion (no Omnivore needed)
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/togeojson/0.16.0/togeojson.min.js");
        // Google Maps JS API
        if (!window.google || !window.google.maps) {
            await loadJS(`https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}`);
        }
    }

    initializeMap() {
        const el = this.mapContainer.el;
        if (!el) {
            console.error("KML Viewer v5: map container not found");
            return;
        }
        console.log("KML Viewer v5: Creating Google Map...");
        this.map = new google.maps.Map(el, {
            center: { lat: 23.5937, lng: 80.9629 }, // Center of India
            zoom: 5,
            mapTypeId: "terrain",
        });
    }

    // Helper: convert a base64 string to Uint8Array correctly
    base64ToUint8Array(base64) {
        const cleaned = base64.replace(/\s/g, "");
        const binaryStr = atob(cleaned);
        const len = binaryStr.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryStr.charCodeAt(i);
        }
        return bytes;
    }

    async renderKml() {
        if (!this.map || !window.google) return;

        const kmlData = this.props.record.data[this.props.name];

        // Remove previous features
        this.map.data.forEach((f) => this.map.data.remove(f));

        if (!kmlData) {
            this.state.status = "No file uploaded.";
            return;
        }

        this.state.error = null;
        this.state.status = "Processing...";

        try {
            // Decode base64 to bytes
            let bytes;
            try {
                bytes = this.base64ToUint8Array(kmlData);
            } catch (e) {
                throw new Error("Could not decode file data (Base64 error): " + e.message);
            }

            let kmlString = "";

            // Detect ZIP signature: bytes 0x50 0x4B
            const isZip = bytes[0] === 0x50 && bytes[1] === 0x4B;

            if (isZip) {
                this.state.status = "Extracting KMZ...";
                if (!window.JSZip) throw new Error("JSZip not loaded.");
                const zip = new JSZip();
                const loaded = await zip.loadAsync(bytes);
                const kmlEntries = Object.keys(loaded.files).filter(n =>
                    n.toLowerCase().endsWith(".kml")
                );
                const entry = kmlEntries.find(n => n.toLowerCase() === "doc.kml") || kmlEntries[0];
                if (!entry) throw new Error("No .kml file found inside KMZ.");
                kmlString = await loaded.file(entry).async("string");
            } else {
                this.state.status = "Reading KML...";
                // Decode UTF-8 bytes
                const decoder = new TextDecoder("utf-8");
                kmlString = decoder.decode(bytes);
            }

            if (!kmlString.trim()) {
                throw new Error("KML content is empty.");
            }

            this.state.status = "Parsing KML...";
            const parser = new DOMParser();
            const kmlDom = parser.parseFromString(kmlString, "text/xml");

            const parseError = kmlDom.querySelector("parsererror");
            if (parseError) {
                throw new Error("XML parse error: " + parseError.textContent.substring(0, 100));
            }

            // Convert to GeoJSON
            if (!window.toGeoJSON) throw new Error("toGeoJSON library not loaded.");
            const geoJson = toGeoJSON.kml(kmlDom);

            this.state.status = "Rendering...";
            this.map.data.addGeoJson(geoJson);

            // Fit map to features
            const bounds = new google.maps.LatLngBounds();
            let featureCount = 0;

            const extendBounds = (geometry) => {
                const type = geometry.getType();
                if (type === "Point") {
                    bounds.extend(geometry.get());
                    featureCount++;
                } else if (type === "LineString" || type === "LinearRing") {
                    geometry.getArray().forEach(p => { bounds.extend(p); featureCount++; });
                } else if (type === "Polygon") {
                    geometry.getArray().forEach(ring =>
                        ring.getArray().forEach(p => { bounds.extend(p); featureCount++; })
                    );
                } else if (["MultiPoint", "MultiLineString", "MultiPolygon", "GeometryCollection"].includes(type)) {
                    geometry.getArray().forEach(extendBounds);
                }
            };

            this.map.data.forEach(f => extendBounds(f.getGeometry()));

            if (featureCount > 0 && !bounds.isEmpty()) {
                this.map.fitBounds(bounds);
            }

            // Default styling
            this.map.data.setStyle({
                fillColor: "#3388ff",
                fillOpacity: 0.4,
                strokeColor: "#3388ff",
                strokeWeight: 2,
            });

            this.state.status = `✓ Rendered ${featureCount} coordinate(s).`;
            console.log("KML Viewer v5: Rendered successfully, features:", featureCount);

        } catch (e) {
            console.error("KML Viewer v5 render error:", e);
            this.state.error = e.message;
            this.state.status = "Error.";
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
