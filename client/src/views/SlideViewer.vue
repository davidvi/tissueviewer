<template>
 <div class="flex min-h-screen">

<!-- OVERLAY -->
<div id="right-arrow-overlay" hidden>
  <span class="text-2xl text-white">&rarr;</span>
</div>

<!-- VIEW -->
<div id="view" class="w-screen h-screen"></div>

<!-- NAVIGATION -->
<div id="navigation-menu" class="rounded text-gray-800 bg-gray-600">
  <div class="flex items-center justify-between p-4">
    <div>
      <strong class="text-white">Settings</strong>
    </div>
    <div class="flex space-x-2">
      <a class="p-2" :href="`?sample=${selectedSampleName}`" target="_blank">
            <share-icon class="icon" />
          </a>
      <button class="p-2" @click="saveDetails" v-if="saveEnabled">
          <archive-box-icon class="icon" />
      </button>
      <button class="p-2" @click="windowMinimal = !windowMinimal">
        <div v-if="windowMinimal">
          <plus-circle-icon class="icon" />
        </div>
        <div v-else>
          <minus-circle-icon class="icon" />
        </div>
      </button>
    </div>
  </div>
  <!-- IF LOADING -->
  <div v-if="!samples.length" class="p-4">
    <div class="flex justify-center">
      <strong class="whiet">Loading..</strong>
    </div>
  </div>
  <!-- IF NOT LOADING -->
  <div v-else class="px-4">
    <div class="mb-4">
      <strong class="text-white">Select slide</strong>
      <select v-model="selectedSampleNameLocal" class="block w-full mt-1 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md">
        <option v-for="sample in samples" :value="sample.name">{{ sample.name }}</option>
      </select>
    </div>
    <!-- IF WINDOW NOT MINIMIZED -->
    <div v-if="!windowMinimal">
      <div class="mb-4">
        <strong class="text-white">Channels</strong>
        <div v-for="file in selectedSample.files" :key="file">
          <div class="mb-2 p-2 border rounded text-gray-800 bg-gray-200" v-if="ch[file] != 'empty'">
            <div class="flex items-center space-x-2 mb-2">
              <input v-model="ch_stain[file]" class="flex-grow p-1 border rounded" placeholder="Stain description">
              <button class="p-1" @click="removeStain(file)">
                <x-circle-icon class="icon" />
              </button>
            </div>
            <div class="flex items-center space-x-2">
              <select v-model="ch[file]" class="flex-grow p-1 border rounded" @change="settingsChanged">
                <option v-for="option in colorOptions" :value="option">{{ option }}</option>
              </select>
              <input type="range" v-model="gain[file]" max="10" min="0" step="1" class="flex-grow" @change="settingsChanged">
            </div>
          </div>
        </div>
      </div>

      <div class="mb-4">
        <strong class="text-white">Add channel</strong>
        <select v-model="addStainFileLocal" class="block w-full mt-1 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md" @change="addStain">
          <option v-for="option in stainOptions" :value="option.file">{{ option.stain }}</option>
        </select>
      </div>

      <div class="mb-4">
        <strong class="text-white">Annotations</strong>
        <div v-for="overlay in overlaysLocal" :key="overlay.number">
          <div class="mb-2 p-2 border rounded text-gray-800 bg-gray-200">
            <div class="flex items-center space-x-2">
              <p>{{ overlay.number }}</p>
              <input v-model="overlay.description" class="flex-grow p-1 border rounded" placeholder="Annotation" @change="reloadOverlays">
              <button class="p-1" @click="deleteOverlay(overlay.number)">
                <x-circle-icon class="icon" />
              </button>
            </div>
          </div>
        </div>
        <small class="text-white">* right click on slide to add annotation</small>
      </div>
    </div>
  </div>
</div>
<!-- END NAVIGATION -->
</div>
</template>

<script>
import OpenSeadragon from "openseadragon";
import { mapGetters, mapActions, mapState, mapMutations } from "vuex";

import { BeakerIcon, MinusCircleIcon, PlusCircleIcon, ArchiveBoxIcon, 
  XCircleIcon, ShareIcon } from '@heroicons/vue/24/solid'

export default {
  components: {
    BeakerIcon, 
    MinusCircleIcon,
    PlusCircleIcon,
    ArchiveBoxIcon,
    XCircleIcon,
    ShareIcon
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
    overlaysLocal: {
      get() {
        return this.overlays;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "overlays", value: value });
      },
    },
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
      for (let i = 0; i < this.overlaysLocal.length; i++) {
        this.addOverlay(this.overlaysLocal[i].location.x, this.overlaysLocal[i].location.y, this.overlaysLocal[i].number, this.overlaysLocal[i].description);
      }

    }, 
    overlaysLocal: function(newValue, oldValue) {
      console.log("overlays changed");
      this.reloadOverlays();
    },
  },
  methods: {
    ...mapActions(["loadSampleSheet", "loadSample", "reloadSlide", "saveDetails", "addStain", "removeStain", "deleteOverlay"]),
    ...mapMutations(["SET_STATE_PROPERTY"]),
    loadOpenSeaDragon() {
      this.viewer = new OpenSeadragon({
        id: "view",
        prefixUrl: "images/",
        timeout: 120000, //120000
        animationTime: 1, //0.5
        blendTime: 0.5, //0.1
        showRotationControl: true,
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

                this.overlaysLocal.push({
                  location: {
                    x: elementCoordiantes.x,
                    y: elementCoordiantes.y
                  },
                  description: "",
                  number: this.overlaysLocal.length > 0 ? this.overlaysLocal.map(overlay => overlay.number).sort((a, b) => a - b)[this.overlaysLocal.length - 1] + 1 : 1
                });

                console.log(this.overlaysLocal);

                //Add overlay, disabled for now
                this.addOverlay(elementCoordiantes.x, elementCoordiantes.y, this.overlaysLocal[this.overlaysLocal.length - 1].number, this.overlaysLocal[this.overlaysLocal.length - 1].description);
              },
            });
          });
        }
      });

      this.viewer.addHandler('open', () => {
        this.setBounds();
      });

    },

    reloadOverlays() {
      this.viewer.clearOverlays();
      for (let i = 0; i < this.overlaysLocal.length; i++) {
        this.addOverlay(this.overlaysLocal[i].location.x, this.overlaysLocal[i].location.y, this.overlaysLocal[i].number, this.overlaysLocal[i].description);
      }
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

    addOverlay(x, y, number, text = "") {
      const overlayElement = document.createElement("div");
      overlayElement.className = "overlay-" + number;

      const displayText = text || number;

      overlayElement.style.cssText = "display: flex; align-items: center; color: white;";
      overlayElement.innerHTML = `
        <span style="font-size: 1em; background-color: rgba(0, 0, 0, 0.5); padding: 4px; border-radius: 4px;">${displayText}</span>
        <span style="font-size: 2em; margin-left: 4px;">&rarr;</span>
      `;

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
  height: 100vh;
  width: 100vw;
}

.icon {
    width: 24px;
    height: 24px;
    color: #d8d8d8;
}

#navigation-menu {
  z-index: 1000;
  /* background-color: #2c3e50; */
  /* color: #ecf0f1; */
  /* padding: 10px; */
  /* border-radius: 4px; */
  position: fixed;
  top: 5vh;
  right: 1vw;
  /* box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); */
  width: 25vw;
  max-height: 90vh;
  overflow-y: auto;
  /* font-family: Arial, sans-serif; */
}
</style>