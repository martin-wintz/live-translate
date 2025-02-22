import React, { useState } from 'react'
import useTranscription from '../hooks/useTranscription'
import AnimatedTranscription from './AnimatedTranscription'
import TranscriptionButton from './ui/TranscriptionButton'
import PlainTextTranscription from './PlainTextTranscription'
import ToggleSwitch from './ui/ToggleSwitch'

const LiveTranscriptionScreen: React.FC = () => {
  const { transcription, recording, startTranscribing, stopTranscribing } =
    useTranscription()
  const [viewMode, setViewMode] = useState<'animated' | 'plain'>('animated')

  return (
    <div className="min-h-screen bg-[url('/subtle-pattern.png')] bg-repeat relative">
      <div className="absolute inset-0 bg-gradient-to-b from-gray-50/70 to-gray-50/90 pointer-events-none" />
      <div className="max-w-prose mx-auto px-4 py-8 sm:py-20 relative h-screen flex flex-col">
        <div className="flex justify-between items-end mb-4">
          <TranscriptionButton
            recording={recording}
            onClick={recording ? stopTranscribing : startTranscribing}
          />
          <ToggleSwitch
            leftLabel="Animated"
            rightLabel="Plain Text"
            value={viewMode === 'plain'}
            onChange={(value) => setViewMode(value ? 'plain' : 'animated')}
          />
        </div>
        {(transcription && transcription.phrases.length > 0) || recording ? (
          <div className="bg-white rounded-md shadow-sm p-8 border border-gray-200 flex-1 mb-20">
            <div className={viewMode === 'animated' ? 'block' : 'hidden'}>
              <AnimatedTranscription
                transcription={transcription}
                recording={recording}
              />
            </div>
            <div className={viewMode === 'plain' ? 'block' : 'hidden'}>
              <PlainTextTranscription
                transcription={transcription}
                recording={recording}
              />
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-md shadow-sm p-8 border border-gray-200 flex-1 mb-20">
            <div className="text-gray-400 text-sm font-normal font-lexend">
              <p className="mb-4">
                Press the button above to start transcribing live audio from
                your microphone. (
                <em>Look out for the pop-up asking for microphone access!</em>)
              </p>
              <p className="mb-4">
                If a language other than English is detected, it will
                automatically be translated.
              </p>
              <p className="mb-4">
                Clicking the button will start a new transcription, overwriting
                the old one.
              </p>
              <p>
                Switch to plain text using the toggle switch for a
                copy-paste-friendly version.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LiveTranscriptionScreen
