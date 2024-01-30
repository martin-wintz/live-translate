import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import axios from 'axios'; // assuming you're using axios for HTTP requests
import './App.css';

const server = 'http://localhost:5555';
const socket = io(server);

axios.defaults.withCredentials = true;
axios.defaults.root = server;


function App() {
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [clientId, setClientId] = useState('');
  const [transcription, setTranscription] = useState({ phrases: [] });

  if (process.env.NODE_ENV === 'development') {
    window.loadTestData = () => {
      setTranscription(() => ({ phrases: [
        {
          index: 0,
          transcription: 'Hello, my name is John',
        },
        {
          index: 1,
          transcription: 'I am 24 years old, and I live in Paris. I\'ve lived here for 10 years and enjoy it very much. My hobbies include playing the piano and reading books. I also enjoy playing tennis and going to the gym.',
        },
        {
          index: 2,
          transcription: 'Je parle français aussi bien que l\'anglais',
          translation: 'I speak French as well as English'
        },
        {
          index: 3,
          transcription: 'I am a software engineer',
        }
      ]}));
    }
  }

  useEffect(() => {

    const initializeSession = async () => {
      const response = await axios.post('/init_session');
      setClientId(response.data.client_id);

      socket.on('connect', () => {
        console.log('Connected to server');
      });

      socket.on('start_translation', (response) => {
        console.log('start_translation', response);
      });

      socket.on('translation', (responsePhrase) => {
        setTranscription((previousTranscription) => {
          const transcription = {...previousTranscription};
          if (!transcription.phrases[responsePhrase.index]) {
            throw new Error('Translation received for non-existent transcription');
          } else if (transcription.phrases[responsePhrase.index].translation !== responsePhrase.translation) {
            transcription.phrases[responsePhrase.index] = {
              ...transcription.phrases[responsePhrase.index],
              translation: responsePhrase.translation
            }
          }
          return transcription;
        });
      });

      socket.on('transcription', (responsePhrase) => {
        
      setTranscription(function (previousTranscription) {
        const transcription = {...previousTranscription};

        // If the phrase is new, add it to the list of phrases
        // We update incomingTranscription to trigger the fade-in transition
        if (!transcription.phrases[responsePhrase.index]) {
          transcription.phrases[responsePhrase.index] = {
            incomingTranscription: responsePhrase.transcription,
            transitioning: true
          };
        // Update the transcription if it has changed
        } else if (transcription.phrases[responsePhrase.index].transcription !== responsePhrase.transcription) {
          transcription.phrases[responsePhrase.index] = {
            ...transcription.phrases[responsePhrase.index],
            incomingTranscription: responsePhrase.transcription,
            transitioning: true
          };
        } 

        return transcription;
      });


        // Remove the old transcription after the fade transition
        setTimeout(() => {
          setTranscription(function (previousTranscription) {
            const transcription = {...previousTranscription};
            transcription.phrases[responsePhrase.index] = {
              ...transcription.phrases[responsePhrase.index],
              transcription: responsePhrase.transcription,
              transitioning: false,
              incomingTranscription: ''
            };
            return transcription;
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
    return axios.post('/start_recording');
  }

  const closeRecording = () => {
    // Call backend to close audio file
    return axios.post('/stop_recording');
  }

  const startRecording = async () => {
    setTranscription({phrases:[]});
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
    <div className="max-w-prose mx-auto px-4 font-serif text-xl py-20">
      <div>
        <div className="text-gray-900">
          {recording && transcription.phrases && (transcription.phrases.length == 0) && <span className="animate-pulse-fast">|</span>}
          {transcription.phrases && transcription.phrases.map((phrase, index) => (
            <div className="mb-4" key={index}>
              <div className="relative">
                <span className={`${phrase.transitioning ? 'fade-out' : ''} ${phrase.translation ? 'text-pink-900' : ''} ${recording && (index == transcription.phrases.length - 1) ? 'text-gray-400' : ''} transition-colors`}>{phrase.transcription}</span>
                {(recording && (index == transcription.phrases.length - 1)) && <span className="animate-pulse-fast">|</span>}
                {phrase.transitioning &&
                  <div className="absolute top-0 left-0 opacity-0 fade-in text-gray-400">{phrase.incomingTranscription}</div>
                }
              </div>
              {phrase.translation &&
                <div className="mb-6 text-pink-600 fade-in">{phrase.translation}</div>
              }
            </div>
          ))}
        </div>
      </div>
      <button className="text-indigo-500 hover:text-indigo-700 transition-colors mt-20j" onClick={recording ? stopRecording : startRecording}>
        {recording ? 'Stop transcribing.' : 'Click here to start transcribing.'}
      </button>
    </div>
  );

}

export default App;