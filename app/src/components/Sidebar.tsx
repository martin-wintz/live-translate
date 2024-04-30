import React from "react";
import { Transcription } from "../types";

interface SidebarProps {
  transcriptions: Transcription[]; // Type this based on your transcription data structure
  onSelectTranscription: (transcription: Transcription) => void;
  onCreateNew: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
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
        {transcriptions.map((transcription, index) => (
          <li
            key={index}
            className="text-sm truncate cursor-pointer"
            onClick={() => onSelectTranscription(transcription)}
          >
            {/* TODO: Refactor transcription timestamp to always be a Date object on the front end */}
            {new Date(transcription.timestamp * 1000).toLocaleString()}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;
