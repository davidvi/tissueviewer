<template>
  <v-app>
    <v-app-bar color="primary">
      <v-btn @click="slideSettingsShown = !slideSettingsShown">{{ slideSettingsShown ? 'hide settings' : 'show settings'
      }}</v-btn>
      <v-btn @click="saveDetails">Save settings</v-btn>
      <v-btn @click="reloadSlide">Reload slide</v-btn>
      <v-select :items="samples" v-model="selectedSampleName" label="Select slide" item-value="name"
        item-title="name"></v-select>
        <v-spacer></v-spacer>
        <span>right click on image to add annotation</span>
    </v-app-bar>
    <v-navigation-drawer v-model="slideSettingsShown" app temporary width="250">
      <v-expansion-panels>
        <v-expansion-panel v-if="selectedSample && selectedSample.files && selectedSample.files.length > 0">
          <v-expansion-panel-title>Slide details</v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row>
              <v-col>
                <v-textarea label="Description" v-model="description"></v-textarea>
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
        <v-expansion-panel title="Multi channel settings" v-if="selectedSample && selectedSample.files && selectedSample.files.length > 1">
          <v-expansion-panel-text>
            <v-list>
              <v-list-item v-for="file in selectedSample.files" :key="file">
                <v-list-item-title>
                  <b>{{ file }}</b>
                </v-list-item-title>
                <v-list-item-content>
                      <p>gain: {{ gain[file] }}</p>
                      <v-slider v-model="gain[file]" :max="10" :min="1" :step="1" default="1"></v-slider>
                      <p>color</p>
                      <v-select v-model="ch[file]" :items="colorOptions" default="empty"></v-select>
                      <p>stain description</p>
                      <v-text-field v-model="ch_stain[file]" label="Stain description"></v-text-field>
                  <v-divider></v-divider>
                </v-list-item-content>
                </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
        <v-expansion-panel v-if="overlays && overlays.length > 0">
          <v-expansion-panel-title>Slide annotations</v-expansion-panel-title> 
          <v-expansion-panel-text>
            <v-list>
              <v-list-item v-for="(overlay, index) in overlays" :key="overlay.number">
                <v-list-item-title>
                  <b>{{ overlay.number }}</b>
                </v-list-item-title>
                <v-list-item-content>
                      <p>annotation description</p>
                      <v-text-field v-model="overlay[index]" label="Annotation description"></v-text-field>
                      <v-btn color="warning" @click="deleteOverlay(index)">Delete</v-btn>
                  <v-divider></v-divider>
                </v-list-item-content>
                </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-navigation-drawer>
    <v-main class="d-flex">
      <div id="right-arrow-overlay" style="display: none;">
        <span style="font-size: 2em; color: white;">&rarr;</span>
      </div>
      <div id="view"></div>
    </v-main>

  </v-app>
</template>

<script>
import axios from "axios";
import OpenSeadragon from "openseadragon";

const base_url = process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:2000";

export default {
  components: {
  },
  data() {
    return {
      selectedSample: {},
      selectedSampleName: "",
      samples: [],
      viewer: null,
      ch: {},
      ch_stain: {},
      gain: {},
      description: "",
      slideSettingsShown: false,
      colorOptions: ["empty", "red", "green", "blue", "yellow", "cyan", "white", "black"],
      overlays: [],
    }
  },
  computed: {

    dropdownOptions() {
      let buf = [];
      buf = this.selectedSample.files ? this.selectedSample.files : [];
      buf.push("empty");
      return buf;
    }

  },
  watch: {
    selectedSampleName: function () {
      this.loadSample(this.selectedSampleName);
    }
  },
  methods: {
    loadOpenSeaDragon() {
      this.viewer = new OpenSeadragon({
        id: "view",
        prefixUrl: "images/",
        timeout: 120000,
        animationTime: 0.5,
        blendTime: 0.1,
        constrainDuringPan: true,
        maxZoomPixelRatio: 2,
        minZoomImageRatio: 1,
        visibilityRatio: 1,
        zoomPerScroll: 2,
        showNavigationControl: true,
        navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_LEFT,
      });

      this.viewer.addHandler('tile-drawn', () => {
      if (!this.mouseTrackerInitialized) {
        this.mouseTrackerInitialized = true;

        this.$nextTick(() => {
          new OpenSeadragon.MouseTracker({
            element: this.viewer.canvas,
            contextMenuHandler: e => {
              e.originalEvent.preventDefault();
              const clickPosition = e.position;

              // Convert the click position to image coordinates
              const imageCoordinates = this.viewer.viewport.viewerElementToImageCoordinates(clickPosition);

              const elementCoordiantes = this.viewer.viewport.imageToViewportCoordinates(imageCoordinates);

              this.overlays.push({
                location: {
                  x: elementCoordiantes.x,
                  y: elementCoordiantes.y
                },
                description: "", 
                number: this.overlays.length > 0 ? this.overlays.map(overlay => overlay.number).sort((a, b) => a - b)[this.overlays.length-1] + 1 : 1
              });

              console.log(this.overlays);

              this.addOverlay(elementCoordiantes.x, elementCoordiantes.y, this.overlays[this.overlays.length-1].number);
            },
            
          });

        });
      }
    });

    },

    addOverlay(x, y, number) {
      const overlayElement = document.createElement("div");
      overlayElement.className = "overlay-"+number; 
      overlayElement.innerHTML = '<span>'+number+'</span><span style="font-size: 2em; color: white;">&rarr;</span>';

      this.viewer.addOverlay({
        element: overlayElement,
        location: new OpenSeadragon.Point(x, y),
        placement: OpenSeadragon.Placement.RIGHT
      });

      new OpenSeadragon.MouseTracker({
        element: overlayElement,
        clickHandler: (event) => {
          event.originalEvent.preventDefault();
          console.log(event);
          console.log('Overlay clicked');
          // Add your custom logic for handling the click event on the overlay here
        },
      }).setTracking(true);
    },  

    deleteOverlay(index) {
      this.overlays.splice(index, 1);
      this.reloadSlide();
    },

    loadSampleSheet() {
      axios.get(`${base_url}/samples.json`)
        .then(response => {
          this.samples = response.data.samples;
          console.log(this.samples);
        })
    },

    saveDetails() {
      let data = {
        ch: this.ch,
        gain: this.gain,
        ch_stain: this.ch_stain,
        description: this.description,
        overlays: this.overlays,
      }
      this.samples.filter(s => s.name === this.selectedSample.name)[0].details = data;

      console.log(data);
      axios.post(`${base_url}/save/${this.selectedSample.name}`, data)
        .then(response => {
          console.log(response);
        })
    },

    reloadSlide() {

      const chString = this.selectedSample.files.map((file) => {
        return this.ch[file] ? this.ch[file] : "empty";
      }).join(";");

      const gainString = this.selectedSample.files.map((file) => {
        return this.gain[file] ? this.gain[file] : "1";
      }).join(";");

      const filesString = this.selectedSample.files.join(";");

      let currentSlide = `${base_url}/${filesString}/${chString}/${gainString}/${this.selectedSample.name}.dzi`;

      console.log(currentSlide);

      this.viewer.open(currentSlide)

      for (let i = 0; i < this.overlays.length; i++) {
        this.addOverlay(this.overlays[i].location.x, this.overlays[i].location.y, this.overlays[i].number);
      }
    },

    loadSample(sample) {
      this.selectedSample = this.samples.filter(s => s.name === sample)[0];

      this.ch = this.selectedSample.details.ch ? this.selectedSample.details.ch : {};
      this.gain = this.selectedSample.details.gain ? this.selectedSample.details.gain : {};
      this.ch_stain = this.selectedSample.details.ch_stain ? this.selectedSample.details.ch_stain : {};
      this.description = this.selectedSample.details.description ? this.selectedSample.details.description : "";
      this.overlays = this.selectedSample.details.overlays ? this.selectedSample.details.overlays : [];

      this.reloadSlide();
    }

  },
  mounted() {

    this.loadOpenSeaDragon();
    this.loadSampleSheet();
  },
}
</script>

<style>
div#view {
  flex: 1;
  background-color: black;
  border: 1px solid #000;
  color: white;
}

.current-slide {
  background-color: #ccc;
}

.card {
  margin: 10px;
  /* padding: 10px !important; */
}
</style>