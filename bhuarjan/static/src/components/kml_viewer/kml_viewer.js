/** @odoo-module **/

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
            status: "Initializing...",
        });

        onMounted(async () => {
            try {
                this.state.status = "Loading Google Maps...";
                await this.loadDependencies();

                // Wait for Google Maps to be fully ready
                const checkGoogle = setInterval(() => {
                    if (window.google && window.google.maps) {
                        clearInterval(checkGoogle);
                        this.initializeMap();
                        this.renderKml();
                        this.state.isLoading = false;
                    }
                }, 100);
            } catch (e) {
                console.error("Setup error:", e);
                this.state.error = "Error: " + e.message;
                this.state.status = "Failed.";
                this.state.isLoading = false;
            }
        });
    }

    async loadDependencies() {
        // Load JSZip for KMZ
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js");
        // Load toGeoJSON (Mapbox) to convert KML -> GeoJSON
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/togeojson/0.16.0/togeojson.min.js");

        // Load Google Maps API
        if (!window.google || !window.google.maps) {
            await loadJS(`https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`);
        }
    }

    initializeMap() {
        if (!this.mapContainer.el) return;

        this.state.status = "Initializing map...";
        this.map = new google.maps.Map(this.mapContainer.el, {
            center: { lat: 20.5937, lng: 78.9629 }, // India
            zoom: 5,
            mapTypeId: 'terrain'
        });
    }

    async renderKml() {
        if (!this.map || !window.toGeoJSON || !window.JSZip || !window.google) return;

        const kmlData = this.props.record.data[this.props.name];

        // Clear existing data layer
        this.map.data.forEach((feature) => {
            this.map.data.remove(feature);
        });

        if (kmlData) {
            this.state.status = "Processing data...";
            try {
                // Clean base64
                const cleanKmlData = kmlData.replace(/\s/g, '');
                const binaryString = atob(cleanKmlData);

                let kmlString = "";

                if (binaryString.startsWith("PK")) {
                    this.state.status = "Unzipping KMZ...";
                    const zip = new JSZip();
                    const loadedZip = await zip.loadAsync(binaryString);
                    const kmlFiles = Object.keys(loadedZip.files).filter(f => f.toLowerCase().endsWith('.kml'));
                    const kmlFile = kmlFiles.find(name => name.toLowerCase() === 'doc.kml') || kmlFiles[0];
                    if (kmlFile) {
                        kmlString = await loadedZip.file(kmlFile).async("string");
                    }
                } else {
                    // Decode text
                    try {
                        const uint8Array = new Uint8Array(binaryString.length);
                        for (let i = 0; i < binaryString.length; i++) {
                            uint8Array[i] = binaryString.charCodeAt(i);
                        }
                        const decoder = new TextDecoder('utf-8');
                        kmlString = decoder.decode(uint8Array);
                    } catch (e) {
                        kmlString = binaryString;
                    }
                }

                if (!kmlString) {
                    this.state.status = "No KML content found.";
                    return;
                }

                this.state.status = "Parsing KML...";
                // Parse XML
                const parser = new DOMParser();
                const kmlDom = parser.parseFromString(kmlString, "text/xml");

                // Convert to GeoJSON
                const geoJson = toGeoJSON.kml(kmlDom);

                this.state.status = "Rendering on Map...";
                // Add to Google Maps
                const features = this.map.data.addGeoJson(geoJson);

                // Fit Bounds
                const bounds = new google.maps.LatLngBounds();
                this.map.data.forEach((feature) => {
                    const processPoints = (geometry) => {
                        if (geometry.getType() === 'Point') {
                            bounds.extend(geometry.get());
                        } else if (geometry.getType() === 'Polygon' || geometry.getType() === 'LineString') {
                            geometry.getArray().forEach((path) => {
                                // For Polygon, path is LinearRing (array of points)
                                // For LineString, path is a point? No, LineString getArray returns points.
                                // Google Maps Data geometry structure is slightly different.

                                const type = geometry.getType();
                                if (type === 'LineString') {
                                    bounds.extend(path);
                                } else if (type === 'Polygon') {
                                    // Polygon -> Array of LinearRings -> Array of LatLngs
                                    path.getArray().forEach(latLng => bounds.extend(latLng));
                                }
                            });
                        } else if (geometry.getType() === 'MultiPolygon' || geometry.getType() === 'MultiLineString' || geometry.getType() === 'GeometryCollection') {
                            geometry.getArray().forEach(processPoints);
                        }
                    };
                    processPoints(feature.getGeometry());
                });

                if (!bounds.isEmpty()) {
                    this.map.fitBounds(bounds);
                    this.state.status = "Rendered successfully.";
                } else {
                    this.state.status = "Map loaded (No geometry found).";
                }

                // Restyle features to look like KML defaults if possible, or just standard colors
                this.map.data.setStyle({
                    fillColor: 'blue',
                    strokeWeight: 2,
                    strokeColor: 'blue'
                });

            } catch (e) {
                console.error("Mapping error", e);
                this.state.error = e.message;
                this.state.status = "Error parsing.";
            }
        } else {
            this.state.status = "No data.";
        }
    }
}

export const kmlViewer = {
    component: KmlViewer,
    displayName: "KML Viewer",
    supportedTypes: ["binary"],
};

registry.category("fields").add("kml_viewer", kmlViewer);
