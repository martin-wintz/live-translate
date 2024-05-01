import "./App.css";
import React, { useState, useEffect } from "react";
import { Transcription } from "./types";
import useLiveTranscriptionEvents from "./components/LiveTranscription/UseLiveTranscriptionEvents";
import useRecording from "./components/LiveTranscription/UseRecording";
import socket from "./socket";
import Sidebar from "./components/Sidebar";
import LiveTranscriptionScreen from "./components/LiveTranscription/LiveTranscriptionScreen";
import API from "./api";

const App: React.FC = () => {
  const [transcription, setTranscription] = useState<Transcription | null>(
    null,
  );
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [clientId, setClientId] = useState("");

  // Set up sockets
  useEffect(() => {
    const initializeSessionAndSetupSocket = async () => {
      const data = await API.initializeSession();
      setClientId(data.client_id);

      socket.on("connect", () => {
        console.log("Connected to server");
      });

      // Cleanup function
      return () => {
        socket.off("connect");
      };
    };

    initializeSessionAndSetupSocket();
  }, []);

  // Set up media recording logic
  const {startRecording, stopRecording, pauseRecording, resumeRecording} = useRecording(
    clientId,
    setTranscription,
    recording,
    setRecording,
  );

  // Set up socket event listeners for live transcription
  useLiveTranscriptionEvents(transcription, setTranscription);


  // Load transcriptions
  useEffect(() => {
    const loadTranscriptions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await API.fetchTranscriptions();
        setTranscriptions(data.transcriptions);
      } catch (error) {
        setError("Failed to load transcriptions: " + error.message);
      } finally {
        setIsLoading(false);
      }
    };

    loadTranscriptions();
  }, []);

  const handleCreateNew = () => {
    setTranscription(null);
  };

  const selectTranscription = async (transcription: Transcription) => {
    // If currently recording, show a confirmation dialog
    pauseRecording();
    if (recording) {
      if (window.confirm("You are currently recording. Are you sure you want to switch transcriptions?")) {
        await stopRecording();
        setTranscription(transcription);
      } else {
        resumeRecording();
        return;
      }
    } else {
      setTranscription(transcription);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar
        selectedTranscription={transcription}
        transcriptions={transcriptions}
        onCreateNew={handleCreateNew}
        onSelectTranscription={selectTranscription}
      />
      <main className="flex-1 bg-gray-100 p-5">
        {isLoading ? (
          <p>Loading...</p>
        ) : error ? (
          <p className="text-red-500">{error}</p>
        ) : (
          <LiveTranscriptionScreen
            transcription={transcription}
            recording={recording}
            handleStartRecording={startRecording}
            handleStopRecording={stopRecording}
          />
        )}
      </main>
    </div>
  );
};

export default App;
