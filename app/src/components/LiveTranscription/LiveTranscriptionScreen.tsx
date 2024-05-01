import React, {
  FC,
  Dispatch,
  SetStateAction,
} from "react";
import { Transcription } from "../../types";

interface LiveTranscriptionScreenProps {
  transcription: Transcription | null;
  recording: boolean;
  handleStartRecording: () => void;
  handleStopRecording: () => void;
}

const LiveTranscriptionScreen: FC<LiveTranscriptionScreenProps> = ({
  transcription,
  recording,
  handleStartRecording,
  handleStopRecording
}) => {


  return (
    <div>
      <div className="bg-gray-50 w-full p-5 flex justify-between">
        <div className="self-center text-gray-500 font-bold text-2xl">Live Transcription</div>
        <button
          className="py-2 px-4 rounded-lg text-pink-500 text-xl border-2 border-gray-300 bg-gray-50 font-bold hover:bg-gray-200"
          onClick={recording ? handleStopRecording : handleStartRecording}
        >
          {recording ? "Stop Transcribing" : "Start Transcribing"}
        </button>
      </div>
      <div className="max-w-prose mx-auto px-4 pt-10">
        <div className="text-xl">
          <div className="text-gray-800">
            {recording &&
              transcription &&
              transcription.phrases &&
              transcription.phrases.length === 0 && (
                <span className="animate-pulse-fast">|</span>
              )}
            {!transcription &&
              <div className="text-gray-400">
                <p>Click <strong>Start Transcribing</strong> on the upper right-hand corner of your screen to start transcribing.</p><p className="mt-3 italic">Make sure to enable microphone permissions when prompted.</p></div>
            }
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

      </div>
    </div>
  );
};

export default LiveTranscriptionScreen;
