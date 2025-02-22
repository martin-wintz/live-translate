import React from 'react'

interface TranscriptionButtonProps {
  recording: boolean
  onClick: () => void
}

const TranscriptionButton: React.FC<TranscriptionButtonProps> = ({
  recording,
  onClick,
}) => {
  const baseClasses =
    'px-3 py-1.5 rounded-sm text-white transition-all text-sm font-medium shadow-sm'
  const colorClasses = recording
    ? 'bg-rose-500 hover:bg-rose-400'
    : 'bg-emerald-400 hover:bg-emerald-300'
  const recordingClass = recording ? 'animate-glow' : ''

  return (
    <button
      className={`${baseClasses} ${colorClasses} ${recordingClass}`}
      onClick={onClick}
    >
      {recording ? 'Stop Transcribing' : 'Start Transcribing'}
    </button>
  )
}

export default TranscriptionButton
