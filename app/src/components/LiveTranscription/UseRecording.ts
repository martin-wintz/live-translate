import { Dispatch, SetStateAction } from "react";
import { startRecording, stopRecording } from "../../api";
import socket from "../../socket";
import { Transcription } from "../../types";
import {
  startRecording as startMediaRecording,
  stopRecording as stopMediaRecording,
} from "./MediaRecorder";

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

  const handleStartRecording = async () => {
    try {
      const data = await startRecording();
      setTranscription(data.transcription);
      startMediaRecording(onArrayBuffer);
      setRecording(true);
    } catch (error) {
      console.error("Error initializing recording", error);
    }
  };

  const handleStopRecording = async () => {
    if (recording) {
      stopMediaRecording();
      setRecording(false);
      await stopRecording();
    }
  };

  return { recording, handleStartRecording, handleStopRecording };
};

export default useRecording;
