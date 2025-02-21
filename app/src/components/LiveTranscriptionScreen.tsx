import React from 'react'
import useTranscription from '../hooks/useTranscription'
import AnimatedTranscription from './AnimatedTranscription'

const LiveTranscriptionScreen: React.FC = () => {
  const { transcription, recording, startTranscribing, stopTranscribing } =
    useTranscription()

  return (
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-20">
      <div>
        <AnimatedTranscription
          transcription={transcription}
          recording={recording}
        />
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
