import axios from "axios";
import { SERVER_URL } from "./config";

axios.defaults.withCredentials = true;
axios.defaults.baseURL = SERVER_URL;

const API = {
  initializeSession: async () => {
    const response = await axios.post("/init_session");
    return response.data;
  },

  startRecording: async () => {
    const response = await axios.post("/start_recording");
    return response.data;
  },

  stopRecording: async () => {
    await axios.post("/stop_recording");
  },

  fetchTranscriptions: async () => {
    const response = await axios.get("/transcriptions");
    return response.data;
  }
};

export default API;
