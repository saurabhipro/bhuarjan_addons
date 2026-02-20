/** @odoo-module **/
/* version: v8-google-maps-fetch */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useState, useEffect } from "@odoo/owl";

const GOOGLE_MAPS_API_KEY = "abcd";
const JSZIP_CDN = "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js";

// Load a <script> tag once
function loadScript(url) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src^="${url.split("?")[0]}"]`)) {
            resolve();
            return;
        }
        const s = document.createElement("script");
        s.src = url;
        s.async = true;
        s.onload = resolve;
        s.onerror = () => reject(new Error("Failed to load: " + url));
        document.head.appendChild(s);
    });
}

// Load Google Maps API exactly once, via callback
function loadGoogleMaps() {
    return new Promise((resolve, reject) => {
        if (window.google && window.google.maps && window.google.maps.Map) {
            resolve();
            return;
        }
        if (window.__gmLoading) {
            // Already loading – wait for existing promise
            window.__gmLoading.then(resolve).catch(reject);
            return;
        }
        const cb = "__gmReady_" + Date.now();
        window.__gmLoading = new Promise((res, rej) => {
            window[cb] = () => { delete window[cb]; delete window.__gmLoading; res(); resolve(); };
            const s = document.createElement("script");
            s.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&callback=${cb}&v=weekly&libraries=`;
            s.async = true;
            s.defer = true;
            s.onerror = () => {
                delete window[cb];
                delete window.__gmLoading;
                const err = new Error("Google Maps API failed to load. Check your API key and network.");
                rej(err);
                reject(err);
            };
            document.head.appendChild(s);
        });
    });
}

export class KmlViewer extends Component {
    static template = "bhuarjan.KmlViewer";
    static props = { ...standardFieldProps };

    setup() {
        this.mapContainer = useRef("mapContainer");
        this.map = null;
        this.markers = [];
        this.polylines = [];
        this.polygons = [];

        this.state = useState({
            isLoading: true,
            error: null,
            status: "Initializing...",
            featureCount: 0,
        });

        onMounted(async () => {
            try {
                this.state.status = "Loading libraries...";
                await loadScript(JSZIP_CDN);
                await loadGoogleMaps();

                this.state.status = "Initializing Google Maps...";
                await new Promise(r => setTimeout(r, 80));

                this.initMap();
                await this.renderKml();
                this.state.isLoading = false;
            } catch (e) {
                console.error("KML Viewer V8:", e);
                this.state.error = e.message;
                this.state.isLoading = false;
            }
        });

        onWillUnmount(() => {
            this.clearOverlays();
            this.map = null;
        });

        // Re-render when field value changes (e.g. user uploads a new file)
        useEffect(() => {
            if (!this.state.isLoading && this.map) {
                this.renderKml();
            }
        }, () => [this.props.record.data[this.props.name]]);
    }

    initMap() {
        const el = this.mapContainer.el;
        if (!el || this.map) return;

        this.map = new google.maps.Map(el, {
            center: { lat: 22.5937, lng: 80.9629 },
            zoom: 5,
            mapTypeId: google.maps.MapTypeId.HYBRID,   // Satellite + labels = Google Earth feel
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
            gestureHandling: "greedy",
        });

        // Ensure map fills container after layout is complete
        setTimeout(() => {
            if (this.map) google.maps.event.trigger(this.map, "resize");
        }, 300);
    }

    clearOverlays() {
        (this.markers || []).forEach(m => m.setMap(null));
        (this.polylines || []).forEach(p => p.setMap(null));
        (this.polygons || []).forEach(p => p.setMap(null));
        this.markers = [];
        this.polylines = [];
        this.polygons = [];
    }

    // ─── Binary data fetching ────────────────────────────────────────────────
    // In Odoo 18, saved binary fields return `true` (not the base64 string)
    // to avoid sending large payloads on every form load.
    // We must fetch the actual bytes via /web/content instead.
    async fetchBinaryBytes() {
        const value = this.props.record.data[this.props.name];

        // No file
        if (!value) return null;

        // If it's a plain base64 string (e.g. newly uploaded, not yet saved)
        if (typeof value === "string" && value.length > 10) {
            return this.base64ToBytes(value);
        }

        // Otherwise fetch from server (saved record returns true/false for binary)
        const model = this.props.record.resModel;
        const id = this.props.record.resId;
        const field = this.props.name;

        if (!id) {
            throw new Error("Please save the record first before viewing the map.");
        }

        const url = `/web/content?model=${encodeURIComponent(model)}&id=${id}&field=${encodeURIComponent(field)}&download=1`;
        this.state.status = "Downloading KML/KMZ file...";
        const resp = await fetch(url, { credentials: "same-origin" });
        if (!resp.ok) throw new Error(`File download failed: HTTP ${resp.status}`);
        const buf = await resp.arrayBuffer();
        return new Uint8Array(buf);
    }

    // Robust base64 → Uint8Array
    base64ToBytes(b64) {
        let s = b64.replace(/[\s\r\n]+/g, "")
            .replace(/-/g, "+")
            .replace(/_/g, "/");
        const mod = s.length % 4;
        if (mod === 2) s += "==";
        else if (mod === 3) s += "=";
        const bin = atob(s);
        const out = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
        return out;
    }

    // ─── KML parsing helpers ─────────────────────────────────────────────────
    parseCoords(str) {
        return str.trim().split(/\s+/).map(t => {
            const p = t.split(",");
            const lng = parseFloat(p[0]), lat = parseFloat(p[1]);
            return (!isNaN(lat) && !isNaN(lng)) ? new google.maps.LatLng(lat, lng) : null;
        }).filter(Boolean);
    }

    kmlColorToHex(kml) {
        if (!kml || kml.length < 6) return "#2979ff";
        const c = kml.replace(/[^0-9a-fA-F]/g, "").padStart(8, "0");
        return `#${c.slice(6, 8)}${c.slice(4, 6)}${c.slice(2, 4)}`;
    }

    placemarkStyle(pm) {
        const st = pm.querySelector("Style");
        return {
            strokeColor: st ? this.kmlColorToHex(st.querySelector("LineStyle > color")?.textContent) : "#2979ff",
            fillColor: st ? this.kmlColorToHex(st.querySelector("PolyStyle > color")?.textContent) : "#2979ff",
            strokeOpacity: 1,
            fillOpacity: 0.35,
            strokeWeight: 2,
        };
    }

    parsePlacemarks(dom, bounds) {
        let count = 0;
        dom.querySelectorAll("Placemark").forEach(pm => {
            const name = pm.querySelector("name")?.textContent?.trim() || "";
            const desc = pm.querySelector("description")?.textContent?.trim() || "";
            const infoHtml = `<div style="max-width:280px;font-family:sans-serif"><b>${name}</b>${desc ? "<br><small>" + desc + "</small>" : ""}</div>`;

            // Points
            pm.querySelectorAll("Point > coordinates").forEach(c => {
                const pts = this.parseCoords(c.textContent);
                if (!pts.length) return;
                const mk = new google.maps.Marker({ position: pts[0], map: this.map, title: name });
                if (name || desc) {
                    const iw = new google.maps.InfoWindow({ content: infoHtml });
                    mk.addListener("click", () => iw.open(this.map, mk));
                }
                this.markers.push(mk);
                bounds.extend(pts[0]);
                count++;
            });

            // LineStrings (direct + inside MultiGeometry)
            pm.querySelectorAll("LineString > coordinates").forEach(c => {
                const pts = this.parseCoords(c.textContent);
                if (pts.length < 2) return;
                const sty = this.placemarkStyle(pm);
                const pl = new google.maps.Polyline({
                    path: pts, map: this.map,
                    strokeColor: sty.strokeColor, strokeOpacity: 1, strokeWeight: 3,
                });
                if (name || desc) {
                    const iw = new google.maps.InfoWindow({ content: infoHtml });
                    pl.addListener("click", e => { iw.setPosition(e.latLng); iw.open(this.map); });
                }
                this.polylines.push(pl);
                pts.forEach(p => bounds.extend(p));
                count++;
            });

            // Polygons
            pm.querySelectorAll("Polygon").forEach(poly => {
                const oc = poly.querySelector("outerBoundaryIs > LinearRing > coordinates");
                if (!oc) return;
                const pts = this.parseCoords(oc.textContent);
                if (pts.length < 3) return;
                const sty = this.placemarkStyle(pm);
                const pg = new google.maps.Polygon({
                    paths: pts, map: this.map,
                    strokeColor: sty.strokeColor, strokeOpacity: 1, strokeWeight: 2,
                    fillColor: sty.fillColor, fillOpacity: sty.fillOpacity,
                });
                if (name || desc) {
                    const iw = new google.maps.InfoWindow({ content: infoHtml });
                    pg.addListener("click", e => { iw.setPosition(e.latLng); iw.open(this.map); });
                }
                this.polygons.push(pg);
                pts.forEach(p => bounds.extend(p));
                count++;
            });
        });
        return count;
    }

    // ─── Main render ─────────────────────────────────────────────────────────
    async renderKml() {
        if (!this.map) return;
        this.clearOverlays();

        try {
            const bytes = await this.fetchBinaryBytes();
            if (!bytes) {
                this.state.status = "No KML/KMZ file uploaded.";
                return;
            }

            this.state.error = null;
            let kmlString = "";

            // KMZ = ZIP (magic: PK 0x50 0x4B)
            if (bytes[0] === 0x50 && bytes[1] === 0x4B) {
                this.state.status = "Extracting KMZ...";
                if (!window.JSZip) throw new Error("JSZip not loaded.");
                const zip = await new JSZip().loadAsync(bytes);
                const files = Object.keys(zip.files).filter(n => n.toLowerCase().endsWith(".kml"));
                const entry = files.find(n => n.toLowerCase() === "doc.kml") || files[0];
                if (!entry) throw new Error("No .kml file found inside KMZ.");
                kmlString = await zip.file(entry).async("string");
            } else {
                kmlString = new TextDecoder("utf-8").decode(bytes);
            }

            if (!kmlString.trim()) throw new Error("KML file is empty.");

            this.state.status = "Parsing KML...";
            const dom = new DOMParser().parseFromString(kmlString, "text/xml");
            const err = dom.querySelector("parsererror");
            if (err) throw new Error("XML error: " + err.textContent.slice(0, 120));

            this.state.status = "Rendering features...";
            const bounds = new google.maps.LatLngBounds();
            const count = this.parsePlacemarks(dom, bounds);

            if (count === 0) {
                this.state.status = "⚠ No geometry found in KML.";
                return;
            }

            if (!bounds.isEmpty()) {
                this.map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
                google.maps.event.addListenerOnce(this.map, "idle", () => {
                    if (this.map.getZoom() > 18) this.map.setZoom(16);
                });
            }

            // Final resize to ensure full-width render
            setTimeout(() => {
                if (this.map) google.maps.event.trigger(this.map, "resize");
            }, 200);

            this.state.featureCount = count;
            this.state.status = `✓ ${count} feature(s) loaded`;
        } catch (e) {
            console.error("KML Viewer V8:", e);
            this.state.error = "❌ " + e.message;
            this.state.status = "Failed.";
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer (Google Maps)",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
