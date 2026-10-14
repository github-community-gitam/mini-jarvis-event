import base64
import os
import secrets
import tempfile
from uuid import UUID
from typing import Literal
from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, StrictBool
from starlette.concurrency import run_in_threadpool
from groq import Groq
from config import GROQ_API_KEY, DATABASE_URL
import memory
from brain import generate_response
from tool_registry import registry, safe_error
from security import owner_context, owner_id, session_owner, serializer, authenticate, COOKIE
from oauth import router as oauth_router

MAX_CHAT_CHARS = int(os.getenv('MAX_CHAT_CHARS', '10000'))
MAX_BODY_BYTES = int(os.getenv('MAX_BODY_BYTES', '65536'))
MAX_AUDIO_BYTES = int(os.getenv('MAX_AUDIO_BYTES', str(20 * 1024 * 1024)))
AUDIO_TYPES = {'audio/webm': '.webm', 'audio/ogg': '.ogg', 'audio/mp4': '.m4a', 'audio/mpeg': '.mp3', 'audio/wav': '.wav', 'audio/x-wav': '.wav'}
ALLOWED_ORIGINS = [x.strip() for x in os.getenv('FRONTEND_URL', 'http://localhost:5173').split(',')]

class BodyLimitMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        limit = MAX_AUDIO_BYTES + 65536 if scope['path'] == '/api/jarvis/transcribe' else MAX_BODY_BYTES
        chunks, size = [], 0
        while True:
            msg = await receive()
            if msg['type'] == 'http.disconnect': return
            size += len(msg.get('body', b''))
            if size > limit:
                return await JSONResponse({'detail': 'Request body too large'}, 413)(scope, receive, send)
            chunks.append(msg)
            if not msg.get('more_body', False): break
        async def bounded_receive():
            return chunks.pop(0) if chunks else await receive()
        await self.app(scope, bounded_receive, send)

app = FastAPI(title='JARVIS Backend API')

@app.middleware('http')
async def authentication(request: Request, call_next):
    public = request.url.path in ('/api/health', '/api/ready', '/api/session/login')
    token = None
    try:
        origin = request.headers.get('origin')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in ALLOWED_ORIGINS:
            raise HTTPException(403, 'Origin not allowed')
        if not public and request.method != 'OPTIONS':
            token = owner_context.set(session_owner(request.cookies.get(COOKIE)))
        return await call_next(request)
    except HTTPException as exc:
        return JSONResponse({'detail': exc.detail}, exc.status_code)
    finally:
        if token is not None: owner_context.reset(token)

app.add_middleware(BodyLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                   allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['Content-Type'])
app.include_router(oauth_router)

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class LoginRequest(StrictModel):
    access_code: str = Field(min_length=32, max_length=256)

@app.post('/api/session/login')
def login(req: LoginRequest):
    user = authenticate(req.access_code)
    response = JSONResponse({'user_id': user})
    secure = os.getenv('COOKIE_SECURE', 'true') == 'true'
    response.set_cookie(COOKIE, serializer().dumps({'user_id': user, 'session_id': secrets.token_urlsafe(24)}), httponly=True, secure=secure,
                        samesite='none' if secure else 'lax', max_age=86400, path='/')
    return response

@app.get('/api/session')
def session(): return {'user_id': owner_id()}

@app.post('/api/session/logout')
def logout():
    response = JSONResponse({'status': 'signed_out'})
    response.delete_cookie(COOKIE, path='/')
    return response

class ToolExecution(StrictModel):
    tool_name: str = Field(max_length=100)
    arguments: dict
    approved: StrictBool
    action_id: str = Field(min_length=32, max_length=100)
    @model_validator(mode='after')
    def valid_tool(self):
        registry.validate(self.tool_name, self.arguments)
        if not registry.get_tool(self.tool_name)['requires_confirmation']:
            raise ValueError('This tool does not accept confirmations')
        return self

class ChatRequest(StrictModel):
    message: str = Field(default='', max_length=MAX_CHAT_CHARS)
    conversation_id: UUID | None = None
    web_mode: bool = False
    tool_execution: ToolExecution | None = None
    @model_validator(mode='after')
    def valid_message(self):
        self.message = self.message.strip()
        if not self.message and not self.tool_execution: raise ValueError('Message cannot be blank')
        if self.tool_execution and not self.conversation_id: raise ValueError('Confirmation needs a conversation')
        if self.tool_execution and self.message: raise ValueError('Confirmation cannot include a new message')
        return self

class CreateConversationRequest(StrictModel):
    title: str = Field(default='New Conversation', max_length=120)
    @field_validator('title')
    @classmethod
    def valid_title(cls, value):
        if not value.strip(): raise ValueError('Title cannot be blank')
        return value.strip()

class MessageRequest(StrictModel):
    role: Literal['user', 'assistant', 'system']
    content: str = Field(min_length=1, max_length=MAX_CHAT_CHARS)
    @field_validator('content')
    @classmethod
    def valid_content(cls, value):
        if not value.strip(): raise ValueError('Content cannot be blank')
        return value

@app.get('/api/health')
def health_check(): return {'status': 'ONLINE'}

@app.get('/api/ready')
def readiness():
    try:
        serializer()
        if not GROQ_API_KEY or not DATABASE_URL or not os.getenv('AUTH_USERS'): raise ValueError()
        with memory.transaction() as cur: cur.execute('SELECT 1;')
    except Exception:
        return JSONResponse({'status': 'NOT_READY'}, 503)
    return {'status': 'READY'}

@app.get('/api/conversations')
def conversations(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000)):
    return memory.list_conversations(limit, offset)

@app.post('/api/conversations')
def create_conversation(req: CreateConversationRequest):
    return {'id': memory.create_conversation(req.title), 'title': req.title}

@app.get('/api/conversations/{conversation_id}')
def get_conversation(conversation_id: UUID):
    return {'conversation': memory.get_conversation(conversation_id), 'messages': memory.get_recent_messages(conversation_id, 100)}

@app.delete('/api/conversations/{conversation_id}')
def delete_conversation(conversation_id: UUID):
    memory.delete_conversation(conversation_id)
    return {'status': 'deleted'}

@app.post('/api/conversations/{conversation_id}/messages')
def add_message(conversation_id: UUID, req: MessageRequest):
    return {'status': 'success', 'data': memory.add_message(conversation_id, req.role, req.content)}

@app.post('/api/jarvis/chat')
def chat(req: ChatRequest):
    cid = str(req.conversation_id) if req.conversation_id else None
    if cid:
        memory.get_conversation(cid)
        if not req.tool_execution: memory.add_message(cid, 'user', req.message)
    else:
        cid = memory.create_conversation(req.message[:30], first_message=req.message)
    try:
        response, tool_call = generate_response(req.message, cid, req.tool_execution.model_dump() if req.tool_execution else None, message_saved=True)
    except PermissionError:
        raise HTTPException(403, 'Tool permission or approval denied') from None
    except ValueError:
        raise HTTPException(422, 'Invalid tool request') from None
    audio = None
    if req.web_mode and response:
        try:
            import tts
            audio = tts.generate_audio(response)
        except Exception as exc:
            safe_error(exc)
    return {'conversation_id': cid, 'response': response, 'audio': base64.b64encode(audio).decode() if audio else None, 'tool_call': tool_call}

@app.post('/api/jarvis/transcribe')
async def transcribe(file: UploadFile = File(...)):
    mime = (file.content_type or '').split(';')[0].lower()
    if mime not in AUDIO_TYPES: raise HTTPException(415, 'Unsupported audio type')
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=AUDIO_TYPES[mime], delete=False) as output:
            path, size = output.name, 0
            while chunk := await file.read(65536):
                size += len(chunk)
                if size > MAX_AUDIO_BYTES: raise HTTPException(413, 'Audio upload too large')
                output.write(chunk)
        if not size: raise HTTPException(422, 'Audio upload is empty')
        if not GROQ_API_KEY: raise HTTPException(503, 'Transcription is not configured')
        def perform():
            with open(path, 'rb') as audio:
                return Groq(api_key=GROQ_API_KEY, timeout=30, max_retries=0).audio.transcriptions.create(file=(os.path.basename(path), audio), model='whisper-large-v3')
        result = await run_in_threadpool(perform)
        return {'text': result.text.strip()}
    except HTTPException: raise
    except Exception as exc:
        safe_error(exc)
        raise HTTPException(502, 'Transcription failed. Please try again.') from None
    finally:
        await file.close()
        if path: os.unlink(path)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
