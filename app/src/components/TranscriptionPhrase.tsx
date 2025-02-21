import React, { useState, useEffect } from 'react'
import { Phrase } from '../types'

interface TranscriptionPhraseProps {
  phrase: Phrase
  isLatest: boolean
  recording: boolean
}

const AnimatedTranscriptionPhrase: React.FC<TranscriptionPhraseProps> = ({
  phrase,
  isLatest,
  recording,
}) => {
  const [transitioning, setTransitioning] = useState(false)
  const [incomingTranscription, setIncomingTranscription] = useState('')

  useEffect(() => {
    if (phrase.transcription !== incomingTranscription) {
      setTransitioning(true)
      setIncomingTranscription(phrase.transcription || '')

      const timer = setTimeout(() => {
        setTransitioning(false)
      }, 400)

      return () => clearTimeout(timer)
    }
  }, [phrase.transcription])

  return (
    <div className="mb-4">
      <div className="relative">
        <span
          className={`
            ${transitioning ? 'animate-fade-out' : ''}
            ${phrase.translation ? 'text-pink-900' : ''}
            ${recording && isLatest ? 'text-gray-400' : ''}
            transition-colors
          `}
        >
          {phrase.transcription}
        </span>
        {recording && isLatest && <span className="animate-pulse-fast">|</span>}
        {transitioning && (
          <div className="absolute top-0 left-0 opacity-0 animate-fade-in-fast text-gray-400">
            {incomingTranscription}
          </div>
        )}
      </div>
      {phrase.translation && (
        <div className="mb-6 text-pink-600 animate-fade-in">
          {phrase.translation}
        </div>
      )}
    </div>
  )
}

export default AnimatedTranscriptionPhrase
