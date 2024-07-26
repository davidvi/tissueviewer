import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import './index.css'
import PrimeVue from 'primevue/config';
import 'primevue/resources/themes/aura-light-green/theme.css'


let app 
app = createApp(App)
app.use(router)
app.use(store)
app.use(PrimeVue)
app.mount('#app')