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
  return (
    <div className="w-64 h-full bg-gray-800 text-white p-5">
      <button
        onClick={onCreateNew}
        className="mb-5 w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
      >
        New Transcription
      </button>
      <h2 className="text-lg mb-3">Recent Transcriptions</h2>
      <ul>
        {transcriptions.map((transcription, index) => {
          const isActive = transcription.uniqueId === selectedTranscription?.uniqueId;
          const itemClasses = `text-sm truncate cursor-pointer ${isActive ? 'bg-blue-300' : ''}`;

          return (
            <li
              key={index}
              className={itemClasses}
              onClick={() => onSelectTranscription(transcription)}
            >
              {new Date(transcription.timestamp * 1000).toLocaleString()}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default Sidebar;
