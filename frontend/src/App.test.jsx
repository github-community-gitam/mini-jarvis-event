import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import App from './App';
import { api, requestError, recordingFormat, audioFilename } from './api';
vi.mock('./api', async importOriginal => ({ ...(await importOriginal()), api: { get: vi.fn(), post: vi.fn(), delete: vi.fn() } }));
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return {promise,resolve,reject}; };
const conversations = [{id:'a',title:'First chat'},{id:'b',title:'Second chat'}];
let recorder, stopped, frame;
beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation(url => Promise.resolve({ data: url === '/conversations' ? conversations : url.includes('/status') ? {connected:true} : {user_id:'user'} }));
  api.post.mockResolvedValue({data:{conversation_id:'a',response:'Reply',audio:null,tool_call:null}});
  api.delete.mockResolvedValue({data:{}});
  vi.spyOn(HTMLMediaElement.prototype,'pause').mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype,'play').mockResolvedValue();
  stopped = vi.fn(); frame = vi.fn();
  window.requestAnimationFrame=vi.fn(() => 42); window.cancelAnimationFrame=frame;
  window.AudioContext=class {
    destination={}; resume=vi.fn().mockResolvedValue(); close=vi.fn();
    createAnalyser=()=>({frequencyBinCount:128,getByteFrequencyData:vi.fn()});
    createMediaStreamSource=()=>({connect:vi.fn(),disconnect:vi.fn()});
    createMediaElementSource=()=>({connect:vi.fn(),disconnect:vi.fn()});
  };
  Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:stopped}]})}});
  window.MediaRecorder=class {
    static isTypeSupported=type=>type==='audio/mp4';
    mimeType='audio/mp4'; state='inactive';
    constructor(){recorder=this;}
    start(){this.state='recording';}
    stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['audio'],{type:this.mimeType})});this.onstop?.();}
  };
});
async function ready(){render(<App/>);await screen.findByText('First chat');}

describe('requests and history',()=>{
  it('keeps sign-in usable when the session is missing',async()=>{
    api.get.mockRejectedValue({response:{status:401}});render(<App/>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Sign in'}).disabled).toBe(false));
    fireEvent.change(screen.getByLabelText('Access code'),{target:{value:'a'.repeat(40)}});
    fireEvent.click(screen.getByRole('button',{name:'Sign in'}));
    await waitFor(()=>expect(api.post).toHaveBeenCalledWith('/session/login',{access_code:'a'.repeat(40)}));
  });
  it('shows history loading, failure, retry, and empty state',async()=>{
    const pending=deferred();api.get.mockImplementation(url=>url==='/conversations'?pending.promise:Promise.resolve({data:{}}));
    render(<App/>);await screen.findByText('Loading conversations…');
    await act(async()=>pending.reject(new Error('offline')));
    api.get.mockImplementation(()=>Promise.resolve({data:[]}));
    fireEvent.click(screen.getByRole('button',{name:'Retry'}));
    await screen.findByText('No conversations yet.');
  });
  it('clears stale integration connection state and offers retry',async()=>{
    await ready();api.get.mockImplementation(url=>url.includes('/status')?Promise.reject(new Error('offline')):Promise.resolve({data:[]}));
    fireEvent.click(screen.getByRole('button',{name:'Integrations'}));
    fireEvent.click(screen.getAllByRole('button',{name:'Disconnect'})[0]);
    await screen.findByText('Unable to check integrations.');
    expect(screen.queryAllByRole('button',{name:'Disconnect'})).toHaveLength(0);
    expect(screen.getAllByRole('button',{name:'Connect'})[0].closest('fieldset').disabled).toBe(true);
  });
  it('prevents repeated Enter submissions synchronously',async()=>{
    await ready();const pending=deferred();api.post.mockReturnValue(pending.promise);
    const input=screen.getByPlaceholderText('Ask JARVIS...');fireEvent.change(input,{target:{value:'Hello'}});
    fireEvent.keyDown(input,{key:'Enter'});fireEvent.keyDown(input,{key:'Enter'});
    expect(api.post.mock.calls.filter(([url])=>url==='/jarvis/chat')).toHaveLength(1);
    await act(async()=>pending.resolve({data:{conversation_id:'a',response:'Done'}}));
    await screen.findByText('Done');
  });
  it('ignores chat responses after switching conversations',async()=>{
    await ready();const pending=deferred();api.post.mockReturnValue(pending.promise);
    const input=screen.getByPlaceholderText('Ask JARVIS...');fireEvent.change(input,{target:{value:'Hello'}});fireEvent.keyDown(input,{key:'Enter'});
    api.get.mockImplementation(url=>Promise.resolve({data:url==='/conversations/b'?{messages:[{role:'assistant',content:'Second history'}]}:[]}));
    fireEvent.click(screen.getByText('Second chat'));await screen.findByText('Second history');
    await act(async()=>pending.resolve({data:{conversation_id:'a',response:'Wrong conversation'}}));
    expect(screen.queryByText('Wrong conversation')).toBeNull();
  });
  it('ignores out-of-order history responses',async()=>{
    await ready();const a=deferred(),b=deferred();api.get.mockImplementation(url=>url.endsWith('/a')?a.promise:b.promise);
    fireEvent.click(screen.getByText('First chat'));fireEvent.click(screen.getByText('Second chat'));
    await act(async()=>b.resolve({data:{messages:[{role:'assistant',content:'B history'}]}}));
    await act(async()=>a.resolve({data:{messages:[{role:'assistant',content:'A history'}]}}));
    expect(screen.queryByText('A history')).toBeNull();await screen.findByText('B history');
  });
  it('restores text and explains timeout errors',async()=>{
    await ready();api.post.mockRejectedValue({code:'ECONNABORTED'});
    const input=screen.getByPlaceholderText('Ask JARVIS...');fireEvent.change(input,{target:{value:'Retry me'}});fireEvent.keyDown(input,{key:'Enter'});
    await screen.findByText('The request timed out. Please try again.');expect(input.value).toBe('Retry me');
  });
});

describe('audio lifecycle',()=>{
  it('uploads the browser-selected MIME type and matching filename',async()=>{
    await ready();api.post.mockImplementation(url=>Promise.resolve({data:url==='/jarvis/transcribe'?{text:''}:{}}));
    const mic=document.querySelector('.mic-btn');fireEvent.click(mic);
    await waitFor(()=>expect(recorder.state).toBe('recording'));fireEvent.click(mic);
    await waitFor(()=>expect(api.post).toHaveBeenCalled());
    const file=api.post.mock.calls[0][1].get('file');expect(file.type).toBe('audio/mp4');expect(file.name).toBe('recording.m4a');
    expect(stopped).toHaveBeenCalled();expect(frame).toHaveBeenCalledWith(42);
  });
  it('stops recording and visualization when voice mode exits',async()=>{
    await ready();fireEvent.click(screen.getAllByRole('button',{name:'Voice Chat'})[0]);fireEvent.click(document.querySelector('.voice-main-btn'));
    await waitFor(()=>expect(recorder.state).toBe('recording'));fireEvent.click(document.querySelector('.exit-voice-btn'));
    expect(stopped).toHaveBeenCalled();expect(frame).toHaveBeenCalledWith(42);expect(api.post).not.toHaveBeenCalled();
  });
  it('releases audio resources on unmount',async()=>{
    const {unmount}=render(<App/>);await screen.findByText('First chat');fireEvent.click(document.querySelector('.mic-btn'));
    await waitFor(()=>expect(recorder.state).toBe('recording'));unmount();expect(stopped).toHaveBeenCalled();expect(frame).toHaveBeenCalled();
  });
  it('keeps text available without audio APIs',async()=>{
    delete window.AudioContext;delete window.MediaRecorder;await ready();
    await screen.findByText('Voice is unavailable in this browser. Text chat is available.');
    expect(screen.getByPlaceholderText('Ask JARVIS...').disabled).toBe(false);
  });
  it('reports microphone failure without starting an animation loop',async()=>{
    navigator.mediaDevices.getUserMedia.mockRejectedValue(new Error('denied'));await ready();fireEvent.click(document.querySelector('.mic-btn'));
    await screen.findByText('Microphone unavailable. Check browser permissions and try again.');expect(window.requestAnimationFrame).not.toHaveBeenCalled();
  });
});
it('classifies errors and MIME fallbacks',()=>{
  expect(requestError({response:{status:500}})).toContain('server could not');
  expect(requestError({})).toContain('connection');
  expect(recordingFormat({isTypeSupported:()=>false})).toEqual({});
  expect(audioFilename('audio/ogg;codecs=opus')).toBe('recording.ogg');
});
