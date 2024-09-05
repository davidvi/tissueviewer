import axios from 'axios';
import { baseUrl } from "../../lib/apiConnection";

export const uploadSlide = async({state, commit}) => {
  if (!state.file) {
    console.log('No file selected');
    return;
  }

  const chunkSize = 50 * 1024 * 1024; // 50MB chunk size
  const fileSize = state.file.size;
  const totalChunks = Math.ceil(fileSize / chunkSize);

  commit('SET_STATE_PROPERTY', { property: 'progressTotalChunks', value: totalChunks });

  for (let chunk = 0; chunk < totalChunks; chunk++) {

    console.log(`Uploading chunk ${chunk + 1}/${totalChunks}`);

    commit('SET_STATE_PROPERTY', { property: 'progressChunk', value: chunk + 1 });

    const start = chunk * chunkSize;
    const end = Math.min(start + chunkSize, fileSize);
    const fileChunk = state.file.slice(start, end);

    const formData = new FormData();
    formData.append('file', fileChunk);
    formData.append("name", state.file.name);
    formData.append("chunk_number", String(chunk));
    formData.append("total_chunks",String(totalChunks));

    console.log('form data', formData);

    try {
      await axios.post(`${baseUrl}/uploadSample`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      console.log(`Chunk ${chunk + 1}/${totalChunks} uploaded`);
    } catch (error) {
      console.error(`Error uploading chunk ${chunk + 1}`, error);
      return;
    }
  }

  console.log('File uploaded successfully');
  commit('SET_STATE_PROPERTY', { property: 'progressChunk', value: 0 });
  commit('SET_STATE_PROPERTY', { property: 'progressTotalChunks', value: 0 });
  commit('SET_STATE_PROPERTY', { property: 'file', value: null });
}