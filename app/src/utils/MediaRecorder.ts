let mediaRecorder: MediaRecorder | null = null
const RECORDING_TIME_SLICE_MS = 1000

export const startRecording = async (onArrayBuffer) => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
  mediaRecorder = recorder

  const onDataAvailable = async (e: BlobEvent) => {
    const data = e.data
    data.arrayBuffer().then(onArrayBuffer)
  }

  recorder.ondataavailable = onDataAvailable
  recorder.start(RECORDING_TIME_SLICE_MS)
}

export const stopRecording = () => {
  if (mediaRecorder) {
    mediaRecorder.stop()
    mediaRecorder = null
  }
}
