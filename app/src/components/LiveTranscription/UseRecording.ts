import { Dispatch, SetStateAction } from "react";
import API from "../../api";
import socket from "../../socket";
import { Transcription } from "../../types";
import Recorder from "./MediaRecorder";

const useRecording = (
  clientId: string,
  setTranscription: (transcription: Transcription) => void,
  recording: boolean,
  setRecording: Dispatch<SetStateAction<boolean>>,
) => {
  const onArrayBuffer = (arrayBuffer: ArrayBuffer) => {
    socket.emit("audio_chunk", {
      clientId,
      arrayBuffer,
    });
  };

  const startRecording = async () => {
    try {
      const data = await API.startRecording();
      setTranscription(data.transcription);
      Recorder.startRecording(onArrayBuffer);
      setRecording(true);
    } catch (error) {
      console.error("Error initializing recording", error);
    }
  };

  const stopRecording = async () => {
    if (recording) {
      Recorder.stopRecording();
      setRecording(false);
      await API.stopRecording();
    }
  };

  const pauseRecording = () => {
    if (recording) {
      Recorder.pauseRecording();
    } 
  };

  const resumeRecording = () => {
    if (recording) {
      Recorder.resumeRecording();
    }
  }

  return { recording, startRecording, stopRecording, pauseRecording, resumeRecording};
};

export default useRecording;
