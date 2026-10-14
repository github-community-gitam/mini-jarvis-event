import axios from 'axios';
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const api = axios.create({ baseURL: API_URL, withCredentials: true, timeout: 20000 });
export function requestError(error) {
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') return 'The request timed out. Please try again.';
  if (error.response?.status === 401) return 'Your session expired. Please sign in again.';
  if (error.response) return 'The server could not complete this request. Please try again.';
  return 'Unable to reach the server. Check your connection and try again.';
}
export function recordingFormat(Recorder = globalThis.MediaRecorder) {
  const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/webm'].find(type => Recorder?.isTypeSupported?.(type));
  return mimeType ? { mimeType } : {};
}
export function audioFilename(mime) {
  return `recording.${mime.includes('mp4') ? 'm4a' : mime.includes('ogg') ? 'ogg' : mime.includes('wav') ? 'wav' : 'webm'}`;
}
