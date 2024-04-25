import { computed, createApp } from 'vue';
import { createStore } from 'vuex';
import axios from "axios";

const baseUrl = process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000";

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
        addStain({state, commit, dispatch}) {
            console.log("adding color");
            let bufStain = state.ch;
            bufStain[state.addStainFile] = "red";
            commit('SET_STATE_PROPERTY', { property:"ch", value: bufStain });
            dispatch('reloadSlide');
            commit('SET_STATE_PROPERTY', { property:"addStainFile", value: "" });
        },
        loadSampleSheet({ commit }) {
            axios.get(`${baseUrl}/samples.json`)
                .then(response => {
                    console.log("sample sheet: ", response.data.samples);
                    commit('SET_STATE_PROPERTY', { property:"samples", value: response.data.samples });
                    commit('SET_STATE_PROPERTY', { property:"saveEnabled", value: response.data.save });
                    commit('SET_STATE_PROPERTY', { property:"colorOptions", value: response.data.colors });
                    commit('SET_STATE_PROPERTY', { property:"selectedSampleName", value: response.data.samples[0].name });
                })
        },

        saveDetails({state, commit}) {
            let data = {
                ch: state.ch,
                gain: state.gain,
                ch_stain: state.ch_stain,
                description: state.description,
                overlays: state.overlays,
            }

            let bufSamples = state.samples;
            bufSamples.filter(s => s.name === state.selectedSample.name)[0].details = data;
            commit('SET_STATE_PROPERTY', { property:"samples", value: bufSamples });

            axios.post(`${baseUrl}/save/${state.selectedSample.name}`, data)
                .then(response => {
                    console.log(response);
                })
        },

        deleteOverlay({state, commit, dispatch}, index) {
            let bufOverlays = state.overlays;
            bufOverlays.splice(index, 1);
            commit('SET_STATE_PROPERTY', { property:"overlays", value: bufOverlays });

            dispatch('reloadSlide');
        },

        removeStain({state, commit, dispatch}, file) {
            let bufStain = state.ch;
            bufStain[file] = "empty";
            commit('SET_STATE_PROPERTY', { property:"ch", value: bufStain });

            dispatch('reloadSlide');
        },

        reloadSlide({state, commit}) {

            const chString = state.selectedSample.files.map((file) => {
                return state.ch[file] ? state.ch[file] : "empty";
            }).join(";");

            const gainString = state.selectedSample.files.map((file) => {
                return state.gain[file] ? state.gain[file] : "0";
            }).join(";");

            const filesString = state.selectedSample.files.join(";");

            let currentSlide = `${baseUrl}/${filesString}/${chString}/${gainString}/${state.selectedSample.name}.dzi`;

            commit('SET_STATE_PROPERTY', { property:"currentSlide", value: currentSlide });

            console.log("setting current slide: ", currentSlide);            
        },

        loadSample({state, commit, dispatch}) {
            let selectedSampleBuf = state.samples.filter(s => s.name === state.selectedSampleName)[0];
            commit('SET_STATE_PROPERTY', { property:"selectedSample", value: selectedSampleBuf });

            console.log("selected sample: ", selectedSampleBuf);

            commit('SET_STATE_PROPERTY', { property:"ch", value: selectedSampleBuf.details.ch ? selectedSampleBuf.details.ch : {} });
            commit('SET_STATE_PROPERTY', { property:"gain", value: selectedSampleBuf.details.gain ? selectedSampleBuf.details.gain : {} });
            commit('SET_STATE_PROPERTY', { property:"ch_stain", value: selectedSampleBuf.details.ch_stain ? selectedSampleBuf.details.ch_stain : {} });
            commit('SET_STATE_PROPERTY', { property:"description", value: selectedSampleBuf.details.description ? selectedSampleBuf.details.description : "" });
            commit('SET_STATE_PROPERTY', { property:"overlays", value: selectedSampleBuf.details.overlays ? selectedSampleBuf.details.overlays : [] });

            dispatch('reloadSlide');
        }


    }
})

export default store;