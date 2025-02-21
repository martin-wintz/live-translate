import React from 'react'
import AnimatedTranscriptionPhrase from './TranscriptionPhrase'
import { Transcription } from '../types'

interface AnimatedTranscriptionProps {
  transcription: Transcription | null
  recording: boolean
}

const AnimatedTranscription: React.FC<AnimatedTranscriptionProps> = ({
  transcription,
  recording,
}) => {
  return (
    <div className="text-gray-900">
      {recording && transcription?.phrases.length === 0 && (
        <span className="animate-pulse-fast">|</span>
      )}
      {transcription?.phrases.map((phrase, index) => (
        <AnimatedTranscriptionPhrase
          key={index}
          phrase={phrase}
          isLatest={index === transcription.phrases.length - 1}
          recording={recording}
        />
      ))}
    </div>
  )
}

export default AnimatedTranscription
