import axios from "axios";
import { baseUrl } from "../../lib/apiConnection";

export const getSampleStats = async ({ commit, state }) => {

  const axiosRequest = `${baseUrl}/sampleStats`;

  try {
    const response = await axios.post(axiosRequest);
    console.log(response.data);
    commit('SET_STATE_PROPERTY', { property: 'userFiles', value: response.data.samples });
    commit('SET_STATE_PROPERTY', { property: 'dataUsed', value: response.data.dataUsed });
  } catch (error) {
    console.error('Error fetching sample stats:', error);
  }
};

export const deleteSample = async ({ state, dispatch }, sample) => {
  try {
    const response = await axios.post(`${baseUrl}/deleteSample`, { sample});
    console.log(response.data);
    dispatch('getSampleStats');
  } catch (error) {
    console.error('Error deleting sample:', error);
  }
}