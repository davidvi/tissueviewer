<template>
 <div class="flex min-h-screen">

<!-- OVERLAY -->
<div id="right-arrow-overlay" hidden>
  <span class="text-2xl text-white">&rarr;</span>
</div>

<!-- VIEW -->
<div id="view" class="w-full h-full relative">
  <div v-if="!hasActiveChannels" id="viewEmpty" class="absolute inset-0 bg-black z-10"></div>
</div>

<!-- HUD -->
<div id="hud" class="fixed bottom-5 left-5 max-w-60 max-h-60 overflow-y-auto bg-black bg-opacity-70 p-2 rounded-md text-white" v-if="activatedSampleLocal && activatedSampleLocal.length > 1">
  <h3 class="text-lg font-semibold mb-2">Stains</h3>
  <div v-for="channel in activatedSampleLocal" :key="channel.channel_name" class="mb-2">
    <div v-if="channel.stain != 'empty'">
      <div class="flex items-center space-x-2">
        <div class="w-4 h-4 rounded-full" :style="{ backgroundColor: channel.stain }"></div>
        <p>{{ channel.channel_name }}</p>
      </div>
    </div>
  </div>
</div>
<!-- END HUD -->

<!-- MINIMIZED -->
<div id="minimized-menu" class="rounded text-gray-800 bg-gray-600" v-if="windowMinimal">
  <div class="flex p-4">
    <button class="p-2" @click="windowMinimal = !windowMinimal">
      <plus-circle-icon class="icon" />
    </button>
  </div>
</div>

<!-- END MINIMIZED -->

<!-- NAVIGATION -->
<div id="navigation-menu" class="rounded text-gray-800 bg-gray-600" v-if="!windowMinimal">
  <div class="flex items-center justify-between p-4">
    <div>
      <strong class="text-white">Settings</strong>
    </div>
    <div class="flex space-x-2">
      <button class="p-2" @click="copyLinkToClipboard">
        <share-icon class="icon" />
      </button>
      <button class="p-2" @click="saveDetails">
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
  <div class="px-4">
    <div class="mb-4">
      <strong class="text-white">Select collection</strong>
      <select v-model="locationLocal" class="block w-full mt-1 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md">
        <option v-for="location in locations" :value="location.key">{{ location.name }}</option>
      </select>
    </div>
  </div>

  <!-- IF LOADING -->
  <div v-if="!samples.length" class="p-4">
    <div class="flex justify-center">
      <strong class="text-white">Uh oh, no slides found</strong>
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
    <!-- <div v-if="!windowMinimal"> -->
      <!-- <div v-if="selectedSample.files.length > 1"> -->
        <div class="mb-4">
          <strong class="text-white">Channels</strong>
          <div v-for="channel in activatedSampleLocal" :key="channel.channel_number">
            <div class="mb-2 p-2 border rounded text-gray-800 bg-gray-200" v-if="channel.stain != 'empty'">
              <div class="flex items-center space-x-2 mb-2">
                <input v-model="channel.channel_name" class="flex-grow p-1 border rounded" placeholder="Stain description">
                <button class="p-1" @click="removeStain(channel.channel_number)">
                  <x-circle-icon class="icon" />
                </button>
              </div>
              <div class="flex items-center space-x-2">
                <select v-model="channel.stain" class="flex-grow p-1 border rounded" @change="settingsChanged">
                  <option v-for="option in colorOptions" :value="option">{{ option }}</option>
                </select>

                <input type="checkbox" v-model="channel.activated" @change="settingsChanged">

                <!-- <input type="range" v-model="channel.gain" max="5" min="0" step="0.01" class="flex-grow" @change="settingsChanged"> -->
                 
                <log-slider
                   :initial-gain="channel.gain"
                  v-model:gain="channel.gain"
                  @change="settingsChanged"
                />
              
              </div>
            </div>
          </div>
        </div>

        <div class="mb-4">
          <strong class="text-white">Add channel</strong>
          <select v-model="addStainFileLocal" class="block w-full mt-1 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md" @change="addStain">
            <option v-for="option in activatedSample" :value="option.channel_number">{{ option.channel_name }}</option>
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
        
        <!-- New Overlay File Upload Section -->
        <div class="mt-3 p-2 border rounded bg-gray-700">
          <div class="flex items-center justify-between mb-2">
            <span class="text-white">Import Overlays</span>
          </div>
          
          <div class="flex items-center space-x-2 mb-2">
            <input
              type="file"
              ref="fileInput"
              accept=".csv"
              class="hidden"
              @change="handleFileUpload"
            />
            <button 
              @click="$refs.fileInput.click()"
              class="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              Upload CSV
            </button>
            <span v-if="selectedFile" class="text-white text-sm truncate">
              {{ selectedFile.name }}
            </span>
          </div>
          
          <!-- Select overlay dropdown -->
          <div v-if="overlayFiles.length > 0">
            <select 
              v-model="selectedOverlayFile" 
              class="block w-full mt-1 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md"
              @change="loadSelectedOverlay"
            >
              <option value="">Select overlay file</option>
              <option v-for="overlayFile in overlayFiles" :key="overlayFile.id" :value="overlayFile.id">
                {{ overlayFile.name }}
              </option>
            </select>
          </div>
        </div>
      </div>
    <!-- </div> -->
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

import LogSlider from "../components/LogSlider.vue";

export default {
  components: {
    BeakerIcon, 
    MinusCircleIcon,
    PlusCircleIcon,
    ArchiveBoxIcon,
    XCircleIcon,
    ShareIcon,
    LogSlider,
  },
  data() {
    return {
      viewer: null,
      windowMinimal: false,
      locations: [{ name: "Examples", key: "public"}],
      selectedFile: null,
      overlayFiles: [],
      selectedOverlayFile: "",
      mouseTrackerInitialized: false,
    }
  },
  computed: {
    ...mapState(["samples", "selectedSample", "gain", "ch", "ch_stain", "overlays",
      "slideSettingsShown", "selectedSampleName", "currentSlide", "colorOptions", "description",
      "stainOptions", "addStainFile", "viewportCenter", "viewportZoom", "viewportBounds", 
      "saveEnabled", "activatedStains", "activatedSample", "location"]),

      hasActiveChannels() {
        return this.activatedSampleLocal.filter(sample => (sample.stain !== "empty" && sample.activated)).length > 0;
      },
      locationLocal: {
         get() {
           return this.location;
         },
         set(value) {
           this.SET_STATE_PROPERTY({ property: "location", value: value });
         },
       },
      activatedSampleLocal: {
        get() {
          return this.activatedSample;
        },
        set(value) {
          this.SET_STATE_PROPERTY({ property: "activatedSample", value: value });
        },
      },
      activatedStainsLocal: {
      get() {
        return this.activatedStains;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "activatedStains", value: value });
      },
    },
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
    locationLocal: function () {
      this.loadSampleSheet();
    },
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
    copyLinkToClipboard() {
      const link = `https://immunoviewer.org?location=${this.locationLocal}&sample=${this.selectedSampleName}`;
      navigator.clipboard.writeText(link).then(() => {
        alert('Link copied to clipboard!');
      }).catch(err => {
        console.error('Failed to copy link: ', err);
      });
    },
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

    handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;
      
      this.selectedFile = file;
      
      // Parse the CSV file
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const csvData = e.target.result;
          this.processCSV(csvData, file.name);
        } catch (error) {
          console.error("Error reading CSV file:", error);
          alert("There was an error reading the CSV file. Please check the format.");
        }
      };
      
      reader.readAsText(file);
    },
    
    processCSV(csvContent, fileName) {
      // Simple CSV parsing
      const lines = csvContent.split('\n');
      const headers = lines[0].split(',');
      
      // Expected headers: x, y, description (optional)
      const xIndex = headers.findIndex(h => h.toLowerCase().trim() === 'x');
      const yIndex = headers.findIndex(h => h.toLowerCase().trim() === 'y');
      const descIndex = headers.findIndex(h => h.toLowerCase().trim() === 'description');
      
      if (xIndex === -1 || yIndex === -1) {
        alert("CSV file must contain columns for 'x' and 'y' coordinates");
        return;
      }
      
      const overlayPoints = [];
      
      // Skip header row, process data rows
      for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue; // Skip empty lines
        
        const values = lines[i].split(',');
        const x = parseFloat(values[xIndex]);
        const y = parseFloat(values[yIndex]);
        const description = descIndex !== -1 ? values[descIndex] : "";
        
        if (!isNaN(x) && !isNaN(y)) {
          overlayPoints.push({
            location: {
              x: x,
              y: y
            },
            description: description || `Point ${i}`,
            number: i
          });
        }
      }
      
      // Add to overlay files list
      const newOverlayFile = {
        id: Date.now().toString(),
        name: fileName,
        data: overlayPoints
      };
      
      this.overlayFiles.push(newOverlayFile);
      this.selectedOverlayFile = newOverlayFile.id;
      this.loadSelectedOverlay();
    },
    
    loadSelectedOverlay() {
      if (!this.selectedOverlayFile) return;
      
      // Find the selected overlay file
      const overlay = this.overlayFiles.find(o => o.id === this.selectedOverlayFile);
      if (!overlay) return;
      
      // Replace existing overlays with new ones from the CSV
      this.overlaysLocal = overlay.data;
      
      // Reload overlays on the viewer
      this.reloadOverlays();
    },
  },
  mounted() {
    console.log("mounted");
    this.loadOpenSeaDragon();
    this.locationLocal = this.$route.query.location ? this.$route.query.location : "public";
    this.loadSampleSheet(this.$route.query.sample);

    // trigger reload of overlays when changing pages
    if(this.currentSlideLocal) {
      this.viewer.open(this.currentSlideLocal);
      for (let i = 0; i < this.overlaysLocal.length; i++) {
          this.addOverlay(this.overlaysLocal[i].location.x, this.overlaysLocal[i].location.y, this.overlaysLocal[i].number, this.overlaysLocal[i].description);
        }
    }
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

#hud {
  z-index: 1000;
}

#minimized-menu {
  z-index: 1000;
  position: fixed;
  top: 10vh;
  right: 1vw;
  width: 5vw;
  max-height: 10vh;
  overflow-y: auto;
}

#navigation-menu {
  z-index: 1000;
  position: fixed;
  top: 10vh;
  right: 1vw;
  width: 25vw;
  max-height: 90vh;
  overflow-y: auto;
}
</style>