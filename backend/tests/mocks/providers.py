"""Deterministic provider doubles. Unsupported query syntax fails explicitly."""
import base64
import copy
import shlex
import time
import re
from datetime import datetime, timezone
from types import SimpleNamespace

class Request:
    def __init__(self, provider, operation): self.provider, self.operation = provider, operation
    def execute(self):
        self.provider.check_failure()
        return copy.deepcopy(self.operation())

class BaseMockProvider:
    def __init__(self): self.reset()
    def reset(self):
        self.state = {}; self.should_fail = False; self.fail_reason = None; self.latency_ms = 0
    def set_failure(self, reason='SIMULATED_FAILURE'): self.should_fail, self.fail_reason = True, reason
    def check_failure(self):
        if self.latency_ms: time.sleep(self.latency_ms / 1000)
        if self.should_fail: raise RuntimeError(self.fail_reason)

def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return dt.replace(tzinfo=timezone.utc) if not dt.tzinfo else dt

class MockCalendarService(BaseMockProvider):
    def reset(self):
        super().reset()
        self.state = {'events': [
            {'id': 'evt_1', 'summary': 'Mock Review', 'start': {'dateTime': '2026-10-10T10:00:00Z'}, 'end': {'dateTime': '2026-10-10T11:00:00Z'}},
            {'id': 'evt_2', 'summary': 'Mock Dentist', 'start': {'dateTime': '2026-10-12T14:00:00Z'}, 'end': {'dateTime': '2026-10-12T15:00:00Z'}}]}
        self.event_id_counter = 3
    def events(self): return self
    def list(self, calendarId, timeMin=None, timeMax=None, maxResults=10, singleEvents=True, orderBy=None):
        def operation():
            def start(event): return timestamp(event['start'].get('dateTime', event['start'].get('date')))
            def end(event): return timestamp(event.get('end', event['start']).get('dateTime', event.get('end', event['start']).get('date')))
            events = [e for e in self.state['events'] if (not timeMin or end(e) > timestamp(timeMin)) and (not timeMax or start(e) < timestamp(timeMax))]
            return {'items': sorted(events, key=lambda e: (start(e), e['id']))[:maxResults]}
        return Request(self, operation)
    def insert(self, calendarId, body):
        def operation():
            event = copy.deepcopy(body); event['id'] = f'evt_{self.event_id_counter}'
            event['htmlLink'] = 'https://mock.calendar/events/' + event['id']
            self.event_id_counter += 1; self.state['events'].append(event)
            return event
        return Request(self, operation)

def obj(value):
    if isinstance(value, dict): return SimpleNamespace(**{k: obj(v) for k,v in value.items()})
    return value

class MockGithubClient(BaseMockProvider):
    def reset(self):
        super().reset()
        self.state = {'repos': {'mock-user/mock-repo': {
            'full_name': 'mock-user/mock-repo', 'description': 'A mock repository', 'stargazers_count': 42,
            'forks_count': 5, 'language': 'Python', 'default_branch': 'main',
            'issues': [{'number': 1, 'title': 'Mock Issue', 'user': {'login': 'mock-user'}, 'pull_request': None, 'state': 'open'}],
            'pulls': [{'number': 2, 'title': 'Mock PR', 'state': 'open', 'user': {'login': 'mock-user'}}],
            'commits': [{'sha': 'abcdef1', 'commit': {'message': 'Initial commit', 'author': {'name': 'mock-user'}}}]}}}
    def get_user(self): return self
    def get_repos(self, **kwargs):
        self.check_failure()
        return [self.get_repo(name) for name in sorted(self.state['repos'])]
    def get_repo(self, name):
        self.check_failure()
        if name not in self.state['repos']: raise RuntimeError('404 Not Found')
        data = self.state['repos'][name]; provider = self
        class Repo(SimpleNamespace):
            def get_issues(self, state='open'):
                provider.check_failure()
                return [obj(i) for i in data['issues'] if state == 'all' or i.get('state', 'open') == state]
            def get_commits(self, **kwargs):
                provider.check_failure()
                return [obj(c) for c in data['commits'] if not kwargs.get('sha') or c.get('branch', 'main') == kwargs['sha']]
            def get_pulls(self, state='open', **kwargs):
                provider.check_failure()
                return [obj(p) for p in data.get('pulls', []) if state == 'all' or p['state'] == state]
        return Repo(**data)

class MockGmailService(BaseMockProvider):
    def reset(self):
        super().reset()
        self.state = {'messages': [{'id': 'msg_1', 'snippet': 'Mock snippet', 'unread': True,
            'headers': {'Subject': 'Mock', 'From': 'sender@mock.com', 'Date': '2026-10-10'}}]}
    def users(self): return self
    def messages(self): return self
    def list(self, userId, q=None, maxResults=5):
        terms = shlex.split(q or '')
        for term in terms:
            if ':' in term and not term.startswith(('from:', 'subject:', 'is:')): raise ValueError('Unsupported mock query')
            if term.endswith(':') or (term.startswith('is:') and term != 'is:unread'): raise ValueError('Malformed mock query')
        def matches(msg):
            for term in terms:
                key, sep, value = term.partition(':')
                if key == 'is' and sep:
                    if not msg.get('unread'): return False
                else:
                    text = msg.get('headers', {}).get({'from':'From', 'subject':'Subject'}.get(key), '') if sep else str(msg)
                    if (value if sep else term).lower() not in str(text).lower(): return False
            return True
        return Request(self, lambda: {'messages': [{'id': m['id']} for m in self.state['messages'] if matches(m)][:maxResults]})
    def get(self, userId, id, format='metadata', metadataHeaders=None):
        def operation():
            msg = next((m for m in self.state['messages'] if m['id'] == id), None)
            if not msg: raise RuntimeError('404')
            payload = msg.get('payload', {'mimeType':'text/plain', 'headers':[{'name':k,'value':v} for k,v in msg.get('headers', {}).items()], 'body':{'data':base64.urlsafe_b64encode(b'Mock body content').decode()}})
            return {'id':id, 'snippet':msg.get('snippet',''), 'payload':payload}
        return Request(self, operation)

class MockDriveService(BaseMockProvider):
    def reset(self):
        super().reset()
        self.state = {'files': [
            {'id':'doc1','name':'Assignment','mimeType':'application/vnd.google-apps.document','content':b'Document text'},
            {'id':'text1','name':'Notes','mimeType':'text/plain','content':b'Plain text'},
            {'id':'bin1','name':'Picture','mimeType':'image/png','content':b'PNG'}]}
    def files(self): return self
    def list(self, q='', pageSize=5, fields=None, pageToken=None):
        def operation():
            files = self.state['files']
            if q:
                match = re.fullmatch(r"name contains '([^']*)'", q)
                if not match: raise ValueError('Unsupported mock Drive query')
                files = [f for f in files if match[1].lower() in f['name'].lower()]
            offset = int(pageToken or 0)
            if offset < 0: raise ValueError('Invalid page token')
            result = {'files':[{k:v for k,v in f.items() if k != 'content'} for f in files[offset:offset+pageSize]]}
            if offset + pageSize < len(files): result['nextPageToken'] = str(offset+pageSize)
            return result
        return Request(self, operation)
    def lookup(self, fileId):
        file = next((f for f in self.state['files'] if f['id'] == fileId), None)
        if not file: raise RuntimeError('404')
        return file
    def get(self, fileId, fields=None): return Request(self, lambda: {k:v for k,v in self.lookup(fileId).items() if k != 'content'})
    def get_media(self, fileId): return Request(self, lambda: self.lookup(fileId)['content'])
    def export_media(self, fileId, mimeType):
        def operation():
            file = self.lookup(fileId)
            if file['mimeType'] != 'application/vnd.google-apps.document' or mimeType != 'text/plain': raise ValueError('Unsupported export')
            return file['content']
        return Request(self, operation)

calendar_mock = MockCalendarService()
github_mock = MockGithubClient()
gmail_mock = MockGmailService()
drive_mock = MockDriveService()
