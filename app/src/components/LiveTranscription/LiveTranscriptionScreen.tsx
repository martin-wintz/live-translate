import React, { useEffect, FC } from "react";
import { initializeSession } from "../../api";
import useLiveTranscriptionEvents from "./UseLiveTranscriptionEvents";
import useRecording from "./UseRecording";
import socket from "../../socket";

const LiveTranscriptionScreen: FC = () => {
  const [clientId, setClientId] = React.useState("");
  const { transcription, setTranscription } = useLiveTranscriptionEvents();
  const { recording, handleStartRecording, handleStopRecording } = useRecording(
    clientId,
    setTranscription,
  );

  useEffect(() => {
    const initializeSessionAndSetupSocket = async () => {
      const data = await initializeSession();
      setClientId(data.client_id);

      socket.on("connect", () => {
        console.log("Connected to server");
      });

      return () => {
        socket.off("connect");
      };
    };

    initializeSessionAndSetupSocket();
  }, []);

  return (
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-20">
      <div>
        <div className="text-gray-900">
          {recording &&
            transcription &&
            transcription.phrases &&
            transcription.phrases.length === 0 && (
              <span className="animate-pulse-fast">|</span>
            )}
          {transcription &&
            transcription.phrases &&
            transcription.phrases.map((phrase, index) => (
              <div className="mb-4" key={index}>
                <div className="relative">
                  <span
                    className={`${phrase.transitioning ? "fade-out" : ""
                      } ${phrase.translation ? "text-pink-900" : ""} ${recording && index === transcription.phrases.length - 1
                        ? "text-gray-400"
                        : ""
                      } transition-colors`}
                  >
                    {phrase.transcription}
                  </span>
                  {recording && index === transcription.phrases.length - 1 && (
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
        onClick={recording ? handleStopRecording : handleStartRecording}
      >
        {recording ? "Stop transcribing." : "Click here to start transcribing."}
      </button>
    </div>
  );
};

export default LiveTranscriptionScreen;
