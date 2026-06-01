import { useCallback, useRef, useState } from "react";
import { postTranscribe } from "../api/client";

interface Props {
  onTranscribed: (text: string) => void;
  onError: (message: string) => void;
  disabled?: boolean;
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const numChannels = 1;
  const bitsPerSample = 16;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeStr(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function MicIcon() {
  return (
    <svg
      className="icon-mic"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 14 0h-2zm-5 7a7 7 0 0 0-7-7H3a9 9 0 0 0 18 0h-2a7 7 0 0 0-7 7v3h4v2H8v-2h4v-3z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      className="icon-stop"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="6" y="6" width="12" height="12" rx="1" />
    </svg>
  );
}

export default function VoiceRecordButton({ onTranscribed, onError, disabled }: Props) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);

  const stopRecording = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;

    const stopped = new Promise<Blob[]>((resolve) => {
      recorder.onstop = () => resolve(chunksRef.current);
      recorder.stop();
    });

    recorder.stream.getTracks().forEach((t) => t.stop());
    mediaRecorderRef.current = null;
    setRecording(false);

    const chunks = await stopped;
    if (chunks.length === 0) {
      onError("No audio captured.");
      return;
    }

    setBusy(true);
    try {
      let blob: Blob;
      const mime = chunks[0].type || "audio/webm";
      if (mime.includes("wav")) {
        blob = new Blob(chunks, { type: "audio/wav" });
      } else {
        const arrayBuffer = await new Blob(chunks, { type: mime }).arrayBuffer();
        const ctx = audioContextRef.current ?? new AudioContext();
        audioContextRef.current = ctx;
        const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
        const channel = audioBuffer.getChannelData(0);
        blob = encodeWav(channel, audioBuffer.sampleRate);
      }
      const { text } = await postTranscribe(blob, "recording.wav");
      onTranscribed(text);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Transcription failed");
    } finally {
      setBusy(false);
      chunksRef.current = [];
    }
  }, [onTranscribed, onError]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const preferred = ["audio/webm", "audio/webm;codecs=opus", "audio/wav"];
      const mime = preferred.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch {
      onError("Microphone access denied or unavailable.");
    }
  }, [onError]);

  const handleClick = () => {
    if (busy || disabled) return;
    if (recording) void stopRecording();
    else void startRecording();
  };

  const ariaLabel = busy
    ? "Transcribing audio"
    : recording
      ? "Stop recording"
      : "Record voice question";

  return (
    <button
      type="button"
      className={`btn btn-record${recording ? " recording" : ""}${busy ? " busy" : ""}`}
      onClick={handleClick}
      disabled={disabled || busy}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      {busy ? <span className="btn-record-busy">…</span> : recording ? <StopIcon /> : <MicIcon />}
    </button>
  );
}
