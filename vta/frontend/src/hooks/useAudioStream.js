import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Audio streaming hook for microphone capture and playback.
 *
 * Captures mic audio at 16kHz mono, encodes to base64 LPCM,
 * and sends chunks via WebSocket.
 *
 * Plays received 24kHz audio chunks from Nova Sonic.
 */
export default function useAudioStream(wsSend) {
  const [isMicActive, setIsMicActive] = useState(false);
  const mediaStreamRef = useRef(null);
  const processorRef = useRef(null);
  const audioContextRef = useRef(null);
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
        },
      });

      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)({
        latencyHint: 'interactive',
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // Use smaller buffer size (512) for lower latency
      const processor = audioContext.createScriptProcessor(512, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = async (event) => {
        const inputBuffer = event.inputBuffer;
        const targetSampleRate = 16000;

        try {
          // Create offline context for resampling to 16kHz
          const offlineContext = new OfflineAudioContext({
            numberOfChannels: 1,
            length: Math.ceil(inputBuffer.duration * targetSampleRate),
            sampleRate: targetSampleRate,
          });

          // Copy input to offline context buffer
          const offlineSource = offlineContext.createBufferSource();
          const monoBuffer = offlineContext.createBuffer(
            1,
            inputBuffer.length,
            inputBuffer.sampleRate
          );
          monoBuffer.copyToChannel(inputBuffer.getChannelData(0), 0);

          offlineSource.buffer = monoBuffer;
          offlineSource.connect(offlineContext.destination);
          offlineSource.start(0);

          // Resample
          const renderedBuffer = await offlineContext.startRendering();
          const resampled = renderedBuffer.getChannelData(0);

          // Convert to Int16 PCM
          const buffer = new ArrayBuffer(resampled.length * 2);
          const pcmData = new DataView(buffer);

          for (let i = 0; i < resampled.length; i++) {
            const s = Math.max(-1, Math.min(1, resampled[i]));
            pcmData.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
          }

          // Convert to base64
          const base64 = arrayBufferToBase64(buffer);

          // Send to orchestrator
          wsSend({
            event: 'student_audio',
            data: base64,
          });
        } catch (err) {
          console.error('Audio processing error:', err);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsMicActive(true);
    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  }, [wsSend]);

  const stopMic = useCallback(async () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
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
    // Clear audio queue when Sonic signals interruption
    console.log('[AUDIO] Sonic signaled interruption - clearing queue');
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

    // Resume context if suspended
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
      // Try to continue with next chunk
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

function float32ToInt16(float32Array) {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16Array;
}

function int16ToFloat32(int16Array) {
  const float32Array = new Float32Array(int16Array.length);
  for (let i = 0; i < int16Array.length; i++) {
    float32Array[i] = int16Array[i] / 0x7fff;
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
