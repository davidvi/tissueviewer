<template>
  <v-app>

    <!-- OVERLAY -->
    <v-main class="d-flex">
      <div id="right-arrow-overlay" style="display: none;">
        <span style="font-size: 2em; color: white;">&rarr;</span>
      </div>

      <!-- VIEW -->
      <div id="view"></div>

      <!-- NAVIGATION -->
      <v-container fluid id="navigation-menu" style="display: block;">
        <v-row align="center" justify="space-between">
          <v-col>
            <h3>Settings</h3>
          </v-col>
          <v-col class="text-right">
            <!-- Save and minimize/restore buttons -->
            <v-btn icon @click="saveDetails" v-if="saveEnabled">
              <v-icon>mdi-content-save</v-icon>
            </v-btn>
            <v-btn icon @click="windowMinimal = !windowMinimal">
              <div v-if="windowMinimal">
                <v-icon>mdi-window-restore</v-icon>
              </div>
              <div v-else>
                <v-icon>mdi-window-minimize</v-icon>
              </div>
            </v-btn>
          </v-col>
        </v-row>
        <div v-if="!samples.length">
        <v-row>
          <v-col>
              <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </v-col>
          </v-row>
        </div>
        <div v-else>
        <v-row>
          <v-col>
            <v-select :items="samples" v-model="selectedSampleNameLocal" label="Select slide" item-value="name"
              item-title="name"></v-select>
          </v-col>
        </v-row>
        <div v-if="!windowMinimal">
        <v-row>
          <v-col>
            <b>Channels</b>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <div v-for="file in selectedSample.files" :key="file">
              <v-card class="ma-1" outlined color="#34495e" v-if="ch[file] != 'empty'">
                <v-card-text>
                  <v-row>
                    <v-col cols="10">
                      <v-text-field v-model="ch_stain[file]" label="Stain description" dense></v-text-field>
                    </v-col>
                    <v-col cols="1">
                      <!-- Remove stain button -->
                      <v-btn icon @click="removeStain(file)">
                        <v-icon>mdi-close</v-icon>
                      </v-btn>
                    </v-col>
                  </v-row>
                  <v-row>
                    <v-col>
                      <!-- Stain description, color selection, and gain adjustment -->

                      <v-select v-model="ch[file]" :items="colorOptions" label="Channel color" dense
                        @update:modelValue="settingsChanged"></v-select>
                      <v-slider v-model="gain[file]" :max="10" :min="0" :step="1" label="Gain" dense color="grey"
                        @update:modelValue="settingsChanged"></v-slider>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </div>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <b>Add channel</b>
          </v-col>
        </v-row>
        <v-row>
          <v-col>

            <!-- Select stain to add and Add stain button -->
            <v-select :items="stainOptions" v-model="addStainFileLocal" label="Select stain to add" item-value="file"
              item-title="stain" @update:modelValue="addStain"></v-select>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <b>Share</b>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-btn icon>
        <a :href="`?sample=${selectedSampleName}`" target="_blank">
          <v-icon color="white">mdi-share</v-icon>
        </a>
      </v-btn>
          </v-col>
        </v-row>
      </div>
      </div>
      </v-container>


    </v-main>

  </v-app>
</template>

<script>
import OpenSeadragon from "openseadragon";
import { mapGetters, mapActions, mapState, mapMutations } from "vuex";

export default {
  components: {
  },
  data() {
    return {
      viewer: null,
      windowMinimal: false,
    }
  },
  computed: {
    ...mapState(["samples", "selectedSample", "gain", "ch", "ch_stain", "overlays",
      "slideSettingsShown", "selectedSampleName", "currentSlide", "colorOptions", "description",
      "stainOptions", "addStainFile", "viewportCenter", "viewportZoom", "viewportBounds", 
      "saveEnabled"]),
    viewportBoundsLocal: {
      get() {
        return this.viewportBounds;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "viewportBounds", value: value });
      },
    },
    viewportCenterLocal: {
      get() {
        return this.viewportCenter;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "viewportCenter", value: value });
      },
    },
    viewportZoomLocal: {
      get() {
        return this.viewportZoom;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "viewportZoom", value: value });
      },
    },
    addStainFileLocal: {
      get() {
        return this.addStainFile;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "addStainFile", value: value });
      },
    },

    stainOptions: {
      get() {
        let buf = this.selectedSample.files ? this.selectedSample.files.map(file => {
          return { file: file, stain: this.ch_stain[file] };
        }) : [];
        return buf;
      }
    },
    selectedSampleNameLocal: {
      get() {
        return this.selectedSampleName;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "selectedSampleName", value: value });
      },
    },
    slideSettingsShownLocal: {
      get() {
        return this.slideSettingsShown;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "slideSettingsShown", value: value });
      },
    },
    currentSlideLocal: {
      get() {
        return this.currentSlide;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "currentSlide", value: value });
      },
    },
  },
  watch: {
    selectedSampleNameLocal: function () {
      this.loadSample();
    },
    currentSlideLocal: function (newValue, oldValue) {
      console.log("changed current slide to: ", newValue);

      this.viewer.open(newValue);
      for (let i = 0; i < this.overlays.length; i++) {
        this.addOverlay(this.overlays[i].location.x, this.overlays[i].location.y, this.overlays[i].number);
      }

    }
  },
  methods: {
    ...mapActions(["loadSampleSheet", "loadSample", "reloadSlide", "saveDetails", "addStain", "removeStain"]),
    ...mapMutations(["SET_STATE_PROPERTY"]),
    loadOpenSeaDragon() {
      this.viewer = new OpenSeadragon({
        id: "view",
        prefixUrl: "images/",
        timeout: 120000, //120000
        animationTime: 1, //0.5
        blendTime: 1, //0.1
        constrainDuringPan: true,
        maxZoomPixelRatio: 3, //2
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
                  number: this.overlays.length > 0 ? this.overlays.map(overlay => overlay.number).sort((a, b) => a - b)[this.overlays.length - 1] + 1 : 1
                });

                console.log(this.overlays);

                //Add overlay, disabled for now
                // this.addOverlay(elementCoordiantes.x, elementCoordiantes.y, this.overlays[this.overlays.length - 1].number);
              },
            });
          });
        }
      });

      this.viewer.addHandler('open', () => {
        this.setBounds();
      });

    },

    settingsChanged() {
      console.log("settings changed");
      this.getBounds();
      this.reloadSlide();
    },

    setBounds() {
      if (this.viewportBoundsLocal) {
        console.log("setting viewport to: ", this.viewportBoundsLocal);
        this.viewer.viewport.fitBounds(this.viewportBoundsLocal, true);
      }
    },

    getBounds() {
      this.viewportBoundsLocal = this.viewer.viewport.getBounds();

      console.log("viewport bounds: ", this.viewportBoundsLocal);
    },

    addOverlay(x, y, number) {
      const overlayElement = document.createElement("div");
      overlayElement.className = "overlay-" + number;
      overlayElement.innerHTML = '<span>' + number + '</span><span style="font-size: 2em; color: white;">&rarr;</span>';

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

  },
  mounted() {
    this.loadOpenSeaDragon();
    this.loadSampleSheet(this.$route.query.sample);
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

#navigation-menu {
  z-index: 1000;
  background-color: #2c3e50;
  color: #ecf0f1;
  padding: 10px;
  border-radius: 4px;
  position: fixed;
  top: 5vh;
  right: 1vw;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
  width: 300px;
  max-height: 90vh;
  overflow-y: auto;
  font-family: Arial, sans-serif;
}

.v-btn {
  background-color: #34495e;
  color: #ecf0f1;
  margin: 0px 0;
  border: none;
  text-transform: none;
  box-shadow: none;
}

.v-btn:hover {
  background-color: #2c3e50;
}

.v-slider .v-slider__thumb {
  background-color: #ecf0f1;
}

.v-slider {
  margin: 0px;
}

.v-select {
  margin: 0px;
}

.v-label {
  color: #ecf0f1;
}

.v-text-field input,
.v-select .v-select__selection {
  background-color: #34495e;
  color: #ecf0f1;
  border: 1px solid #4a6572;
}

.current-slide {
  background-color: #ccc;
}

.card {
  margin: 0px;

}

.v-col {
  margin: 0px;
  padding-top: 1px;
  padding-bottom: 1px;
}
</style>