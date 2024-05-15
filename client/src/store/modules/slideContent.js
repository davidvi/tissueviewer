import axios from "axios";

const baseUrl = process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000";

/**
 * Adds a new stain (color) to the current state and reloads the slide.
 * @param {Object} context - Vuex context object.
 */
export const addStain = async ({ state, commit, dispatch }) => {
  console.log("adding color");
  let bufStain = state.ch;
  bufStain[state.addStainFile] = "red"; // Default color for new stain
  commit('SET_STATE_PROPERTY', { property: "ch", value: bufStain });
  dispatch('reloadSlide');
  commit('SET_STATE_PROPERTY', { property: "addStainFile", value: "" });
}

/**
 * Loads the sample sheet from the server and updates the state with sample data.
 * @param {Object} context - Vuex context object.
 * @param {string} sample - Optional sample name to select initially.
 */
export const loadSampleSheet = async ({ commit }, sample) => {
  axios.get(`${baseUrl}/samples.json`)
    .then(response => {
      console.log("sample sheet: ", response.data.samples);
      commit('SET_STATE_PROPERTY', { property: "samples", value: response.data.samples });
      commit('SET_STATE_PROPERTY', { property: "saveEnabled", value: response.data.save });
      commit('SET_STATE_PROPERTY', { property: "colorOptions", value: response.data.colors });
      commit('SET_STATE_PROPERTY', { property: "selectedSampleName", value: sample ? sample : response.data.samples[0].name });
    })
}

/**
 * Saves the current details of the selected sample to the server.
 * @param {Object} context - Vuex context object.
 */
export const saveDetails = async ({ state, commit }) => {
  let data = {
    ch: state.ch,
    gain: state.gain,
    ch_stain: state.ch_stain,
    description: state.description,
    overlays: state.overlays,
  }

  let bufSamples = state.samples;
  bufSamples.filter(s => s.name === state.selectedSample.name)[0].details = data;
  commit('SET_STATE_PROPERTY', { property: "samples", value: bufSamples });

  axios.post(`${baseUrl}/save/${state.selectedSample.name}`, data)
    .then(response => {
      console.log(response);
    })
}

/**
 * Deletes an overlay from the current state.
 * @param {Object} context - Vuex context object.
 * @param {number} index - The index of the overlay to delete.
 */
export const deleteOverlay = async ({ state, commit, dispatch }, index) => {
  console.log("removing overlay: ", index)

  let bufOverlays = state.overlays;

  // Remove the overlay with the specified index
  bufOverlays = bufOverlays.filter(overlay => overlay.number !== index);

  console.log("new overlays: ", bufOverlays)

  commit('SET_STATE_PROPERTY', { property: "overlays", value: bufOverlays });
}

/**
 * Removes a stain (color) from the current state and reloads the slide.
 * @param {Object} context - Vuex context object.
 * @param {string} file - The file name of the stain to remove.
 */
export const removeStain = async ({ state, commit, dispatch }, file) => {
  let bufStain = state.ch;
  bufStain[file] = "empty"; // Mark the stain as empty
  commit('SET_STATE_PROPERTY', { property: "ch", value: bufStain });

  dispatch('reloadSlide');
}

/**
 * Reloads the slide with the current stain and gain settings.
 * @param {Object} context - Vuex context object.
 */
export const reloadSlide = async ({ state, commit }) => {
  const chString = state.selectedSample.files.map((file) => {
    return state.ch[file] ? state.ch[file] : "empty";
  }).join(";");

  const gainString = state.selectedSample.files.map((file) => {
    return state.gain[file] ? state.gain[file] : "0";
  }).join(";");

  const filesString = state.selectedSample.files.join(";");

  let currentSlide = `${baseUrl}/${filesString}/${chString}/${gainString}/${state.selectedSample.name}.dzi`;

  commit('SET_STATE_PROPERTY', { property: "currentSlide", value: currentSlide });

  console.log("setting current slide: ", currentSlide);
}

/**
 * Loads the selected sample from the state and updates the relevant details.
 * @param {Object} context - Vuex context object.
 */
export const loadSample = async ({ state, commit, dispatch }) => {
  let selectedSampleBuf = state.samples.filter(s => s.name === state.selectedSampleName)[0];
  commit('SET_STATE_PROPERTY', { property: "selectedSample", value: selectedSampleBuf });

  console.log("selected sample: ", selectedSampleBuf);

  commit('SET_STATE_PROPERTY', { property: "ch", value: selectedSampleBuf.details.ch ? selectedSampleBuf.details.ch : {} });
  commit('SET_STATE_PROPERTY', { property: "gain", value: selectedSampleBuf.details.gain ? selectedSampleBuf.details.gain : {} });
  commit('SET_STATE_PROPERTY', { property: "ch_stain", value: selectedSampleBuf.details.ch_stain ? selectedSampleBuf.details.ch_stain : {} });
  commit('SET_STATE_PROPERTY', { property: "description", value: selectedSampleBuf.details.description ? selectedSampleBuf.details.description : "" });
  commit('SET_STATE_PROPERTY', { property: "overlays", value: selectedSampleBuf.details.overlays ? selectedSampleBuf.details.overlays : [] });

  dispatch('reloadSlide');
}
