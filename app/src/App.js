import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import axios from 'axios'; // assuming you're using axios for HTTP requests
import './App.css';

const socket = io('http://localhost:5555');

axios.defaults.withCredentials = true;

function App() {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [clientId, setClientId] = useState('');
  const [previousTranscriptions, setPreviousTranscriptions] = useState([]);
  const [currentTranscription, setCurrentTranscription] = useState('');
  const [newTranscription, setNewTranscription] = useState('');
  const [transitioning, setTransitioning] = useState(false);


  
  useEffect(() => {

    const initializeSession = async () => {
      const response = await axios.post('http://localhost:5555/init_session');
      setClientId(response.data.client_id);

      socket.on('connect', () => {
        console.log('Connected to server');
      });

      socket.on('transcription', (response) => {

        if (response.transcriptions && response.transcriptions.length > 0) {
          const newServerTranscription = response.transcriptions[response.transcriptions.length - 1].text;

          const previousTranscriptionsResponse = response.transcriptions.slice(0, response.transcriptions.length - 1);
          setPreviousTranscriptions(function (previousTranscriptions) {
              if (response.transcriptions.length > previousTranscriptions.length + 1) {
                // Because we got a new transcrition, the current transcription will be added to previousTranscriptions
                // So we should not display it twice
                setCurrentTranscription(()=>'');
              }
              return previousTranscriptionsResponse.map(transcription => transcription.text);
            });

          setNewTranscription(newServerTranscription);

          setTransitioning(true);

          setTimeout(() => {
            setCurrentTranscription(newServerTranscription);
            setTransitioning(false);
          }, 400); // Duration of the fade transition

        }
      });


      return () => {
        socket.off('connect');
      };
    };
    
    initializeSession();
  }, []);

  const initializeNewRecording = () => {
    // Call backend to initialize audio file
    return axios.post('http://localhost:5555/start_recording');
  }

  const closeRecording = () => {
    // Call backend to close audio file
    return axios.post('http://localhost:5555/stop_recording');
  }

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    setMediaRecorder(recorder);
  
    initializeNewRecording();
  
    recorder.start(1000);
  
    // Event listener for when an audio chunk is available
    recorder.ondataavailable = async (e) => {
      // Convert the audio chunk to an ArrayBuffer and send it via WebSocket
      const data = e.data;
      data.arrayBuffer().then(arrayBuffer => {
        socket.emit('audio_chunk', {
          clientId,
          arrayBuffer
          });
      });
    };
  
    setRecording(true);
  };
  

  const stopRecording = async () => {
    if (mediaRecorder && recording) {
      mediaRecorder.stop();
      setRecording(false);
      
      // Call backend to close audio file
      await closeRecording();
    }
  };
  

  return (
    <div className="main-container">
      <div className="transcription-container">
        <div className="previous-transcriptions">
          { previousTranscriptions.map((transcription, index) => (
            <div className={`transcription`} key={index}>{transcription}</div>
          ))}
        </div>
        <div className="current-transcriptions">
          <div className={`transcription old ${transitioning ? 'fade-out' : ''}`}>{currentTranscription}</div>
          {transitioning && 
            <div className="transcription new fade-in">{newTranscription}</div>
          }
        </div>
      </div>
      <button onClick={recording ? stopRecording : startRecording}>
        {recording ? 'Stop' : 'Record'}
      </button>
    </div>
  );

}

export default App;