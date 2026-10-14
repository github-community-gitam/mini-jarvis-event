import base64
import hashlib
import json
import os
import socket
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import memory
import server
import brain
import integrations
import oauth
from actions import issue_record, consume_record
from security import owner_context, serializer, COOKIE
from tool_registry import registry, ToolRegistry, ToolFailure, safe_error
from tests.mocks.providers import calendar_mock, github_mock, gmail_mock, drive_mock
from tools_calendar import list_events
from tools_github import list_open_issues, get_recent_commits, list_pull_requests
from tools_gmail import search_emails, read_email
from tools_drive import search_drive_files, read_drive_document

USER_A, USER_B = str(uuid4()), str(uuid4())

class Cursor:
    def __init__(self, connection): self.cursor = connection.cursor()
    def __enter__(self): return self
    def __exit__(self, *args): self.cursor.close()
    def execute(self, sql, args=()):
        if 'INSERT INTO messages (conversation_id, role, content)' in sql:
            sql = sql.replace('(conversation_id, role, content)', '(conversation_id, role, content, created_at)').replace('VALUES (%s, %s, %s)', 'VALUES (%s, %s, %s, %s)')
            args = (*args, datetime.now(timezone.utc).isoformat())
        sql = sql.replace('%s', '?').replace('ILIKE', 'LIKE')
        self.cursor.execute(sql, tuple(str(x) if isinstance(x, datetime) else x for x in args))
    def fetchone(self):
        row = self.cursor.fetchone(); return dict(row) if row else None
    def fetchall(self): return [dict(row) for row in self.cursor.fetchall()]

class Connection:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.row_factory = sqlite3.Row
    def cursor(self): return Cursor(self.db)
    def commit(self): self.db.commit()
    def rollback(self): self.db.rollback()
    def close(self): self.db.close()

@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.db')
    with sqlite3.connect(path) as conn:
        conn.executescript('''
        CREATE TABLE conversations (id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), user_id TEXT, title TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE messages (id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))), conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE user_integrations (user_id TEXT, integration_name TEXT, access_token TEXT, refresh_token TEXT, expires_at TEXT, scopes TEXT,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, integration_name));
        CREATE TABLE pending_actions (id TEXT PRIMARY KEY, user_id TEXT, kind TEXT, payload TEXT, binding TEXT, expires_at TEXT);
        ''')
    monkeypatch.setattr(memory, 'get_db_connection', lambda: Connection(path))
    token = owner_context.set(USER_A)
    yield path
    owner_context.reset(token)

@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv('SESSION_SECRET', 'offline-test-secret-' * 3)
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('AUTH_USERS', json.dumps({hashlib.sha256(('a'*40).encode()).hexdigest(): USER_A}))
    client = TestClient(server.app)
    client.cookies.set(COOKIE, serializer().dumps({'user_id': USER_A}))
    # UUID defaults in PostgreSQL are canonical; reproduce that in SQLite fixtures.
    original = memory.create_conversation
    def create(*args, **kwargs):
        cid = original(*args, **kwargs)
        from uuid import UUID
        canonical = str(UUID(cid))
        with sqlite3.connect(db) as conn:
            conn.execute('UPDATE conversations SET id=? WHERE id=?', (canonical, cid))
            conn.execute('UPDATE messages SET conversation_id=? WHERE conversation_id=?', (canonical, cid))
        return canonical
    monkeypatch.setattr(memory, 'create_conversation', create)
    monkeypatch.setattr(brain, 'GROQ_API_KEY', 'offline')
    monkeypatch.setattr(server, 'GROQ_API_KEY', 'offline')
    monkeypatch.setattr('tts.generate_audio', lambda text: b'audio')
    return client

def new_chat(client):
    res = client.post('/api/conversations', json={'title':' Test '})
    assert res.status_code == 200
    return res.json()['id']

@pytest.mark.parametrize('message', ['', ' ', '\n\t'])
def test_blank_chat(client, message):
    assert client.post('/api/jarvis/chat', json={'message':message}).status_code == 422

@pytest.mark.parametrize('title', ['', '  ', 'x'*121])
def test_titles(client, title):
    assert client.post('/api/conversations', json={'title':title}).status_code == 422

def test_missing_and_owned_conversation(client):
    cid = new_chat(client)
    assert client.get('/api/conversations/'+cid).json()['conversation']['title'] == 'Test'
    missing = str(uuid4())
    assert client.get('/api/conversations/'+missing).status_code == 404
    assert client.delete('/api/conversations/'+missing).status_code == 404
    assert client.delete('/api/conversations/'+cid).status_code == 200
    assert client.get('/api/conversations/'+cid).status_code == 404

@pytest.mark.parametrize('role', ['tool', '', 'admin'])
def test_bad_roles(client, role):
    cid = new_chat(client)
    assert client.post(f'/api/conversations/{cid}/messages', json={'role':role,'content':'Hi'}).status_code == 422
    assert client.get('/api/conversations/'+cid).json()['messages'] == []

@pytest.mark.parametrize('content', ['', ' \n'])
def test_empty_direct_message(db, content):
    with pytest.raises(ValueError): memory.add_message('unused', 'user', content)

def test_history_limit_order_activity_and_pagination(client, db):
    cid = new_chat(client)
    other = new_chat(client)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE conversations SET updated_at='2000-01-01' WHERE id=?", (cid,))
        for i in range(110):
            conn.execute('INSERT INTO messages(id,conversation_id,role,content,created_at) VALUES(?,?,?,?,?)', (f'{i:05}', cid,'user',str(i),f'2020-01-01T00:{i//60:02}:{i%60:02}'))
    rows = client.get('/api/conversations/'+cid).json()['messages']
    assert [r['content'] for r in rows] == [str(i) for i in range(10,110)]
    assert client.get('/api/conversations?limit=1').json()[0]['id'] == other
    with sqlite3.connect(db) as conn: conn.execute("UPDATE conversations SET updated_at='2001-01-01' WHERE id=?", (other,))
    assert client.post(f'/api/conversations/{cid}/messages', json={'role':'user','content':'new'}).status_code == 200
    assert client.get('/api/conversations?limit=1').json()[0]['id'] == cid
    assert client.get('/api/conversations?limit=1&offset=1').json()[0]['id'] == other
    for params in ('limit=0','limit=101','offset=-1'): assert client.get('/api/conversations?'+params).status_code == 422
    assert client.get('/api/conversations?offset=50').json() == []

def test_cross_user_isolation(client, db):
    cid = new_chat(client)
    memory.add_message(cid, 'user', 'confidential assignment')
    integrations.save_integration_token('google','secret-a','refresh',None,'scope')
    client.cookies.set(COOKIE, serializer().dumps({'user_id': USER_B}))
    assert client.get('/api/conversations').json() == []
    for method, path, payload in [('get',f'/api/conversations/{cid}',None),('delete',f'/api/conversations/{cid}',None),('post',f'/api/conversations/{cid}/messages',{'role':'user','content':'attack'}),('post','/api/jarvis/chat',{'message':'attack','conversation_id':cid})]:
        kwargs = {'json':payload} if payload else {}
        assert getattr(client,method)(path,**kwargs).status_code == 404
    token = owner_context.set(USER_B)
    try:
        assert integrations.get_integration_token('google') is None
        assert memory.search_previous_conversations('assignment') == []
        integrations.save_integration_token('google','secret-b',None,None,'scope')
        integrations.remove_integration('google')
    finally: owner_context.reset(token)
    assert integrations.get_integration_token('google')['access_token'] == 'secret-a'

def test_atomic_create_and_delete_rollback(client, db):
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON messages BEGIN SELECT RAISE(ABORT, 'failure'); END")
    assert client.post('/api/jarvis/chat', json={'message':'hello'}).status_code == 503
    assert client.get('/api/conversations').json() == []
    with sqlite3.connect(db) as conn: conn.execute('DROP TRIGGER fail_insert')
    cid = new_chat(client); memory.add_message(cid,'user','hello')
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON messages BEGIN SELECT RAISE(ABORT, 'failure'); END")
    assert client.delete('/api/conversations/'+cid).status_code == 503
    assert len(client.get('/api/conversations/'+cid).json()['messages']) == 1
    with sqlite3.connect(db) as conn: conn.execute('DROP TRIGGER fail_delete')
    client.delete('/api/conversations/'+cid)
    with sqlite3.connect(db) as conn: assert conn.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 0

def test_offline_and_health(client, monkeypatch):
    monkeypatch.setattr(memory,'get_db_connection',lambda: None)
    assert client.post('/api/jarvis/chat',json={'message':'hello'}).status_code == 503
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/ready').status_code == 503

def test_search_and_history_budgets(db):
    assert memory.search_keywords('!?! ') == []
    assert memory.search_keywords('hello hello, WORLD!') == ['hello','world']
    assert len(memory.search_keywords(' '.join('word'+str(i) for i in range(100)))) == 8
    assert len(memory.search_keywords('x'*1000)[0]) == 64
    result = brain.bounded_history([{'role':'user','content':'a'*1000},{'role':'assistant','content':'new'*10}],50)
    assert sum(len(r['content']) for r in result) == 50 and result[-1]['content'] == 'new'*10

@pytest.mark.parametrize('value', [0, -1, 51, True])
def test_provider_limits(value):
    for fn,args in [(list_events,{'max_results':value}),(list_open_issues,{'repo_name':'mock-user/mock-repo','limit':value}),(get_recent_commits,{'repo_name':'mock-user/mock-repo','limit':value}),(list_pull_requests,{'repo_name':'mock-user/mock-repo','limit':value})]:
        with pytest.raises(ValueError): fn(**args)

@pytest.mark.parametrize('value',[1,50])
def test_provider_boundaries(value):
    assert isinstance(list_events(time_min='2026-01-01T00:00:00Z',max_results=value),str)
    assert 'Mock Issue' in list_open_issues('mock-user/mock-repo', value)

def test_calendar_utc(monkeypatch):
    service = MagicMock(); service.events.return_value.list.return_value.execute.return_value={'items':[]}
    monkeypatch.setattr('tools_calendar.get_calendar_service', lambda: service)
    list_events()
    value = service.events.return_value.list.call_args.kwargs['timeMin']
    assert datetime.fromisoformat(value).utcoffset() == timedelta(0)

def test_github_metadata_and_filters():
    data = github_mock.state['repos']['mock-user/mock-repo']
    data['issues'].insert(0,{'number':99,'title':'PR disguise','user':{'login':'test'},'pull_request':{},'state':'open'})
    assert 'Mock Issue' in list_open_issues('mock-user/mock-repo',1)
    assert 'PR disguise' not in list_open_issues('mock-user/mock-repo',1)
    data['commits'][0]['commit']={'message':'','author':None}
    assert 'Unknown author' in get_recent_commits('mock-user/mock-repo')
    with pytest.raises(ValueError): list_pull_requests('mock-user/mock-repo','nonsense')
    assert 'No closed' in list_pull_requests('mock-user/mock-repo','closed')
    assert len(github_mock.get_repo('mock-user/mock-repo').get_issues(state='closed')) == 0
    data['issues']=[]; data['pulls']=[]; data['commits']=[]
    assert 'No open' in list_open_issues('mock-user/mock-repo')

def test_gmail_nested_malformed_and_queries():
    assert 'msg_1' in search_emails('from:sender@mock.com')
    assert 'No emails' in search_emails('subject:missing')
    assert 'No emails' in search_emails('other text')
    with pytest.raises(ValueError): search_emails('from:')
    payload={'headers':[None,{}, {'name':None}, {'name':'Subject','value':None}], 'parts':[
        {'mimeType':'text/plain','body':{'data':'$$$'}}, {'parts':[{'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(b'nested').decode()}}]}]}
    gmail_mock.state['messages'][0]['payload']=payload
    assert 'nested' in read_email('msg_1') and 'No Subject' in read_email('msg_1')
    payload['parts']=[{'mimeType':'text/html','body':{'data':'abc'}}]
    assert 'No readable' in read_email('msg_1')

def test_drive_pagination_read_and_failures():
    first=search_drive_files('',1); second=search_drive_files('',1,first['next_page_token'])
    assert first['files'][0]['id'] != second['files'][0]['id']
    assert 'Document text' in read_drive_document('doc1')
    assert 'Plain text' in read_drive_document('text1')
    assert read_drive_document('bin1')['error']['code']=='unsupported_file_type'
    assert 'Error' in read_drive_document('missing')
    drive_mock.set_failure('secret-token')
    assert 'secret-token' not in read_drive_document('doc1')

def test_mock_calendar_boundaries_and_reset():
    events=calendar_mock.events().list('primary',timeMin='2026-10-10T11:00:00Z',timeMax='2026-10-12T14:00:00Z').execute()['items']
    assert events==[]
    events=calendar_mock.events().list('primary',timeMin='2026-10-10T10:30:00Z',timeMax='2026-10-12T14:01:00Z').execute()['items']
    assert [e['id'] for e in events]==['evt_1','evt_2']
    for provider in [calendar_mock,github_mock,gmail_mock,drive_mock]:
        provider.set_failure('oops'); provider.latency_ms=1; provider.state.clear(); provider.reset()
        assert provider.state and not provider.should_fail and provider.latency_ms==0 and provider.fail_reason is None
    assert calendar_mock.event_id_counter==3

def test_network_patch_cleanup():
    before=socket.socket
    from tests.conftest import disable_network
    monkeypatch=pytest.MonkeyPatch(); fixture=disable_network.__wrapped__(monkeypatch)
    try:
        next(fixture)
        raise RuntimeError('deliberate test body failure')
    except RuntimeError: pass
    finally: fixture.close()
    assert socket.socket is before

def test_session_csrf_and_body_limits(client, monkeypatch):
    client.cookies.clear()
    assert client.get('/api/conversations').status_code==401
    assert client.post('/api/session/login',json={'access_code':'a'*40}).status_code==200
    assert client.get('/api/session').json()['user_id']==USER_A
    assert client.post('/api/conversations',json={},headers={'origin':'https://attacker.invalid'}).status_code==403
    assert client.post('/api/jarvis/chat',json={'message':'x'*10001}).status_code==422
    assert client.post('/api/jarvis/chat',content=b'x'*(server.MAX_BODY_BYTES+1)).status_code==413
    assert client.post('/api/session/logout').status_code==200
    assert client.get('/api/session').status_code==401

@pytest.mark.parametrize('mime,data,code',[('text/plain',b'abc',415),('audio/webm',b'',422),('audio/webm',b'x'*101,413)])
def test_upload_validation(client, monkeypatch,mime,data,code):
    monkeypatch.setattr(server,'MAX_AUDIO_BYTES',100)
    assert client.post('/api/jarvis/transcribe',files={'file':('../../evil',data,mime)}).status_code==code

def test_upload_temp_cleanup_and_uniqueness(client, monkeypatch):
    paths=[]
    def transcribe(**kwargs):
        path=kwargs['file'][1].name; assert os.path.exists(path); paths.append(path)
        return NS(text=' hello ')
    monkeypatch.setattr(server,'Groq',lambda **kwargs:NS(audio=NS(transcriptions=NS(create=transcribe))))
    for _ in range(2):
        res=client.post('/api/jarvis/transcribe',files={'file':('../../evil.webm',b'audio','audio/webm')})
        assert res.json()=={'text':'hello'}
    assert len(set(paths))==2 and all(not os.path.exists(p) for p in paths)
    def fail(**kwargs): paths.append(kwargs['file'][1].name); raise RuntimeError('secret token')
    monkeypatch.setattr(server,'Groq',lambda **kwargs:NS(audio=NS(transcriptions=NS(create=fail))))
    res=client.post('/api/jarvis/transcribe',files={'file':('a.webm',b'audio','audio/webm')})
    assert res.status_code==502 and 'secret' not in res.text and not os.path.exists(paths[-1])

@pytest.mark.parametrize('args',[None,[],{'unknown':1},{'title':'only title'}])
def test_schema_validation(args):
    with pytest.raises(ValueError): registry.validate('create_calendar_event',args)

def test_depth_and_size():
    from tool_registry import validate_bounds
    value={}
    for _ in range(10): value={'child':value}
    with pytest.raises(ValueError): validate_bounds(value)
    with pytest.raises(ValueError): validate_bounds({'text':'x'*20000})

def event_args(): return {'title':'Meeting','start_time':'2026-10-15T10:00:00Z','end_time':'2026-10-15T11:00:00Z'}

def allow_tools(monkeypatch):
    monkeypatch.setattr('tool_registry.get_integration_token',lambda provider:{'access_token':'fake','scopes':'https://www.googleapis.com/auth/calendar.events'})

def fake_llm(monkeypatch, messages):
    create=MagicMock(side_effect=[NS(choices=[NS(message=m)]) for m in messages])
    monkeypatch.setattr(brain,'Groq',lambda **kwargs:NS(chat=NS(completions=NS(create=create))))
    return create

def tool_message(arguments=None):
    call=NS(id='call1',function=NS(name='create_calendar_event',arguments=json.dumps(event_args()) if arguments is None else arguments))
    call.model_dump=lambda:{'id':'call1','type':'function','function':{'name':call.function.name,'arguments':call.function.arguments}}
    return NS(content=None,tool_calls=[call])

def plain_message(text='Hello'): return NS(content=text,tool_calls=None)

def test_end_to_end_chat_history_and_approval(client,monkeypatch):
    allow_tools(monkeypatch)
    llm=fake_llm(monkeypatch,[plain_message('Welcome'),tool_message(),plain_message('Created')])
    res=client.post('/api/jarvis/chat',json={'message':'hello','web_mode':True})
    assert res.status_code==200
    cid=res.json()['conversation_id']; assert res.json()['audio']==base64.b64encode(b'audio').decode()
    assert [r['content'] for r in client.get('/api/conversations/'+cid).json()['messages']]==['hello','Welcome']
    req=client.post('/api/jarvis/chat',json={'message':'create event','conversation_id':cid}).json()['tool_call']
    assert len(calendar_mock.state['events'])==2
    payload={'message':'','conversation_id':cid,'tool_execution':{k:req[k] for k in ('tool_name','arguments','action_id')}}
    payload['tool_execution']['approved']=True
    assert client.post('/api/jarvis/chat',json=payload).status_code==200
    assert len(calendar_mock.state['events'])==3
    assert client.post('/api/jarvis/chat',json=payload).status_code==409
    assert len(calendar_mock.state['events'])==3

def test_canceled_and_forged_approvals(client,monkeypatch):
    allow_tools(monkeypatch); fake_llm(monkeypatch,[tool_message(),plain_message('Canceled')])
    cid=new_chat(client)
    req=client.post('/api/jarvis/chat',json={'message':'event','conversation_id':cid}).json()['tool_call']
    payload={'conversation_id':cid,'tool_execution':{k:req[k] for k in ('tool_name','arguments','action_id')}}
    payload['tool_execution']['approved']=False
    assert client.post('/api/jarvis/chat',json=payload).status_code==200
    assert len(calendar_mock.state['events'])==2
    payload['tool_execution']['approved']=True
    assert client.post('/api/jarvis/chat',json=payload).status_code==409
    payload['tool_execution'].pop('action_id')
    assert client.post('/api/jarvis/chat',json=payload).status_code==422
    payload['tool_execution']['action_id']='x'*40
    payload['tool_execution']['tool_name']='unknown'
    assert client.post('/api/jarvis/chat',json=payload).status_code==422

@pytest.mark.parametrize('arguments',['{','[]','null','{"title":"missing"}'])
def test_malformed_llm_tool_args(client,monkeypatch,arguments):
    fake_llm(monkeypatch,[tool_message(arguments)])
    res=client.post('/api/jarvis/chat',json={'message':'event'})
    assert res.status_code==200 and res.json()['tool_call'] is None
    assert len(calendar_mock.state['events'])==2

def test_missing_llm_and_failure(client,monkeypatch):
    monkeypatch.setattr(brain,'GROQ_API_KEY',None)
    assert 'not configured' in client.post('/api/jarvis/chat',json={'message':'hi'}).json()['response']
    monkeypatch.setattr(brain,'GROQ_API_KEY','fake')
    fake=MagicMock(); fake.chat.completions.create.side_effect=RuntimeError('token=secret')
    monkeypatch.setattr(brain,'Groq',lambda **kwargs:fake)
    res=client.post('/api/jarvis/chat',json={'message':'hi'})
    assert res.status_code==200 and 'secret' not in res.text

def test_permission_denials_and_retry_policy(db,monkeypatch):
    reg=ToolRegistry(); fn=MagicMock(return_value='ok')
    reg.register('read','read',{'type':'object','properties':{}},fn,required_permissions='google:scope')
    monkeypatch.setattr('tool_registry.get_integration_token',lambda provider:None)
    with pytest.raises(PermissionError): reg.execute('read',{})
    monkeypatch.setattr('tool_registry.get_integration_token',lambda provider:{'access_token':'fake','scopes':'other'})
    with pytest.raises(PermissionError): reg.execute('read',{})
    assert not fn.called
    monkeypatch.setattr('tool_registry.get_integration_token',lambda provider:{'access_token':'fake','scopes':'scope'})
    fn.side_effect=[RuntimeError('fail'),'ok']
    assert reg.execute('read',{})=='ok' and fn.call_count==2
    fn.reset_mock(); fn.side_effect=RuntimeError('secret')
    with pytest.raises(ToolFailure): reg.execute('read',{})
    assert fn.call_count==2
    reg.register('write','write',{'type':'object','properties':{}},fn,requires_confirmation=True,retries=10)
    assert reg.get_tool('write')['retries']==0
    with pytest.raises(PermissionError): reg.execute('write',{})
    action=issue_record('tool',{'tool_name':'write','arguments':{}},'conv')
    fn.reset_mock()
    with pytest.raises(ToolFailure): reg.execute('write',{},action,'conv')
    assert fn.call_count==1
    with pytest.raises(HTTPException): reg.execute('write',{},action,'conv')

def test_tool_timeout_no_overlap():
    reg=ToolRegistry(); finished=threading.Event(); started=threading.Event()
    def blocked(): started.set(); finished.wait(2); return 'late'
    reg.register('slow','slow',{'type':'object','properties':{}},blocked,timeout=.01,retries=2)
    try:
        with pytest.raises(ToolFailure,match='timed out'): reg.execute('slow',{})
        assert started.is_set()
    finally: finished.set()

def test_oauth_state_binding_expiry_and_owners(client,db):
    action=issue_record('oauth:github',{},'browser')
    with pytest.raises(HTTPException): consume_record(action,'oauth:github','other')
    assert consume_record(action,'oauth:github','browser')=={}
    with pytest.raises(HTTPException): consume_record(action,'oauth:github','browser')
    action=issue_record('oauth:google',{},'browser',ttl=-10)
    with pytest.raises(HTTPException): consume_record(action,'oauth:google','browser')
    action=issue_record('tool',{},'conv')
    token=owner_context.set(USER_B)
    try:
        with pytest.raises(HTTPException): consume_record(action,'tool','conv')
    finally: owner_context.reset(token)

def oauth_login(client, monkeypatch, provider):
    monkeypatch.setenv('GITHUB_CLIENT_ID','fake-client'); monkeypatch.setenv('GITHUB_CLIENT_SECRET','fake-secret')
    if provider=='google':
        flow=MagicMock(); flow.authorization_url.side_effect=lambda **kw:('https://google.invalid?state='+kw['state'],kw['state'])
        flow.credentials=NS(token='fake',refresh_token='refresh',expiry=None,scopes=['scope'],granted_scopes=None)
        monkeypatch.setattr(oauth,'google_flow',lambda:flow)
    from urllib.parse import urlparse,parse_qs
    res=client.get('/api/auth/'+provider+'/login',follow_redirects=False)
    return parse_qs(urlparse(res.headers['location']).query)['state'][0]

@pytest.mark.parametrize('provider',['google','github'])
def test_oauth_success_replay_and_missing_state(client,monkeypatch,provider):
    state=oauth_login(client,monkeypatch,provider)
    result=MagicMock(); result.json.return_value={'access_token':'fake','scope':''}
    monkeypatch.setattr(oauth.requests,'post',lambda *a,**kw:result)
    res=client.get(f'/api/auth/{provider}/callback?code=fake&state={state}',follow_redirects=False)
    assert res.status_code==307 and 'status=success' in res.headers['location']
    assert client.get(f'/api/auth/{provider}/callback?code=fake&state={state}').status_code==409
    assert client.get(f'/api/auth/{provider}/callback?code=fake').status_code==400
    assert client.get(f'/api/auth/{provider}/callback?code=fake&state=wrong').status_code==409

@pytest.mark.parametrize('failure',['timeout','400','500','json','missing','database'])
def test_oauth_sanitized_failures(client,monkeypatch,failure,caplog):
    state=oauth_login(client,monkeypatch,'github')
    post=MagicMock(); result=post.return_value
    result.json.return_value={'access_token':'sensitive-token'}
    if failure=='timeout': post.side_effect=TimeoutError('secret-code')
    elif failure in ('400','500'): result.raise_for_status.side_effect=RuntimeError('secret-body')
    elif failure=='json': result.json.side_effect=ValueError('secret-body')
    elif failure=='missing': result.json.return_value={'error':'sensitive-token'}
    elif failure=='database': monkeypatch.setattr(oauth,'save_integration_token',lambda *args:False)
    monkeypatch.setattr(oauth.requests,'post',post)
    res=client.get('/api/auth/github/callback?code=secret-code&state='+state,follow_redirects=False)
    assert res.status_code==502
    assert 'secret-code' not in res.text and 'sensitive-token' not in res.text and 'secret-body' not in caplog.text
    assert post.call_args.kwargs['timeout']==10

def test_github_minimal_scopes(client,monkeypatch):
    oauth_login(client,monkeypatch,'github')
    res=client.get('/api/auth/github/login',follow_redirects=False)
    assert 'scope=&' in res.headers['location'] or res.headers['location'].endswith('scope=')
    monkeypatch.setenv('GITHUB_PRIVATE_REPOS','true')
    assert 'scope=repo' in client.get('/api/auth/github/login',follow_redirects=False).headers['location']

@pytest.mark.parametrize('mode',['valid','expired','revoked','transient'])
def test_google_refresh(db,monkeypatch,mode):
    from google.auth.exceptions import RefreshError
    creds=MagicMock(); creds.expired=mode!='valid'; creds.refresh_token='rotated'; creds.token='new'; creds.expiry=None; creds.scopes=['scope']
    if mode=='revoked': creds.refresh.side_effect=RefreshError('revoked')
    if mode=='transient': creds.refresh.side_effect=RefreshError('temporary',retryable=True)
    monkeypatch.setattr(integrations,'Credentials',lambda **kwargs:creds)
    saved=MagicMock(return_value=True); removed=MagicMock()
    monkeypatch.setattr(integrations,'save_integration_token',saved); monkeypatch.setattr(integrations,'remove_integration',removed)
    data={'access_token':'old','refresh_token':'oldrefresh','expires_at':datetime.now(timezone.utc)-timedelta(hours=1),'scopes':'scope'}
    if mode in ('revoked','transient'):
        with pytest.raises(PermissionError): integrations.google_credentials(data)
        assert removed.called==(mode=='revoked')
    else:
        integrations.google_credentials(data)
        assert creds.refresh.called==(mode=='expired')
        assert saved.called==(mode=='expired')
        if saved.called: assert saved.call_args.args[2]=='rotated'

def test_concurrent_uploads_never_share_paths(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    paths=[]; lock=threading.Lock()
    def transcribe(**kwargs):
        path=kwargs['file'][1].name
        with lock: paths.append(path)
        assert os.path.exists(path)
        return NS(text='ok')
    monkeypatch.setattr(server,'Groq',lambda **kwargs:NS(audio=NS(transcriptions=NS(create=transcribe))))
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.post('/api/jarvis/transcribe',files={'file':('../same.webm',b'abc','audio/webm')}),range(4)))
    assert all(r.status_code==200 for r in responses)
    assert len(set(paths))==4 and all(not os.path.exists(p) for p in paths)

def test_concurrent_approval_consumption(db):
    from concurrent.futures import ThreadPoolExecutor
    action=issue_record('tool',{'value':1},'conv')
    def consume(_):
        token=owner_context.set(USER_A)
        try:
            try: return consume_record(action,'tool','conv')
            except HTTPException as exc: return exc.status_code
        finally: owner_context.reset(token)
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(consume,range(4)))
    assert results.count({'value':1})==1 and results.count(409)==3

def test_mock_reset_restores_generated_ids_after_success_and_failure():
    calendar_mock.events().insert('primary',{'summary':'Created'}).execute()
    assert calendar_mock.event_id_counter==4
    calendar_mock.set_failure('failure')
    with pytest.raises(RuntimeError): calendar_mock.events().insert('primary',{}).execute()
    calendar_mock.reset()
    created=calendar_mock.events().insert('primary',{'summary':'Again'}).execute()
    assert created['id']=='evt_3'

def test_refresh_persistence_failure_never_returns_unsaved_credentials(db,monkeypatch):
    creds=MagicMock();creds.expired=True;creds.refresh_token='new';creds.token='new';creds.expiry=None;creds.scopes=['scope']
    monkeypatch.setattr(integrations,'Credentials',lambda **kw:creds)
    monkeypatch.setattr(integrations,'save_integration_token',lambda *a:False)
    with pytest.raises(RuntimeError): integrations.google_credentials({'access_token':'old','refresh_token':'old','scopes':'scope'})

def test_distinct_browser_sessions_have_distinct_oauth_bindings(client):
    first=client.post('/api/session/login',json={'access_code':'a'*40}).cookies.get(COOKIE)
    second=client.post('/api/session/login',json={'access_code':'a'*40}).cookies.get(COOKIE)
    assert first!=second
