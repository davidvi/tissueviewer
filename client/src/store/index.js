import { createStore } from 'vuex';
import * as slideContent from "./modules/slideContent";

const store = createStore({
    state() {
        return {
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
    }
})

export default store;