import axios from "axios";
import { SERVER_URL } from "./config";

axios.defaults.withCredentials = true;
axios.defaults.baseURL = SERVER_URL;

export const initializeSession = async () => {
  const response = await axios.post("/init_session");
  return response.data;
};

export const startRecording = async () => {
  const response = await axios.post("/start_recording");
  return response.data;
};

export const stopRecording = async () => {
  await axios.post("/stop_recording");
};

export const fetchTranscriptions = async () => {
  const response = await axios.get("/transcriptions");
  return response.data;
};
