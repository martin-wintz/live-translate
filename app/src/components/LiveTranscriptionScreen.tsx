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
      <div className="max-w-prose mx-auto px-4 py-20 relative h-screen flex flex-col">
        <div className="flex justify-between items-center mb-4">
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
      </div>
    </div>
  )
}

export default LiveTranscriptionScreen
