import React from 'react'
import { Transcription, Phrase } from '../types'

interface PlainTextTranscriptionProps {
  transcription: Transcription | null
  recording: boolean
}

const PlainTextTranscription: React.FC<PlainTextTranscriptionProps> = ({
  transcription,
  recording,
}) => {
  const formattedText = transcription
    ? transcription.phrases
        .map((phrase: Phrase) => {
          const timestamp = phrase.timestamp
            ? new Date(parseFloat(phrase.timestamp) * 1000).toLocaleTimeString(
                'en-US',
                {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                }
              )
            : ''
          const translation = phrase.translation
            ? `\n(${phrase.translation})`
            : ''
          return `[${timestamp}] ${phrase.transcription}${translation}`
        })
        .join('\n\n')
    : ''

  return (
    <textarea
      className="w-full h-full min-h-[20rem] p-2 font-mono text-sm"
      value={formattedText}
      readOnly
      placeholder={
        recording ? 'Recording...' : 'Start recording to see transcription'
      }
    />
  )
}

export default PlainTextTranscription
