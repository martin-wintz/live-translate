import React, { useState, useEffect } from "react";
import Sidebar from "./components/Sidebar";
import { fetchTranscriptions } from "./api";
import LiveTranscriptionScreen from "./components/LiveTranscription/LiveTranscriptionScreen";
import "./App.css";
import { Transcription } from "./types";

const App: React.FC = () => {
  const [transcription, setTranscription] = useState<Transcription | null>(
    null,
  );
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);

  useEffect(() => {
    const loadTranscriptions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchTranscriptions();
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
    // Logic to create a new transcription
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar
        transcriptions={transcriptions}
        onCreateNew={handleCreateNew}
        onSelectTranscription={setTranscription}
      />
      <main className="flex-1 bg-gray-100 p-5">
        {isLoading ? (
          <p>Loading...</p>
        ) : error ? (
          <p className="text-red-500">{error}</p>
        ) : (
          <LiveTranscriptionScreen
            transcription={transcription}
            setTranscription={setTranscription}
            recording={recording}
            setRecording={setRecording}
          />
        )}
      </main>
    </div>
  );
};

export default App;
