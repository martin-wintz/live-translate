import React, { useState, useEffect, FC, SetStateAction } from "react";
import io from "socket.io-client";
import axios from "axios"; // assuming you're using axios for HTTP requests
import "./App.css";

const server = "http://localhost:5555";
const socket = io(server);

axios.defaults.withCredentials = true;
axios.defaults.baseURL = server;

// ----------------- Interfaces -----------------

interface Phrase {
  transcriptionId: string;
  startTime: number;
  index: number;
  transcription?: string;
  detectedLanguage?: string;
  translation?: string;
  timestamp?: number;
  transitioning?: boolean;
  incomingTranscription?: string;
}

interface Transcription {
  uniqueId: string;
  timestamp: number;
  phrases: Phrase[];
}

const App: FC = () => {
  const [recording, setRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(
    null,
  );
  const [clientId, setClientId] = useState<string>("");
  const [transcription, setTranscription] = useState<Transcription | null>(
    null,
  );

  useEffect(() => {
    const initializeSession = async () => {
      const response = await axios.post("/init_session");
      setClientId(response.data.client_id);

      socket.on("connect", () => {
        console.log("Connected to server");
      });

      socket.on("translation", (responsePhrase) => {
        setTranscription((previousTranscription) => {
          if (previousTranscription === null) {
            throw new Error(
              "Translation received for non-existent transcription",
            );
          }
          const transcription = { ...previousTranscription };
          if (!transcription.phrases[responsePhrase.index]) {
            throw new Error("Translation received for non-existent phrase");
          } else if (
            transcription.phrases[responsePhrase.index].translation !==
            responsePhrase.translation
          ) {
            transcription.phrases[responsePhrase.index] = {
              ...transcription.phrases[responsePhrase.index],
              translation: responsePhrase.translation,
            };
          }
          return transcription;
        });
      });

      socket.on("transcription", (responsePhrase) => {
        setTranscription(function (previousTranscription) {
          if (previousTranscription === null) {
            throw new Error(
              "Transcription received for non-existent transcription",
            );
          }
          const transcription = { ...previousTranscription };

          // If the phrase is new, add it to the list of phrases
          // We update incomingTranscription to trigger the fade-in transition
          if (!transcription.phrases[responsePhrase.index]) {
            transcription.phrases[responsePhrase.index] = {
              ...responsePhrase,
              transcription: null,
              incomingTranscription: responsePhrase.transcription,
              transitioning: true,
            };
            transcription.phrases[responsePhrase.index].incomingTranscription =
              responsePhrase.transcription;
            transcription.phrases[responsePhrase.index].transitioning = true;
            // Update the transcription if it has changed
          } else if (
            transcription.phrases[responsePhrase.index].transcription !==
            responsePhrase.transcription
          ) {
            transcription.phrases[responsePhrase.index] = {
              ...transcription.phrases[responsePhrase.index],
              incomingTranscription: responsePhrase.transcription,
              transitioning: true,
            };
          }

          return transcription;
        });

        // Remove the old transcription after the fade transition
        setTimeout(() => {
          setTranscription(function (previousTranscription) {
            if (previousTranscription === null) {
              return null;
            }
            const transcription = { ...previousTranscription };
            transcription.phrases[responsePhrase.index] = {
              ...transcription.phrases[responsePhrase.index],
              transcription: responsePhrase.transcription,
              transitioning: false,
              incomingTranscription: "",
            };
            return transcription;
          });
        }, 400); // Duration of the fade transition, MUST MATCH CSS
      });

      return () => {
        socket.off("connect");
      };
    };

    initializeSession();
  }, []);

  const initializeNewRecording = () => {
    // Call backend to initialize audio file
    return axios.post("/start_recording");
  };

  const closeRecording = () => {
    // Call backend to close audio file
    return axios.post("/stop_recording");
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    setMediaRecorder(recorder);

    initializeNewRecording()
      .then((response) => {
        setTranscription(response.data.transcription);
        recorder.start(1000);

        // Event listener for when an audio chunk is available
        recorder.ondataavailable = async (e) => {
          // Convert the audio chunk to an ArrayBuffer and send it via WebSocket
          const data = e.data;
          data.arrayBuffer().then((arrayBuffer) => {
            socket.emit("audio_chunk", {
              clientId,
              arrayBuffer,
            });
          });
        };

        setRecording(true);
      })
      .catch((error) => {
        console.error("Error initializing recording", error);
      });
  };

  const stopRecording = async () => {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      setRecording(false);

      // Call backend to close audio file
      await closeRecording();
    }
  };

  return (
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-20">
      <div>
        <div className="text-gray-900">
          {recording &&
            transcription &&
            transcription.phrases &&
            transcription.phrases.length == 0 && (
              <span className="animate-pulse-fast">|</span>
            )}
          {transcription &&
            transcription.phrases &&
            transcription.phrases.map((phrase, index) => (
              <div className="mb-4" key={index}>
                <div className="relative">
                  <span
                    className={`${phrase.transitioning ? "fade-out" : ""} ${phrase.translation ? "text-pink-900" : ""} ${recording && index == transcription.phrases.length - 1 ? "text-gray-400" : ""} transition-colors`}
                  >
                    {phrase.transcription}
                  </span>
                  {recording && index == transcription.phrases.length - 1 && (
                    <span className="animate-pulse-fast">|</span>
                  )}
                  {phrase.transitioning && (
                    <div className="absolute top-0 left-0 opacity-0 fade-in text-gray-400">
                      {phrase.incomingTranscription}
                    </div>
                  )}
                </div>
                {phrase.translation && (
                  <div className="mb-6 text-pink-600 fade-in">
                    {phrase.translation}
                  </div>
                )}
              </div>
            ))}
        </div>
      </div>
      <button
        className="text-indigo-500 hover:text-indigo-700 transition-colors mt-20j"
        onClick={recording ? stopRecording : startRecording}
      >
        {recording ? "Stop transcribing." : "Click here to start transcribing."}
      </button>
    </div>
  );
};

export default App;
