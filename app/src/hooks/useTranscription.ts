import { useState, useEffect } from 'react'
import { Transcription, Phrase } from '../types'
import socket from '../socket'
import { startRecording, stopRecording } from '../utils/MediaRecorder'

const useTranscription = () => {
  const [recording, setRecording] = useState(false)
  const [transcription, setTranscription] = useState<Transcription | null>(null)

  useEffect(() => {
    // Set up listeners for transcription and translation messages
    socket.on('transcription', handleTranscriptionMessage)
    socket.on('translation', handleTranslationMessage)

    return () => {
      socket.off('transcription')
      socket.off('translation')
    }
  }, [])

  const handleTranslationMessage = (receivedPhrase: Phrase) => {
    console.log('Received translation message:', receivedPhrase)
    setTranscription((prev) => {
      if (!prev) return prev
      const transcription = { ...prev }

      if (!transcription.phrases[receivedPhrase.index]) {
        console.error('Received translation for non-existent phrase')
        return transcription
      }

      transcription.phrases[receivedPhrase.index] = {
        ...transcription.phrases[receivedPhrase.index],
        translation: receivedPhrase.translation,
      }
      return transcription
    })
  }

  const handleTranscriptionMessage = (receivedPhrase: Phrase) => {
    console.log('Received transcription message:', receivedPhrase)
    setTranscription((prev) => {
      if (!prev) return prev
      const transcription = { ...prev }
      transcription.phrases[receivedPhrase.index] = {
        ...(transcription.phrases[receivedPhrase.index] || receivedPhrase),
        transcription: receivedPhrase.transcription,
      }
      return transcription
    })
  }

  const onArrayBuffer = (arrayBuffer: ArrayBuffer) => {
    socket.emit('audio_chunk', { arrayBuffer })
  }

  const startTranscribing = async () => {
    try {
      const micAccessPromise = navigator.mediaDevices.getUserMedia({
        audio: true,
      })
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Microphone access timeout')), 10000)
      })

      // Wait for either microphone access or timeout
      await Promise.race([micAccessPromise, timeoutPromise]).catch((error) => {
        alert(
          'Could not access microphone. Please check your permissions and try again.'
        )
        throw error
      })

      const { transcription: newTranscription } = await new Promise<{
        transcription: Transcription
      }>((resolve) => {
        socket.emit('start_recording', resolve)
      })

      setTranscription(newTranscription)
      startRecording(onArrayBuffer)
      setRecording(true)
    } catch (error) {
      console.error('Error starting transcription:', error)
    }
  }

  const stopTranscribing = async () => {
    if (recording) {
      stopRecording()
      setRecording(false)
      await new Promise((resolve) => {
        socket.emit('stop_recording', resolve)
      })
    }
  }

  return {
    transcription,
    recording,
    startTranscribing,
    stopTranscribing,
  }
}

export default useTranscription
