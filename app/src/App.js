import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import hark from 'hark';
import axios from 'axios'; // assuming you're using axios for HTTP requests

const socket = io('http://localhost:5555');

function App() {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [uniqueId, setUniqueId] = useState('');
  const [silenceTimer, setSilenceTimer] = useState(null);


  useEffect(() => {
    socket.on('connect', () => {
      console.log('Connected to server');
    });

    return () => {
      socket.off('connect');
    };
  }, []);

  const initializeNewRecording = () => {
    // Call backend to initialize audio file
    return axios.post('http://localhost:5555/start_recording', { clientId: socket.id }).then(response => {
      setUniqueId(response.data.uniqueId);
    });
  }

  const closeRecording = () => {
    // Call backend to close audio file
    return axios.post('http://localhost:5555/stop_recording', { clientId: socket.id });
  }

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    setMediaRecorder(recorder);
  
    initializeNewRecording();
  
    recorder.start();
  
    // Set up hark to monitor the stream
    const speechEvents = hark(stream, {});
  
    speechEvents.on('stopped_speaking', () => {
      setSilenceTimer(setTimeout(async () => {
        // Silence for more than 3 seconds detected
        await closeRecording();
        initializeNewRecording();
      }, 3000)); // 3000 milliseconds = 3 seconds
    });

    speechEvents.on('speaking', () => {
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        setSilenceTimer(null);
      }
    });
  
    // Event listener for when an audio chunk is available
    recorder.ondataavailable = async (e) => {
      // Convert the audio chunk to an ArrayBuffer and send it via WebSocket
      const data = e.data;
      data.arrayBuffer().then(arrayBuffer => {
        socket.emit('audio_chunk', arrayBuffer, uniqueId);
      });
    };
  
    setRecording(true);
  };
  

  const stopRecording = async () => {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      setRecording(false);
      clearTimeout(silenceTimer);
      
      // Call backend to close audio file
      await closeRecording();
    }
  };
  

  return (
    <div>
      <button onClick={recording ? stopRecording : startRecording}>
        {recording ? 'Stop' : 'Record'}
      </button>
    </div>
  );
}

export default App;
