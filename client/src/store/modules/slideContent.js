import axios from "axios";
import { baseUrl } from "../../lib/apiConnection";

/**
 * Adds a new stain (color) to the current state and reloads the slide.
 * @param {Object} context - Vuex context object.
 */
export const addStain = async ({ state, commit, dispatch }) => {
  console.log("adding color");
  // let bufStain = state.ch;
  // bufStain[state.addStainFile] = "red"; // Default color for new stain

  let bufActivatedSample = state.activatedSample;
  bufActivatedSample.filter(ch => ch.channel_number === state.addStainFile)[0].stain = "red";

  commit('SET_STATE_PROPERTY', { property: "activatedSample", value: bufActivatedSample });
  dispatch('reloadSlide');
  commit('SET_STATE_PROPERTY', { property: "addStainFile", value: "" });
}

/**
 * Loads the sample sheet from the server and updates the state with sample data.
 * @param {Object} context - Vuex context object.
 * @param {string} sample - Optional sample name to select initially.
 */
export const loadSampleSheet = async ({ commit, state }, sample) => {
  console.log("received sample: ", sample);
  console.log("received location: ", state.location);
  const axiosRequest = `${baseUrl}/samples.json?location=${state.location == "public" ? "public" : (state.userProfile && state.userProfile.uid ? state.userProfile.uid : "noid")}`; 
  console.log("axios request: ", axiosRequest);
  axios.get(axiosRequest)
    .then(response => {
      console.log("sample sheet: ", response.data.samples);
      commit('SET_STATE_PROPERTY', { property: "samples", value: response.data.samples });
      commit('SET_STATE_PROPERTY', { property: "saveEnabled", value: response.data.save });
      commit('SET_STATE_PROPERTY', { property: "colorOptions", value: response.data.colors });
      commit('SET_STATE_PROPERTY', { property: "selectedSampleName", value: sample ? sample : response.data.samples[0].name });
      commit('SET_STATE_PROPERTY', { property: "selectedSampleFolder", value: response.data.samples[0].details.folder ? response.data.samples[0].details.folder : "" });
    })
}

/**
 * Saves the current details of the selected sample to the server.
 * @param {Object} context - Vuex context object.
 */
export const saveDetails = async ({ state, commit }) => {
  let data = {
    channelsSetting: state.activatedSample,
    description: state.description,
    overlays: state.overlays,
    altName: state.selectedSampleAltName,
    folder: state.selectedSampleFolder,
  }

  const location = state.location == "public" ? "public" : (state.userProfile && state.userProfile.uid ? state.userProfile.uid : "noid");

  let bufSamples = state.samples;
  bufSamples.filter(s => s.name === state.selectedSample.name)[0].details = data;

  console.log("buf samples: ", bufSamples);

  commit('SET_STATE_PROPERTY', { property: "samples", value: bufSamples });

  console.log("saving details: ", data);

  axios.post(`${baseUrl}/save/${location}/${state.selectedSample.name}`, data)
    .then(response => {
      console.log(response);
    })
}

/**
 * Saves only the channel settings without affecting folder or other details.
 * @param {Object} context - Vuex context object.
 */
export const saveChannels = async ({ state, commit }) => {
  // Get the current sample's existing details to preserve folder and other settings
  let selectedSampleBuf = state.samples.filter(s => s.name === state.selectedSample.name)[0];
  
  let data = {
    channelsSetting: state.activatedSample,
    description: selectedSampleBuf.details.description || state.description,
    overlays: selectedSampleBuf.details.overlays || state.overlays,
    altName: selectedSampleBuf.details.altName || state.selectedSampleAltName,
    folder: selectedSampleBuf.details.folder || "", // Preserve existing folder
  }

  const location = state.location == "public" ? "public" : (state.userProfile && state.userProfile.uid ? state.userProfile.uid : "noid");

  let bufSamples = state.samples;
  bufSamples.filter(s => s.name === state.selectedSample.name)[0].details = data;

  console.log("buf samples: ", bufSamples);

  commit('SET_STATE_PROPERTY', { property: "samples", value: bufSamples });

  console.log("saving channels: ", data);

  axios.post(`${baseUrl}/save/${location}/${state.selectedSample.name}`, data)
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
  let bufActivatedSample = state.activatedSample;
  bufActivatedSample.filter(ch => ch.channel_number === file)[0].stain = "empty";
  commit('SET_STATE_PROPERTY', { property: "activatedSample", value: bufActivatedSample });
  dispatch('reloadSlide');
}

/**
 * Reloads the slide with the current stain and gain settings.
 * @param {Object} context - Vuex context object.
 */
export const reloadSlide = async ({ state, commit }) => {

  const chList = [];
  const gainList = [];
  const stainList = [];
  const minList = [];
  const maxList = [];

  console.log("activated sample: ", state.activatedSample);

  state.activatedSample.forEach((ch) => {
    if(ch.stain != "empty" && ch.activated) {
      stainList.push(`${ch.stain}`);
      gainList.push(`${ch.gain}`);
      chList.push(`${ch.channel_number}`);
      minList.push(ch.low != null ? ch.low : 0.0);
      maxList.push(ch.high != null ? ch.high : 1.0);
    }
  });

  const chString = chList.join(";");
  const gainString = gainList.join(";");
  const stainString = stainList.join(";");
  const minString = minList.join(";");
  const maxString = maxList.join(";");

  const location = state.location == "public" ? "public" : (state.userProfile && state.userProfile.uid ? state.userProfile.uid : "noid");

  let currentSlide = `${baseUrl}/${location}/${chString}/${state.currentSampleIsRGB}/${stainString}/${gainString}/${minString}/${maxString}/${state.selectedSample.name}.dzi`;

  commit('SET_STATE_PROPERTY', { property: "currentSlide", value: currentSlide });

  console.log("setting current slide: ", currentSlide);
}

/**
 * Copies the settings from another slide to the current slide.
 * @param {Object} context - Vuex context object.
 */
export const copySettings = async ({ state, commit, dispatch }, sample) => {
  console.log("copying settings from: ", sample);
  let selectedSampleBuf = state.samples.filter(s => s.name === sample)[0];
  console.log("selected sample buf: ", selectedSampleBuf);
  console.log("activated sample: ", state.activatedSample);
  commit('SET_STATE_PROPERTY', { property: "activatedSample", value: selectedSampleBuf.details.channelsSetting });
}

/**
 * Loads the selected sample from the state and updates the relevant details.
 * @param {Object} context - Vuex context object.
 */
export const loadSample = async ({ state, commit, dispatch }) => {
  let selectedSampleBuf = state.samples.filter(s => s.name === state.selectedSampleName)[0];
  commit('SET_STATE_PROPERTY', { property: "selectedSample", value: selectedSampleBuf });

  console.log("selected sample: ", selectedSampleBuf);

  console.log("selected sample alt name: ", state.selectedSampleAltName);

  let activatedSample = [];
  if(!selectedSampleBuf.details.channelsSetting) {
    selectedSampleBuf.metadata[0].channel_info.forEach((ch, index) => {
      const channelInfo = {
        channel_name: ch.channel_name ? ch.channel_name : index,
        channel_number: index,
        gain: selectedSampleBuf.details.gain && selectedSampleBuf.details.gain[index] ? selectedSampleBuf.details.gain[index] : 1,
        stain : selectedSampleBuf.details.ch_stain && selectedSampleBuf.details.ch_stain[index] ? selectedSampleBuf.details.ch_stain[index] : "empty",
        activated: true,
        low: 0.0,
        high: 1.0,
      }
      activatedSample.push(channelInfo);
    });
  } else {
    activatedSample = selectedSampleBuf.details.channelsSetting.map(ch => ({
      low: 0.0,
      high: 1.0,
      ...ch,
    }));
  }

  console.log("activatedSample: ", activatedSample);

  commit('SET_STATE_PROPERTY', { property: "activatedSample", value: activatedSample });
  commit('SET_STATE_PROPERTY', { property: "description", value: selectedSampleBuf.details.description ? selectedSampleBuf.details.description : "" });
  commit('SET_STATE_PROPERTY', { property: "selectedSampleAltName", value: selectedSampleBuf.details.altName ? selectedSampleBuf.details.altName : selectedSampleBuf.name });
  commit('SET_STATE_PROPERTY', { property: "overlays", value: selectedSampleBuf.details.overlays ? selectedSampleBuf.details.overlays : [] });
  dispatch('reloadSlide');
}