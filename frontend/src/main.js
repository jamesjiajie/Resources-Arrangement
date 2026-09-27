import { createApp } from "vue";
import App from "./App.vue";
import FreeformSandbox from "./components/FreeformSandbox.vue";
import "./styles.css";

createApp(window.location.pathname.startsWith("/free-sandbox") ? FreeformSandbox : App).mount("#app");
