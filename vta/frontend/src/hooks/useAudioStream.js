import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Audio streaming hook for microphone capture and playback.
 *
 * Captures mic audio at 16kHz mono PCM, sends as base64 via WebSocket.
 * Plays received 24kHz audio chunks from Gemini.
 */
export default function useAudioStream(wsSend) {
  const [isMicActive, setIsMicActive] = useState(false);
  const mediaStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const workletNodeRef = useRef(null);
  const playbackContextRef = useRef(null);
  const playbackQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  // --- Microphone capture ---

  const startMic = useCallback(async () => {
    try {
      console.log('[AUDIO] Starting microphone');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1,
        },
      });

      mediaStreamRef.current = stream;

      // Create AudioContext at 16kHz to avoid resampling
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000,
        latencyHint: 'interactive',
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // Use ScriptProcessorNode with larger buffer (4096) for stability
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        const float32Data = event.inputBuffer.getChannelData(0);

        // Convert Float32 to Int16 PCM
        const int16Array = new Int16Array(float32Data.length);
        for (let i = 0; i < float32Data.length; i++) {
          const s = Math.max(-1, Math.min(1, float32Data[i]));
          int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        // Convert to base64
        const base64 = arrayBufferToBase64(int16Array.buffer);

        // Send to orchestrator
        wsSend({
          event: 'student_audio',
          data: base64,
        });
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      workletNodeRef.current = processor;
      setIsMicActive(true);
    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  }, [wsSend]);

  const stopMic = useCallback(async () => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }

    setIsMicActive(false);
  }, []);

  // --- Audio playback ---

  const playAudioChunk = useCallback((base64Data) => {
    playbackQueueRef.current.push(base64Data);
    if (!isPlayingRef.current) {
      processPlaybackQueue();
    }
  }, []);

  const handleInterruption = useCallback(() => {
    console.log('[AUDIO] Interruption - clearing queue');
    playbackQueueRef.current = [];
    isPlayingRef.current = false;
  }, []);

  const processPlaybackQueue = useCallback(async () => {
    if (playbackQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      wsSend({ event: 'audio_playback_done' });
      return;
    }

    isPlayingRef.current = true;

    if (!playbackContextRef.current) {
      playbackContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,
        latencyHint: 'interactive',
      });
    }

    const ctx = playbackContextRef.current;

    if (ctx.state === 'suspended') {
      try {
        await ctx.resume();
      } catch (e) {
        console.warn('Failed to resume playback context:', e);
      }
    }

    const base64 = playbackQueueRef.current.shift();

    try {
      const pcmBytes = base64ToArrayBuffer(base64);
      const int16Array = new Int16Array(pcmBytes);
      const float32Array = int16ToFloat32(int16Array);

      const audioBuffer = ctx.createBuffer(1, float32Array.length, 24000);
      audioBuffer.getChannelData(0).set(float32Array);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      source.onended = () => {
        processPlaybackQueue();
      };

      source.start();
    } catch (err) {
      console.error('Audio playback error:', err);
      isPlayingRef.current = false;
      if (playbackQueueRef.current.length > 0) {
        setTimeout(() => processPlaybackQueue(), 100);
      }
    }
  }, [wsSend]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMic();
      if (playbackContextRef.current) {
        playbackContextRef.current.close();
      }
    };
  }, [stopMic]);

  return {
    isMicActive,
    startMic,
    stopMic,
    playAudioChunk,
    handleInterruption,
  };
}

// --- Utility Functions ---

function int16ToFloat32(int16Array) {
  const float32Array = new Float32Array(int16Array.length);
  for (let i = 0; i < int16Array.length; i++) {
    float32Array[i] = int16Array[i] / 0x7FFF;
  }
  return float32Array;
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}
