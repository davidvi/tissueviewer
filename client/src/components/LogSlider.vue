<template>
  <div class="flex items-center space-x-2">
    <input
      type="range"
      v-model="sliderValue"
      :min="0"
      :max="100"
      step="1"
      class="flex-grow h-2 bg-gray-300 rounded-lg appearance-none cursor-pointer slider"
      @input="updateGain"
    />
    <!-- Display the current intensity value -->
    <span class="text-xs font-mono bg-gray-100 px-2 py-1 rounded border min-w-[3rem] text-center text-gray-800">
      {{ formattedGain }}
    </span>
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
      // Enhanced logarithmic scaling to allow much lower values
      // Scale goes from 0.001 to 5 (instead of 0.01 to 5)
      // Using log scale: 10^(slider_position * range + min_exponent)
      const minExponent = -3; // 10^-3 = 0.001
      const maxExponent = 0.699; // 10^0.699 ≈ 5
      const range = maxExponent - minExponent;
      const exponent = minExponent + (this.sliderValue / 100) * range;
      return Number(Math.pow(10, exponent).toFixed(6));
    },
    formattedGain() {
      // Smart formatting based on value magnitude
      if (this.gain >= 1) {
        return this.gain.toFixed(2);
      } else if (this.gain >= 0.01) {
        return this.gain.toFixed(3);
      } else if (this.gain >= 0.001) {
        return this.gain.toFixed(4);
      } else {
        return this.gain.toExponential(2);
      }
    },
  },
  methods: {
    updateGain() {
      this.$emit('update:gain', this.gain);
      this.$emit('change');
    },
    setGainFromOutside(newGain) {
      // Reverse calculation to set slider position from gain value
      const minExponent = -3;
      const maxExponent = 0.699;
      const range = maxExponent - minExponent;
      
      // Clamp the gain to our supported range
      const clampedGain = Math.max(0.001, Math.min(5, newGain));
      const logGain = Math.log10(clampedGain);
      this.sliderValue = Math.round(((logGain - minExponent) / range) * 100);
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

<style scoped>
/* Enhanced slider styling */
.slider {
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  background: linear-gradient(to right, #ef4444 0%, #f97316 25%, #eab308 50%, #22c55e 75%, #3b82f6 100%);
  border-radius: 3px;
  outline: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #374151;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #374151;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  border: none;
}

.slider:hover::-webkit-slider-thumb {
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  transform: scale(1.1);
}

.slider:hover::-moz-range-thumb {
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  transform: scale(1.1);
}
</style>