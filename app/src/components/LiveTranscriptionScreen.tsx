import React from 'react'
import useTranscription from '../hooks/useTranscription'
import TranscriptionPhrase from './TranscriptionPhrase'

const LiveTranscriptionScreen: React.FC = () => {
  const { transcription, recording, startTranscribing, stopTranscribing } =
    useTranscription()

  return (
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-20">
      <div>
        <div className="text-gray-900">
          {recording && transcription?.phrases.length === 0 && (
            <span className="animate-pulse-fast">|</span>
          )}
          {transcription?.phrases.map((phrase, index) => (
            <TranscriptionPhrase
              key={index}
              phrase={phrase}
              isLatest={index === transcription.phrases.length - 1}
              recording={recording}
            />
          ))}
        </div>
      </div>
      <button
        className="text-indigo-500 hover:text-indigo-700 transition-colors mt-20"
        onClick={recording ? stopTranscribing : startTranscribing}
      >
        {recording ? 'Stop transcribing.' : 'Click here to start transcribing.'}
      </button>
    </div>
  )
}

export default LiveTranscriptionScreen
