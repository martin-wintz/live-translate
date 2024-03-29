import { useState, useEffect } from "react";
import { Transcription } from "../../types";
import socket from "../../socket";

/**
 * Custom hook to handle live transcription/translation events and update the transcription object
 *
 * @returns transcription: The current transcription object
 * @returns setTranscription: Function to update the transcription object
 **/
const useLiveTranscriptionEvents = () => {
  const [transcription, setTranscription] = useState<Transcription | null>(
    null,
  );

  useEffect(() => {
    // Once a phrase is done transcribing, the server will translate it if necessary
    // Listen for translation events and add them to the corresponding phrase
    socket.on("translation", (responsePhrase) => {
      setTranscription((previousTranscription) => {
        if (previousTranscription === null) {
          throw new Error(
            "Translation received for non-existent transcription",
          );
        }
        const transcription = { ...previousTranscription };
        if (!transcription.phrases[responsePhrase.index]) {
          throw new Error("Translation received for non-existent phrase");
        } else if (
          transcription.phrases[responsePhrase.index].translation !==
          responsePhrase.translation
        ) {
          transcription.phrases[responsePhrase.index] = {
            ...transcription.phrases[responsePhrase.index],
            translation: responsePhrase.translation,
          };
        }
        return transcription;
      });
    });

    // Everytime the server finishes transcribing a chunk of audio, we receive a transcription event
    // We then update the appropriate phrase with the transcription, adding some specialized logic for the fade-in transition
    socket.on("transcription", (responsePhrase) => {
      setTranscription(function (previousTranscription) {
        if (previousTranscription === null) {
          throw new Error(
            "Transcription received for non-existent transcription",
          );
        }
        const transcription = { ...previousTranscription };

        // If the phrase is new, add it to the list of phrases
        // We update incomingTranscription to trigger the fade-in transition
        if (!transcription.phrases[responsePhrase.index]) {
          transcription.phrases[responsePhrase.index] = {
            ...responsePhrase,
            transcription: null,
            incomingTranscription: responsePhrase.transcription,
            transitioning: true,
          };
          transcription.phrases[responsePhrase.index].incomingTranscription =
            responsePhrase.transcription;
          transcription.phrases[responsePhrase.index].transitioning = true;
          // Update the transcription if it has changed
        } else if (
          transcription.phrases[responsePhrase.index].transcription !==
          responsePhrase.transcription
        ) {
          transcription.phrases[responsePhrase.index] = {
            ...transcription.phrases[responsePhrase.index],
            incomingTranscription: responsePhrase.transcription,
            transitioning: true,
          };
        }

        return transcription;
      });

      // Remove the old transcription after the fade transition
      setTimeout(() => {
        setTranscription(function (previousTranscription) {
          if (previousTranscription === null) {
            return null;
          }
          const transcription = { ...previousTranscription };
          transcription.phrases[responsePhrase.index] = {
            ...transcription.phrases[responsePhrase.index],
            transcription: responsePhrase.transcription,
            transitioning: false,
            incomingTranscription: "",
          };
          return transcription;
        });
      }, 400); // Duration of the fade transition, MUST MATCH CSS
    });

    return () => {
      socket.off("translation");
      socket.off("transcription");
    };
  }, []);

  return { transcription, setTranscription };
};

export default useLiveTranscriptionEvents;
