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
  const [transcriptions, setTranscriptions] = useState([]);

  
  useEffect(() => {

    console.log('Initializing session');
    const initializeSession = async () => {
      const response = await axios.post('http://localhost:5555/init_session');
      setClientId(response.data.client_id);

      socket.on('connect', () => {
        console.log('Connected to server');
      });

      socket.on('start_translation', (response) => {
        console.log('start_translation', response);
      });

      socket.on('translation', (response) => {
        setTranscriptions((previousTranscriptions) => {
          const transcriptions = [...previousTranscriptions]
          if (!transcriptions[response.index]) {
            throw new Error('Translation received for non-existent transcription');
          } else if (transcriptions[response.index].translation !== response.translation) {
            transcriptions[response.index].translation = response.translation;
          }
          return transcriptions;
        });
      });

      socket.on('transcription', (transcription) => {
        
        setTranscriptions(function (previousTranscriptions) {
          const transcriptions = [...previousTranscriptions]

          // If the transcription is new, add it to the list of transcriptions
          // We update incomingTranscription to trigger the fade-in transition
          if (!transcriptions[transcription.index]) {
            transcriptions[transcription.index] = {
              incomingTranscription: transcription.text,
              transitioning: true
            }
          // Update the transcription if it has changed
          } else {
            if (transcriptions[transcription.index].transcription !== transcription.text) {
              transcriptions[transcription.index].incomingTranscription = transcription.text;
              transcriptions[transcription.index].transitioning = true;
            }
          }

          return transcriptions;
          });

          // Remove the old transcription after the fade transition
          setTimeout(() => {
            setTranscriptions(function (previousTranscriptions) {
              const transcriptions = [...previousTranscriptions];
              transcriptions[transcription.index].transcription = transcription.text;
              transcriptions[transcription.index].transitioning = false;
              transcriptions[transcription.index].incomingTranscription = '';
              return transcriptions;
            });
          }, 400); // Duration of the fade transition, MUST MATCH CSS

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
      <div className="transcriptions-container">
        <div className="transcriptions">
          { transcriptions.map((transcription, index) => (
            <div className="transcription-container">
              <div className="transcription" key={index}>
                <div className={`transcription-text old ${transcription.transitioning ? 'fade-out' : ''}`}>{transcription.transcription}</div>
                {transcription.transitioning && 
                  <div className="transcription-text new fade-in">{transcription.incomingTranscription}</div>
                }
              </div>
              { transcription.translation && 
                <div className="translation fade-in">{transcription.translation}</div>
              }
            </div>
          ))}
        </div>
      </div>
      <button onClick={recording ? stopRecording : startRecording}>
        {recording ? 'Stop' : 'Record'}
      </button>
    </div>
  );

}

export default App;