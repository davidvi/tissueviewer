import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

import '@mdi/font/css/materialdesignicons.css'
import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";

const app = createApp(App)

app.use(router)

const vuetify = createVuetify({
  components,
  directives,
});

app.use(vuetify);
app.use(store); 

app.config.globalProperties.$filters = {
  truncateGene(value) {
    if (!value) return ''
    value = value.toString();
    if (value.length > 10) {
      return value.substring(0, 10) + '...';
    }
    return value
  }
}

app.mount('#app')
