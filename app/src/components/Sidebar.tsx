import React from "react";
import { Transcription } from "../types";

interface SidebarProps {
  selectedTranscription: Transcription | null;
  transcriptions: Transcription[]; // Type this based on your transcription data structure
  onSelectTranscription: (transcription: Transcription) => void;
  onCreateNew: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  selectedTranscription,
  transcriptions,
  onCreateNew,
  onSelectTranscription,
}) => {
  function formatDate(date) {

    const formatter = new Intl.DateTimeFormat('en-US', {
      weekday: 'long', // long weekday name.
      month: 'long', // long month name.
      day: 'numeric', // numeric day.
      hour: 'numeric', // numeric hour.
      minute: 'numeric', // numeric minute.
      hour12: true // use 12-hour time format instead of 24-hour format.
    });

    return formatter.format(date);
  }
  return (
    <div className="w-80 bg-gray-800 text-white p-5">
      {selectedTranscription && (
        <button
          onClick={onCreateNew}
          className="mb-8 mt-10 w-full bg-pink-600 hover:bg-pink-400 text-white font-bold py-3 px-4 rounded text-xl"
        >
          New Transcription
        </button>
      )}
      {!selectedTranscription && (
        <button
          className="mb-8 mt-10 w-full bg-gray-500 text-white font-bold py-3 px-4 rounded text-xl"
        >
          New Transcription
        </button>
      )}

      <h2 className="text-lg mb-6 mt-10 font-bold text-gray-200">Previous Transcriptions</h2>
      <ul>
        {transcriptions.map((transcription, index) => {
          const isActive = transcription.uniqueId === selectedTranscription?.uniqueId;
          const itemClasses = `text-base truncate cursor-pointer bg-gray-800 rounded hover:bg-gray-600 mt-3 p-2  ${isActive ? 'bg-pink-300 hover:bg-pink-300' : ''}`;

          return (
            <li
              key={index}
              className={itemClasses}
              onClick={() => onSelectTranscription(transcription)}
            >
              {formatDate(new Date(transcription.timestamp * 1000))}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default Sidebar;
