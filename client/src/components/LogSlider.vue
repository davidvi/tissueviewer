<template>
  <div>
    <input
      type="range"
      v-model="sliderValue"
      :min="0"
      :max="100"
      step="1"
      class="flex-grow"
      @input="updateGain"
    />
    <span>Gain: {{ formattedGain }}</span>
  </div>
</template>

<script>
export default {
  props: {
    initialGain: {
      type: Number,
      default: 1
    }
  },
  data() {
    return {
      sliderValue: 0, // Will be set in created hook
    };
  },
  computed: {
    gain() {
      return Number((Math.pow(10, this.sliderValue / 100 * 2.699) / 100).toFixed(3));
    },
    formattedGain() {
      return this.gain.toFixed(3);
    },
  },
  methods: {
    updateGain() {
      this.$emit('update:gain', this.gain);
      this.$emit('change');
    },
    setGainFromOutside(newGain) {
      this.sliderValue = Math.round((Math.log10(newGain * 100) / 2.699) * 100);
    },
  },
  created() {
    // Initialize the slider value based on the initial gain
    this.setGainFromOutside(this.initialGain);
  },
  watch: {
    initialGain(newValue) {
      this.setGainFromOutside(newValue);
    }
  }
};
</script>