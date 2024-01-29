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

  // Uncomment to test with dummy data
  // const [transcriptions, setTranscriptions] = useState([
  //   {
  //     transcription: 'Hello, my name is John',
  //   },
  //   {
  //     transcription: 'I am 25 years old, and I live in Paris. I\'ve lived here for 10 years and enjoy it very much. My hobbies include playing the piano and reading books. I also enjoy playing tennis and going to the gym.',
  //   },
  //   {
  //     transcription: 'Je parle français aussi bien que l\'anglais',
  //     translation: 'I speak French as well as English'
  //   },
  //   {
  //     transcription: 'I am a software engineer',
  //   }
  // ]);

  
  useEffect(() => {

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
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-10">
      <div>
        <div className="text-gray-900">
          {recording && (transcriptions.length == 0) && <span className="animate-pulse-fast">|</span>}
          { transcriptions.map((transcription, index) => (
            <div className="mb-4">
              <div className="relative" key={index}>
                <span className={`${transcription.transitioning ? 'fade-out' : ''} ${transcription.translation ? 'text-pink-900':''} ${recording && (index == transcriptions.length - 1) ? 'text-gray-400':''} transition-colors`}>{transcription.transcription}</span>
  {(recording && (index == transcriptions.length - 1)) && <span className="animate-pulse-fast">|</span>}
                {transcription.transitioning && 
                  <div className="absolute top-0 left-0 opacity-0 fade-in text-gray-400">{transcription.incomingTranscription}</div>
                }
              </div>
              { transcription.translation && 
                <div className="mb-6 text-pink-600 fade-in">{transcription.translation}</div>
              }
            </div>
          ))}
        </div>
      </div>
      <button className="text-indigo-500 hover:text-indigo-700 transition-all" onClick={recording ? stopRecording : startRecording}>
        {recording ? 'Stop transcribing.' : 'Click here to start transcribing.'}
      </button>
    </div>
  );

}

export default App;