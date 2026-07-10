import { createPinia } from 'pinia'
import { createApp } from 'vue'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import { router } from './router'
import './styles.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.mount('#app')
