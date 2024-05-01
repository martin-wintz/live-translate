let mediaRecorder: MediaRecorder | null = null;


const startRecording = async (onArrayBuffer) => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
  mediaRecorder = recorder;

  const onDataAvailable = async (e: BlobEvent) => {
    const data = e.data;
    data.arrayBuffer().then(onArrayBuffer);
  };

  recorder.ondataavailable = onDataAvailable;
  recorder.start(1000);
};

const pauseRecording = () => {
  if (mediaRecorder) {
    mediaRecorder.pause();
  }
};

const resumeRecording = () => {
  if (mediaRecorder) {
    mediaRecorder.resume();
  }
};

const stopRecording = () => {
  if (mediaRecorder) {
    mediaRecorder.stop();
    mediaRecorder = null;
  }
};

const Recorder = {
  startRecording,
  pauseRecording,
  resumeRecording,
  stopRecording,
};

export default Recorder;