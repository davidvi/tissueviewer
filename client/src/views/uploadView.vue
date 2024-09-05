<template>
  <div class="container mx-auto p-4 flex">
    <!-- Left side: List of files -->
    <div class="w-1/2 pr-4">
      <h2 class="text-xl font-semibold mb-4">Manage files</h2>
      <ul class="p-4 grid grid-cols-3 gap-4">
          <li v-for="(file, index) in userFilesLocal" :key="index" class="flex items-center border p-2 rounded-md shadow-sm">
              <div class="w-full flex justify-between items-center">
                  <p>{{ file }}</p>
                  <button @click="deleteFileLocal(file, index)" class="text-red-500 hover:text-red-700 ml-4">x</button>
              </div>
          </li>
      </ul>
    </div>

    <!-- Right side: Upload function -->
    <div class="w-1/2 pl-4">
      <h2 class="text-xl font-semibold mb-4">Upload new file</h2>
      <p class="mb-4">Please upload only bioformats compatible files.</p>
      <p><b>Note: After uploading, it may take some time for the image to be processed and appear. Please be patient!</b></p>
      <br />
      <div v-if="!isUploading">
        <input type="file" @change="onFileChange" />
        <button @click="uploadSlideLocal" class="mt-2 px-4 py-2 bg-blue-500 text-white font-semibold rounded-lg shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75">
          Upload
        </button>
      </div>
      <div v-else>
        <progress :value="progressChunk" :max="progressTotalChunks" class="w-full h-4 mt-2"></progress>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters, mapActions, mapState, mapMutations } from "vuex";

export default {
  data() {
    return {
      uploadedFiles: [],
      isUploading: false,
    };
  },
  computed: {
    ...mapState(["userFiles", "progressChunk", "progressTotalChunks", "files", "dataUsed", "samples", "file"]),
    userFilesLocal: {
      get() {
        return this.userFiles;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "userFiles", value: value });
      },
    },
    fileLocal: {
      get() {
        return this.file;
      },
      set(value) {
        this.SET_STATE_PROPERTY({ property: "file", value: value });
      },
    },
  },
  methods: {
    ...mapActions(["uploadSlide", "getSampleStats", "deleteSample", "uploadSlide"]),
    ...mapMutations(["SET_STATE_PROPERTY"]),

    deleteFileLocal(file, index) {
      // Ask the user for confirmation
      if (confirm(`Are you sure you want to delete the file: ${file}?`)) {
        // If the user confirms, delete the file
        this.deleteSample(file);
        this.userFilesLocal.splice(index, 1);

      } else {
        // If the user cancels, do nothing
        console.log('File deletion cancelled.');
      }
    },

    onFileChange(event) { 
      const file = event.target.files[0];
      const allowedExtensions = ['svs', 'tiff', 'tif'];
      const fileExtension = file.name.split('.').pop().toLowerCase();
      if (allowedExtensions.includes(fileExtension)) {
        this.fileLocal = file;
        console.log('Selected file:', this.fileLocal);
      } else {
        alert('Invalid file type. Please upload only bioformats compatible files.');
        event.target.value = ''; // Clear the file input
      }
    },

    uploadSlideLocal() {
      if (this.fileLocal) {
        console.log('Uploading file:', this.fileLocal);

        this.isUploading = true;

        this.uploadSlide(this.fileLocal).then(() => {
          this.userFilesLocal = null;
          this.getSampleStats();
          this.isUploading = false;
        });
      }
    },
  },
  mounted() {
    this.getSampleStats();
  },
};
</script>

<style>
.container {
  max-width: 800px;
}
</style>