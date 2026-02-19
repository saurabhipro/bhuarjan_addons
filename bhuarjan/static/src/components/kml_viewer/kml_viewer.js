/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useEffect } from "@odoo/owl";
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

        onMounted(async () => {
            await this.loadDependencies();
            this.initializeMap();
            this.renderKml();
        });

        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
        });

        useEffect(() => {
            this.renderKml();
        }, () => [this.props.record.data[this.props.name]]);
    }

    async loadDependencies() {
        try {
            await loadCSS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css");
            await loadJS("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
            // Omnivore for KML parsing
            await loadJS("https://api.tiles.mapbox.com/mapbox.js/plugins/leaflet-omnivore/v0.3.1/leaflet-omnivore.min.js");
        } catch (e) {
            console.error("Failed to load map dependencies", e);
        }
    }

    initializeMap() {
        if (!this.mapContainer.el || this.map) return;

        // Default view (India)
        this.map = L.map(this.mapContainer.el).setView([20.5937, 78.9629], 5);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
    }

    renderKml() {
        if (!this.map || !window.omnivore) return;

        const kmlData = this.props.record.data[this.props.name];

        if (this.layer) {
            this.map.removeLayer(this.layer);
            this.layer = null;
        }

        if (kmlData) {
            try {
                // Decode Base64 to string
                const kmlString = atob(kmlData);

                // Parse using omnivore
                const layer = omnivore.kml.parse(kmlString);

                layer.addTo(this.map);
                this.layer = layer;

                // Zoom to fit KML bounds
                if (layer.getBounds().isValid()) {
                    this.map.fitBounds(layer.getBounds());
                }
            } catch (e) {
                console.error("Error parsing KML data", e);
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
