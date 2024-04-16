<template>
    <v-app>
      <v-app-bar color="primary">
        <v-btn @click="slideSettingsShownLocal = !slideSettingsShownLocal">{{ slideSettingsShownLocal ? 'hide settings' : 'show settings'
        }}</v-btn>
        <v-btn @click="saveDetails">Save settings</v-btn>
        <v-btn @click="reloadSlide">Reload slide</v-btn>
        <v-select :items="samples" v-model="selectedSampleNameLocal" label="Select slide" item-value="name"
          item-title="name"></v-select>
          <v-spacer></v-spacer>
          <span>right click on image to add annotation</span>
      </v-app-bar>
      <v-navigation-drawer v-model="slideSettingsShownLocal" app temporary width="250">
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

                        <p>gain: {{ gain[file] }}</p>
                        <v-slider v-model="gain[file]" :max="10" :min="1" :step="1" default="1"></v-slider>
                        <p>color</p>
                        <v-select v-model="ch[file]" :items="colorOptions" default="empty"></v-select>
                        <p>stain description</p>
                        <v-text-field v-model="ch_stain[file]" label="Stain description"></v-text-field>
                    <v-divider></v-divider>

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

                        <p>annotation description</p>
                        <v-text-field v-model="overlay[index]" label="Annotation description"></v-text-field>
                        <v-btn color="warning" @click="deleteOverlay(index)">Delete</v-btn>
                    <v-divider></v-divider>

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
        "slideSettingsShown", "selectedSampleName", "currentSlide", "colorOptions", "description"]),
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
      ...mapActions(["loadSampleSheet", "loadSample", "reloadSlide", "saveDetails"]),
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