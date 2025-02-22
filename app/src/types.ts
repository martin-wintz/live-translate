export interface Phrase {
  transcriptionId: string
  startTime: number
  index: number
  transcription?: string
  detectedLanguage?: string
  translation?: string
  timestamp?: string
  transitioning?: boolean
  incomingTranscription?: string
}

export interface Transcription {
  uniqueId: string
  timestamp: number
  phrases: Phrase[]
}
