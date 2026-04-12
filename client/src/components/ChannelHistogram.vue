<template>
  <div ref="container" class="channel-histogram w-full">
    <div v-if="loading" class="text-xs text-gray-400 py-2">Loading...</div>
    <template v-else>
      <svg
        ref="svg"
        :width="svgWidth"
        :height="svgHeight"
        class="block select-none"
        style="cursor: crosshair"
        @mousemove.prevent="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
      >
        <!-- histogram bars -->
        <rect
          v-for="(count, i) in bins"
          :key="i"
          :x="i * barWidth"
          :y="svgHeight - barHeightFor(count)"
          :width="Math.max(barWidth - 0.5, 1)"
          :height="barHeightFor(count)"
          :fill="displayColor"
          opacity="0.75"
        />

        <!-- dim region left of low handle -->
        <rect x="0" y="0" :width="lowPx" :height="svgHeight" fill="black" opacity="0.55" style="pointer-events:none" />
        <!-- dim region right of high handle -->
        <rect :x="highPx" y="0" :width="svgWidth - highPx" :height="svgHeight" fill="black" opacity="0.55" style="pointer-events:none" />

        <!-- low handle line -->
        <line
          :x1="lowPx" y1="0" :x2="lowPx" :y2="svgHeight"
          stroke="white" stroke-width="2"
          style="cursor: ew-resize"
          @mousedown.prevent.stop="startDrag('low', $event)"
        />
        <circle
          :cx="lowPx" :cy="svgHeight * 0.5" r="5"
          fill="white" stroke="#374151" stroke-width="1.5"
          style="cursor: ew-resize"
          @mousedown.prevent.stop="startDrag('low', $event)"
        />

        <!-- high handle line -->
        <line
          :x1="highPx" y1="0" :x2="highPx" :y2="svgHeight"
          stroke="white" stroke-width="2"
          style="cursor: ew-resize"
          @mousedown.prevent.stop="startDrag('high', $event)"
        />
        <circle
          :cx="highPx" :cy="svgHeight * 0.5" r="5"
          fill="white" stroke="#374151" stroke-width="1.5"
          style="cursor: ew-resize"
          @mousedown.prevent.stop="startDrag('high', $event)"
        />
      </svg>

      <!-- numeric labels -->
      <div class="flex justify-between text-xs text-gray-400 mt-0.5 px-0.5">
        <span>{{ (lowValue * 100).toFixed(0) }}%</span>
        <span>{{ (highValue * 100).toFixed(0) }}%</span>
      </div>
    </template>
  </div>
</template>

<script>
import axios from 'axios';
import { baseUrl } from '../lib/apiConnection';

const NUM_BINS = 64;
const SVG_HEIGHT = 56;

const COLOR_MAP = {
  red: '#ef4444',
  green: '#22c55e',
  blue: '#3b82f6',
  yellow: '#eab308',
  magenta: '#d946ef',
  cyan: '#06b6d4',
  white: '#d1d5db',
};

export default {
  name: 'ChannelHistogram',
  props: {
    channelNumber: { type: Number, required: true },
    channelColor: { type: String, default: 'white' },
    low: { type: Number, default: 0.0 },
    high: { type: Number, default: 1.0 },
  },
  emits: ['update:low', 'update:high', 'change'],
  data() {
    return {
      bins: new Array(NUM_BINS).fill(0),
      loading: true,
      svgWidth: 200,
      svgHeight: SVG_HEIGHT,
      dragging: null,
      dragSvgRect: null,
    };
  },
  computed: {
    lowValue() { return this.low ?? 0.0; },
    highValue() { return this.high ?? 1.0; },
    lowPx() { return this.lowValue * this.svgWidth; },
    highPx() { return this.highValue * this.svgWidth; },
    barWidth() { return this.svgWidth / NUM_BINS; },
    maxCount() { return Math.max(...this.bins, 1); },
    displayColor() { return COLOR_MAP[this.channelColor] || '#d1d5db'; },
    storeLocation() {
      const loc = this.$store.state.location;
      const uid = this.$store.state.userProfile?.uid;
      return loc === 'public' ? 'public' : (uid || 'noid');
    },
    storeSampleName() {
      return this.$store.state.selectedSample?.name;
    },
  },
  methods: {
    barHeightFor(count) {
      if (count === 0) return 0;
      return Math.max(2, (Math.log(count + 1) / Math.log(this.maxCount + 1)) * this.svgHeight);
    },
    async fetchHistogram() {
      if (!this.storeSampleName) return;
      this.loading = true;
      try {
        // Fetch DZI XML to get image dimensions
        const dziUrl = `${baseUrl}/${this.storeLocation}/${this.channelNumber}/false/white/1.0/0.0/1.0/${this.storeSampleName}.dzi`;
        const dziResp = await axios.get(dziUrl);

        // Parse width/height to choose a small level for sampling
        const parser = new DOMParser();
        const doc = parser.parseFromString(dziResp.data, 'application/xml');
        const sizeEl = doc.querySelector('Size');
        const w = parseInt(sizeEl?.getAttribute('Width') || '1024');
        const h = parseInt(sizeEl?.getAttribute('Height') || '1024');
        const maxLevel = Math.ceil(Math.log2(Math.max(w, h)));
        // Target ~256px coverage: go 8 levels below max
        const targetLevel = Math.max(0, maxLevel - 8);

        // Fetch the overview tile (top-left, covers whole image at low res)
        const tileUrl = `${baseUrl}/${this.storeLocation}/${this.channelNumber}/false/white/1.0/0.0/1.0/${this.storeSampleName}_files/${targetLevel}/0_0.jpeg`;
        const tileResp = await axios.get(tileUrl, { responseType: 'blob' });

        // Draw on offscreen canvas and read pixel data
        const img = new Image();
        const blobUrl = URL.createObjectURL(tileResp.data);
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
          img.src = blobUrl;
        });
        URL.revokeObjectURL(blobUrl);

        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        canvas.getContext('2d').drawImage(img, 0, 0);
        const { data } = canvas.getContext('2d').getImageData(0, 0, img.width, img.height);

        // Count pixels into bins (use R channel — grayscale white rendering means R=G=B)
        const counts = new Array(NUM_BINS).fill(0);
        for (let i = 0; i < data.length; i += 4) {
          const bin = Math.min(NUM_BINS - 1, Math.floor((data[i] / 255) * NUM_BINS));
          counts[bin]++;
        }
        this.bins = counts;
      } catch (e) {
        console.error('ChannelHistogram: fetch failed', e);
        this.bins = new Array(NUM_BINS).fill(1);
      } finally {
        this.loading = false;
      }
    },
    startDrag(handle, event) {
      this.dragging = handle;
      this.dragSvgRect = this.$refs.svg.getBoundingClientRect();
    },
    onMouseMove(event) {
      if (!this.dragging || !this.dragSvgRect) return;
      const fraction = Math.max(0, Math.min(1, (event.clientX - this.dragSvgRect.left) / this.svgWidth));
      if (this.dragging === 'low') {
        const clamped = Math.min(fraction, this.highValue - 0.02);
        this.$emit('update:low', +clamped.toFixed(4));
        this.$emit('change');
      } else {
        const clamped = Math.max(fraction, this.lowValue + 0.02);
        this.$emit('update:high', +clamped.toFixed(4));
        this.$emit('change');
      }
    },
    onMouseUp() {
      this.dragging = null;
      this.dragSvgRect = null;
    },
    updateWidth() {
      if (this.$refs.container) {
        const w = this.$refs.container.clientWidth;
        if (w > 0) this.svgWidth = w;
      }
    },
  },
  mounted() {
    this.$nextTick(() => {
      this.updateWidth();
      this.fetchHistogram();
    });
  },
  watch: {
    storeSampleName() { this.fetchHistogram(); },
    channelNumber() { this.fetchHistogram(); },
  },
};
</script>
