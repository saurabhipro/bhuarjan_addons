/** @odoo-module **/
/* version: v6-leaflet-builtin-parser */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useEffect, useState } from "@odoo/owl";
import { loadJS, loadCSS } from "@web/core/assets";

export class KmlViewer extends Component {
    static template = "bhuarjan.KmlViewer";
    static props = { ...standardFieldProps };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.layers = [];
        this.state = useState({
            isLoading: true,
            error: null,
            status: "V6: Starting...",
        });

        onMounted(async () => {
            console.log("KML Viewer V6: Mounted");
            try {
                this.state.status = "Loading Leaflet...";
                await loadCSS("https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css");
                await loadJS("https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js");
                await loadJS("https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js");
                console.log("KML Viewer V6: Libraries loaded");

                this.state.status = "Initializing map...";
                // Small delay to ensure DOM is ready
                await new Promise(r => setTimeout(r, 150));

                this.initMap();
                await this.renderKml();
                this.state.isLoading = false;
                console.log("KML Viewer V6: Done mounting");
            } catch (e) {
                console.error("KML Viewer V6 error:", e);
                this.state.error = "Error: " + e.message;
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
            }
        }, () => [this.props.record.data[this.props.name]]);
    }

    initMap() {
        const el = this.mapContainer.el;
        if (!el || this.map) return;
        console.log("KML Viewer V6: Creating Leaflet map on", el);

        this.map = L.map(el, { preferCanvas: true }).setView([22.5937, 80.9629], 5);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
            maxZoom: 19,
        }).addTo(this.map);

        // Force size calculation after creation
        setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 300);
    }

    // Robust base64 decode — handles standard, URL-safe, and missing-padding variants
    decodeBase64ToBytes(b64) {
        // Remove whitespace, convert URL-safe chars, fix padding
        let s = b64.replace(/[\s\r\n]+/g, "")
            .replace(/-/g, "+")
            .replace(/_/g, "/");
        const mod = s.length % 4;
        if (mod === 2) s += "==";
        else if (mod === 3) s += "=";

        const bin = atob(s);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        return bytes;
    }

    // Parse latitude/longitude pairs from a KML coordinates string
    parseCoords(coordStr) {
        return coordStr.trim().split(/\s+/).map(triplet => {
            const parts = triplet.split(",");
            const lng = parseFloat(parts[0]);
            const lat = parseFloat(parts[1]);
            if (!isNaN(lat) && !isNaN(lng)) return [lat, lng];
            return null;
        }).filter(Boolean);
    }

    // Recursively extract Leaflet layers from a KML DOM element
    parsePlacemarks(el, layers, bounds) {
        // Points
        el.querySelectorAll("Point > coordinates").forEach(c => {
            const coords = this.parseCoords(c.textContent);
            if (coords.length > 0) {
                const marker = L.marker(coords[0]);
                const name = c.closest("Placemark")?.querySelector("name")?.textContent || "";
                if (name) marker.bindPopup(name);
                layers.push(marker);
                bounds.extend(coords[0]);
            }
        });

        // LineStrings
        el.querySelectorAll("LineString > coordinates").forEach(c => {
            const coords = this.parseCoords(c.textContent);
            if (coords.length > 1) {
                const line = L.polyline(coords, { color: "#3388ff", weight: 3 });
                layers.push(line);
                coords.forEach(pt => bounds.extend(pt));
            }
        });

        // Polygons (outer boundary only)
        el.querySelectorAll("Polygon").forEach(poly => {
            const outerCoordEl = poly.querySelector("outerBoundaryIs > LinearRing > coordinates");
            if (outerCoordEl) {
                const outerCoords = this.parseCoords(outerCoordEl.textContent);
                if (outerCoords.length > 2) {
                    const polygon = L.polygon(outerCoords, {
                        color: "#3388ff",
                        fillColor: "#3388ff",
                        fillOpacity: 0.3,
                        weight: 2,
                    });
                    layers.push(polygon);
                    outerCoords.forEach(pt => bounds.extend(pt));
                }
            }
        });
    }

    async renderKml() {
        if (!this.map) return;

        // Clear previous layers
        this.layers.forEach(l => this.map.removeLayer(l));
        this.layers = [];

        const kmlData = this.props.record.data[this.props.name];
        if (!kmlData) {
            this.state.status = "No file uploaded.";
            return;
        }

        this.state.error = null;
        this.state.status = "Decoding...";

        try {
            let bytes;
            try {
                bytes = this.decodeBase64ToBytes(kmlData);
            } catch (e) {
                throw new Error("Base64 decode failed: " + e.message);
            }

            let kmlString = "";

            // Detect ZIP  (PK = 0x50 0x4B)
            if (bytes[0] === 0x50 && bytes[1] === 0x4B) {
                this.state.status = "Extracting KMZ...";
                if (!window.JSZip) throw new Error("JSZip not loaded.");
                const zip = new JSZip();
                const loaded = await zip.loadAsync(bytes);
                const kmlEntries = Object.keys(loaded.files).filter(n => n.toLowerCase().endsWith(".kml"));
                const entry = kmlEntries.find(n => n.toLowerCase() === "doc.kml") || kmlEntries[0];
                if (!entry) throw new Error("No .kml file found inside KMZ.");
                kmlString = await loaded.file(entry).async("string");
            } else {
                this.state.status = "Decoding KML text...";
                kmlString = new TextDecoder("utf-8").decode(bytes);
            }

            if (!kmlString.trim()) throw new Error("File content is empty.");

            this.state.status = "Parsing KML...";
            const parser = new DOMParser();
            const dom = parser.parseFromString(kmlString, "text/xml");

            const parseErr = dom.querySelector("parsererror");
            if (parseErr) throw new Error("XML parse error: " + parseErr.textContent.substring(0, 120));

            const layers = [];
            const bounds = L.latLngBounds([]);
            this.parsePlacemarks(dom, layers, bounds);

            if (layers.length === 0) {
                this.state.status = "No geometry found in KML.";
                return;
            }

            this.state.status = "Rendering...";
            layers.forEach(l => {
                l.addTo(this.map);
                this.layers.push(l);
            });

            if (bounds.isValid()) {
                this.map.fitBounds(bounds, { padding: [30, 30] });
            }

            // Invalidate size one more time after rendering
            setTimeout(() => { if (this.map) this.map.invalidateSize(); }, 200);
            this.state.status = `✓ Rendered ${layers.length} layer(s).`;
            console.log("KML Viewer V6: Rendered", layers.length, "layers.");

        } catch (e) {
            console.error("KML Viewer V6 render error:", e);
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
