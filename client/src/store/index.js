import { createStore } from 'vuex';
import * as slideContent from "./modules/slideContent";
import * as uploadSlide from "./modules/uploadSlide";
import * as manageFiles from "./modules/manageFiles";

const store = createStore({
    state() {
        return {
            // slide variables
            selectedSample: {},
            selectedSampleName: "",
            samples: [],
            ch: {},
            ch_stain: {},
            gain: {},
            description: "",
            slideSettingsShown: false,
            overlays: [],
            currentSlide: null, 
            colorOptions: [],
            addStainFile: "", 
            viewportCenter: {x: 0.5, y: 0.5},
            viewportZoom: 1,
            viewportBounds: null, 
            saveEnabled: false,
            userProfile: null,
            location: "public",
            activatedStains: {},

            // upload variables
            file: null,
            progressChunk: 0,
            progressTotalChunks: 0, 

            // file management variables
            userFiles: [],
            dataUsed: 0,
        }
    },
    mutations: {
        SET_STATE_PROPERTY(state, { property, value }) {
            if (state.hasOwnProperty(property)) {
                state[property] = value;
            }
        },
    },
    actions: {
        ...slideContent,
        ...uploadSlide,
        ...manageFiles,
    }
})

export default store;