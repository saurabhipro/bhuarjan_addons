/** @odoo-module **/
/* version: v7-google-maps */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const GOOGLE_MAPS_API_KEY = "AIzaSyCQ1XvoKRmX1qqo2XwlLj2C2gCIiCjtgFE";
const JSZIP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js";

function loadScript(url) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${url}"]`)) {
            resolve();
            return;
        }
        const script = document.createElement("script");
        script.src = url;
        script.async = true;
        script.defer = true;
        script.onload = resolve;
        script.onerror = () => reject(new Error(`Failed to load: ${url}`));
        document.head.appendChild(script);
    });
}

function loadGoogleMaps() {
    return new Promise((resolve, reject) => {
        if (window.google && window.google.maps) {
            resolve();
            return;
        }
        // Unique callback name to avoid collisions
        const cb = "__gm_cb_" + Date.now();
        window[cb] = () => {
            delete window[cb];
            resolve();
        };
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&callback=${cb}&v=weekly`;
        script.async = true;
        script.defer = true;
        script.onerror = () => reject(new Error("Google Maps API failed to load. Check your API key."));
        document.head.appendChild(script);
    });
}

export class KmlViewer extends Component {
    static template = "bhuarjan.KmlViewer";
    static props = { ...standardFieldProps };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.dataLayers = [];
        this.markers = [];
        this.polylines = [];
        this.polygons = [];

        this.state = useState({
            isLoading: true,
            error: null,
            status: "Initializing Google Maps...",
            layerCount: 0,
        });

        onMounted(async () => {
            console.log("KML Viewer V7 (Google Maps): Mounted");
            try {
                this.state.status = "Loading JSZip...";
                await loadScript(JSZIP_CDN);

                this.state.status = "Loading Google Maps API...";
                await loadGoogleMaps();

                this.state.status = "Initializing map...";
                await new Promise(r => setTimeout(r, 100));

                this.initMap();
                await this.renderKml();
                this.state.isLoading = false;
            } catch (e) {
                console.error("KML Viewer V7 error:", e);
                this.state.error = e.message;
                this.state.isLoading = false;
            }
        });

        onWillUnmount(() => {
            this.clearLayers();
            this.map = null;
        });
    }

    initMap() {
        const el = this.mapContainer.el;
        if (!el || this.map) return;

        this.map = new google.maps.Map(el, {
            center: { lat: 22.5937, lng: 80.9629 },
            zoom: 5,
            mapTypeId: google.maps.MapTypeId.HYBRID,  // Satellite + labels (Google Earth look)
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
                position: google.maps.ControlPosition.TOP_RIGHT,
                mapTypeIds: [
                    google.maps.MapTypeId.ROADMAP,
                    google.maps.MapTypeId.SATELLITE,
                    google.maps.MapTypeId.HYBRID,
                    google.maps.MapTypeId.TERRAIN,
                ],
            },
            fullscreenControl: true,
            streetViewControl: false,
            zoomControl: true,
        });

        console.log("KML Viewer V7: Google Map initialized (HYBRID/satellite mode)");
    }

    clearLayers() {
        if (this.dataLayers) {
            this.dataLayers.forEach(dl => dl.setMap(null));
        }
        if (this.markers) {
            this.markers.forEach(m => m.setMap(null));
        }
        if (this.polylines) {
            this.polylines.forEach(p => p.setMap(null));
        }
        if (this.polygons) {
            this.polygons.forEach(p => p.setMap(null));
        }
        this.dataLayers = [];
        this.markers = [];
        this.polylines = [];
        this.polygons = [];
    }

    // Robust base64 decode
    decodeBase64ToBytes(b64) {
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

    // Parse KML coordinates string → array of google.maps.LatLng
    parseCoords(coordStr) {
        return coordStr.trim().split(/\s+/).map(triplet => {
            const parts = triplet.split(",");
            const lng = parseFloat(parts[0]);
            const lat = parseFloat(parts[1]);
            if (!isNaN(lat) && !isNaN(lng)) {
                return new google.maps.LatLng(lat, lng);
            }
            return null;
        }).filter(Boolean);
    }

    getStyleFromPlacemark(placemark) {
        const styleEl = placemark.querySelector("Style");
        let strokeColor = "#3388ff";
        let fillColor = "#3388ff";
        let strokeOpacity = 1;
        let fillOpacity = 0.35;
        let strokeWeight = 2;

        if (styleEl) {
            const lineColor = styleEl.querySelector("LineStyle > color")?.textContent;
            const polyColor = styleEl.querySelector("PolyStyle > color")?.textContent;
            if (lineColor) strokeColor = this.kmlColorToHex(lineColor);
            if (polyColor) fillColor = this.kmlColorToHex(polyColor);
        }
        return { strokeColor, fillColor, strokeOpacity, fillOpacity, strokeWeight };
    }

    // KML AABBGGRR → CSS #RRGGBB
    kmlColorToHex(kmlColor) {
        if (!kmlColor || kmlColor.length < 6) return "#3388ff";
        const c = kmlColor.replace(/[^0-9a-fA-F]/g, "").padStart(8, "0");
        const r = c.substring(6, 8);
        const g = c.substring(4, 6);
        const b = c.substring(2, 4);
        return `#${r}${g}${b}`;
    }

    parsePlacemarks(dom, bounds) {
        let count = 0;

        // Points
        dom.querySelectorAll("Placemark").forEach(placemark => {
            const name = placemark.querySelector("name")?.textContent || "";
            const desc = placemark.querySelector("description")?.textContent || "";
            const infoContent = `<div style="max-width:260px"><b>${name}</b>${desc ? "<br>" + desc : ""}</div>`;

            // --- Point ---
            placemark.querySelectorAll("Point > coordinates").forEach(c => {
                const coords = this.parseCoords(c.textContent);
                if (coords.length > 0) {
                    const marker = new google.maps.Marker({
                        position: coords[0],
                        map: this.map,
                        title: name,
                    });
                    if (name || desc) {
                        const iw = new google.maps.InfoWindow({ content: infoContent });
                        marker.addListener("click", () => iw.open(this.map, marker));
                    }
                    this.markers.push(marker);
                    bounds.extend(coords[0]);
                    count++;
                }
            });

            // --- LineString ---
            placemark.querySelectorAll("LineString > coordinates").forEach(c => {
                const coords = this.parseCoords(c.textContent);
                if (coords.length > 1) {
                    const style = this.getStyleFromPlacemark(placemark);
                    const polyline = new google.maps.Polyline({
                        path: coords,
                        map: this.map,
                        strokeColor: style.strokeColor,
                        strokeOpacity: style.strokeOpacity,
                        strokeWeight: style.strokeWeight + 1,
                    });
                    if (name || desc) {
                        const iw = new google.maps.InfoWindow({ content: infoContent });
                        polyline.addListener("click", e => {
                            iw.setPosition(e.latLng);
                            iw.open(this.map);
                        });
                    }
                    this.polylines.push(polyline);
                    coords.forEach(pt => bounds.extend(pt));
                    count++;
                }
            });

            // --- Polygon ---
            placemark.querySelectorAll("Polygon").forEach(poly => {
                const outerEl = poly.querySelector("outerBoundaryIs > LinearRing > coordinates");
                if (!outerEl) return;
                const outerCoords = this.parseCoords(outerEl.textContent);
                if (outerCoords.length < 3) return;

                const style = this.getStyleFromPlacemark(placemark);
                const polygon = new google.maps.Polygon({
                    paths: outerCoords,
                    map: this.map,
                    strokeColor: style.strokeColor,
                    strokeOpacity: style.strokeOpacity,
                    strokeWeight: style.strokeWeight,
                    fillColor: style.fillColor,
                    fillOpacity: style.fillOpacity,
                });
                if (name || desc) {
                    const iw = new google.maps.InfoWindow({ content: infoContent });
                    polygon.addListener("click", e => {
                        iw.setPosition(e.latLng);
                        iw.open(this.map);
                    });
                }
                this.polygons.push(polygon);
                outerCoords.forEach(pt => bounds.extend(pt));
                count++;
            });

            // --- MultiGeometry (recursively handles nested geometries) ---
            placemark.querySelectorAll("MultiGeometry").forEach(mg => {
                mg.querySelectorAll("LineString > coordinates").forEach(c => {
                    const coords = this.parseCoords(c.textContent);
                    if (coords.length > 1) {
                        const style = this.getStyleFromPlacemark(placemark);
                        const polyline = new google.maps.Polyline({
                            path: coords,
                            map: this.map,
                            strokeColor: style.strokeColor,
                            strokeOpacity: style.strokeOpacity,
                            strokeWeight: style.strokeWeight + 1,
                        });
                        this.polylines.push(polyline);
                        coords.forEach(pt => bounds.extend(pt));
                        count++;
                    }
                });
            });
        });

        return count;
    }

    async renderKml() {
        if (!this.map) return;

        this.clearLayers();

        const kmlData = this.props.record.data[this.props.name];
        if (!kmlData) {
            this.state.status = "No KML/KMZ file uploaded.";
            return;
        }

        this.state.error = null;
        this.state.status = "Decoding file...";

        try {
            let bytes;
            try {
                bytes = this.decodeBase64ToBytes(kmlData);
            } catch (e) {
                throw new Error("Base64 decode failed: " + e.message);
            }

            let kmlString = "";

            // Detect ZIP (KMZ) magic bytes: PK = 0x50 0x4B
            if (bytes[0] === 0x50 && bytes[1] === 0x4B) {
                this.state.status = "Extracting KMZ archive...";
                if (!window.JSZip) throw new Error("JSZip not loaded.");
                const zip = new JSZip();
                const loaded = await zip.loadAsync(bytes);
                const kmlEntries = Object.keys(loaded.files).filter(n => n.toLowerCase().endsWith(".kml"));
                const entry = kmlEntries.find(n => n.toLowerCase() === "doc.kml") || kmlEntries[0];
                if (!entry) throw new Error("No .kml file found inside KMZ.");
                kmlString = await loaded.file(entry).async("string");
                console.log("KML Viewer V7: Extracted KML from KMZ:", entry);
            } else {
                this.state.status = "Reading KML file...";
                kmlString = new TextDecoder("utf-8").decode(bytes);
            }

            if (!kmlString.trim()) throw new Error("File content is empty.");

            this.state.status = "Parsing KML...";
            const parser = new DOMParser();
            const dom = parser.parseFromString(kmlString, "text/xml");

            const parseErr = dom.querySelector("parsererror");
            if (parseErr) throw new Error("XML parse error: " + parseErr.textContent.substring(0, 150));

            this.state.status = "Rendering on Google Maps...";

            const bounds = new google.maps.LatLngBounds();
            const count = this.parsePlacemarks(dom, bounds);

            if (count === 0) {
                this.state.status = "⚠ No geometry found in KML file.";
                return;
            }

            if (!bounds.isEmpty()) {
                this.map.fitBounds(bounds);
                // Ensure we don't zoom in too close for single points
                google.maps.event.addListenerOnce(this.map, "idle", () => {
                    if (this.map.getZoom() > 18) this.map.setZoom(16);
                });
            }

            this.state.layerCount = count;
            this.state.status = `✓ Rendered ${count} feature(s) on Google Maps.`;
            console.log("KML Viewer V7: Rendered", count, "features.");

        } catch (e) {
            console.error("KML Viewer V7 render error:", e);
            this.state.error = "❌ " + e.message;
            this.state.status = "Render failed.";
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer (Google Maps)",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
