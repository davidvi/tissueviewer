<template>
  <v-app>

    <v-main class="d-flex">
      <div id="right-arrow-overlay" style="display: none;">
        <span style="font-size: 2em; color: white;">&rarr;</span>
      </div>
      <div id="view"></div>


      <div id="navigation-menu" style="display: block;">
        <v-select :items="samples" v-model="selectedSampleNameLocal" label="Select slide" item-value="name"
          item-title="name"></v-select>
        <v-btn @click="saveDetails">Save settings</v-btn>
        <v-btn @click="getBounds(); reloadSlide()">Reload slide</v-btn>
        <!-- Add other navigation buttons here -->

        <div>
          <div v-for="file in selectedSample.files" :key="file">
            <div v-if="ch[file] != 'empty'">
              <v-text-field v-model="ch_stain[file]" label="Stain description"></v-text-field>
              <v-select v-model="ch[file]" :items="colorOptions" default="empty"></v-select>
              <v-slider v-model="gain[file]" :max="10" :min="1" :step="1" default="1" color="grey"></v-slider>
              <v-btn @click="removeStain(file)">Remove stain</v-btn>
            </div>
          </div>
        </div>
        <v-select :items="stainOptions" v-model="addStainFileLocal" label="Select stain to add" item-value="file"
          item-title="stain"></v-select>
        <v-btn @click="addStain">Add stain</v-btn>
      </div>

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
    }
  },
  computed: {
    ...mapState(["samples", "selectedSample", "gain", "ch", "ch_stain", "overlays",
      "slideSettingsShown", "selectedSampleName", "currentSlide", "colorOptions", "description", 
      "stainOptions", "addStainFile", "viewportCenter", "viewportZoom", "viewportBounds"]),
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

      // this.viewer.viewport.panTo(new OpenSeadragon.Point(this.viewportCenterLocal.x, this.viewportCenterLocal.y), true);
      // this.viewer.viewport.zoomTo(this.viewportZoomLocal, null, true);
      // this.viewer.viewport.fitBoundsWithConstraints(this.viewportBoundsLocal, true);

      if(this.viewportBoundsLocal){
        console.log("setting viewport to: ", this.viewportBoundsLocal);
        this.viewer.viewport.fitBounds(this.viewportBoundsLocal); 
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
        maxZoomPixelRatio: 1, //2
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

                this.addOverlay(elementCoordiantes.x, elementCoordiantes.y, this.overlays[this.overlays.length - 1].number);
              },
            });
          });
        }
      });

      // this.viewer.addHandler('viewport-change', () => {
        // const center = this.viewer.viewport.getCenter();
        // const zoom = this.viewer.viewport.getZoom();

        // this.viewportCenterLocal = {
        //   x: center.x,
        //   y: center.y
        // };
        // this.viewportZoomLocal = zoom;
        // this.viewportBoundsLocal = this.viewer.viewport.getBounds();
      // });

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

#navigation-menu {
  z-index: 1000;
  background-color: #2c3e50; /* Dark blue background */
  color: #ecf0f1; /* Light text for contrast */
  padding: 10px;
  border-radius: 4px; /* Soft rounded corners */
  position: fixed;
  top: 50px;
  right: 50px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); /* More pronounced shadow for depth on dark themes */
  width: 300px; /* Adjust based on content */
  max-height: 80vh; /* Maximum height before scrolling, vh units ensure it's based on the viewport height */
  overflow-y: auto; /* Show scrollbar only if needed */
  font-family: Arial, sans-serif; /* Simple, readable font */
}

/* Adjust button styles for a dark theme */
.v-btn {
  background-color: #34495e;
  /* Darker grey background for buttons */
  color: #ecf0f1;
  /* Light text for readability */
  margin: 5px 0;
  /* Spacing between buttons */
  border: none;
  /* No borders for a flat design */
  text-transform: none;
  /* Avoid uppercase to maintain readability */
  box-shadow: none;
  /* No shadow for a flat design */
}

.v-btn:hover {
  background-color: #2c3e50;
  /* Even darker on hover to match the menu background */
}

/* Adjust slider thumb and input fields for a dark theme */
.v-slider .v-slider__thumb {
  background-color: #ecf0f1;
  /* Light color thumb for visibility */
}

.v-text-field input,
.v-select .v-select__selection {
  background-color: #34495e;
  /* Darker background for inputs */
  color: #ecf0f1;
  /* Light text for inputs for readability */
  border: 1px solid #4a6572;
  /* Slightly lighter border for definition */
}

.current-slide {
  background-color: #ccc;
}

.card {
  margin: 10px;
  /* padding: 10px !important; */
}
</style>