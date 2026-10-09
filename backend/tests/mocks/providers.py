import copy

class BaseMockProvider:
    def __init__(self):
        self.state = {}
        self.should_fail = False
        self.fail_reason = None
        self.latency_ms = 0

    def reset(self):
        self.state = {}
        self.should_fail = False
        self.fail_reason = None
        self.latency_ms = 0

    def set_failure(self, reason: str = "SIMULATED_FAILURE"):
        self.should_fail = True
        self.fail_reason = reason

    def check_failure(self):
        if self.should_fail:
            raise Exception(f"Mock Provider Error: {self.fail_reason}")

class MockCalendarService(BaseMockProvider):
    def __init__(self):
        super().__init__()
        self.reset()
        
    def reset(self):
        super().reset()
        self.state = {
            "events": [
                {"id": "evt_1", "summary": "Mock Review", "start": {"dateTime": "2026-10-10T10:00:00Z"}},
                {"id": "evt_2", "summary": "Mock Dentist", "start": {"dateTime": "2026-10-12T14:00:00Z"}}
            ]
        }
        self.event_id_counter = 3

    # Simulated Google API client structure
    def events(self):
        return self

    def list(self, calendarId, timeMin=None, timeMax=None, maxResults=10, singleEvents=True, orderBy=None):
        self.check_failure()
        class RequestBuilder:
            def __init__(self, parent):
                self.parent = parent
            def execute(self):
                return {"items": self.parent.state["events"][:maxResults]}
        return RequestBuilder(self)

    def insert(self, calendarId, body):
        self.check_failure()
        class RequestBuilder:
            def __init__(self, parent, body):
                self.parent = parent
                self.body = body
            def execute(self):
                # Simulated idempotency or duplicate check can be added here
                new_evt = copy.deepcopy(self.body)
                new_evt["id"] = f"evt_{self.parent.event_id_counter}"
                new_evt["htmlLink"] = f"https://mock.calendar/events/{new_evt['id']}"
                self.parent.event_id_counter += 1
                self.parent.state["events"].append(new_evt)
                return new_evt
        return RequestBuilder(self, body)

class MockGithubClient(BaseMockProvider):
    def __init__(self):
        super().__init__()
        self.reset()
        
    def reset(self):
        super().reset()
        self.state = {
            "repos": {
                "mock-user/mock-repo": {
                    "full_name": "mock-user/mock-repo",
                    "description": "A mock repository",
                    "stargazers_count": 42,
                    "forks_count": 5,
                    "language": "Python",
                    "default_branch": "main",
                    "issues": [
                        {"number": 1, "title": "Mock Issue", "user": {"login": "mock-user"}, "pull_request": None}
                    ],
                    "commits": [
                        {"sha": "abcdef1", "commit": {"message": "Initial commit", "author": {"name": "mock-user"}}}
                    ]
                }
            }
        }

    def get_repo(self, repo_name):
        self.check_failure()
        if repo_name not in self.state["repos"]:
            raise Exception("404 Not Found")
        
        repo_data = self.state["repos"][repo_name]
        
        class MockRepo:
            def __init__(self, data):
                self.full_name = data["full_name"]
                self.description = data["description"]
                self.stargazers_count = data["stargazers_count"]
                self.forks_count = data["forks_count"]
                self.language = data["language"]
                self.default_branch = data["default_branch"]
                self._data = data
                
            def get_issues(self, state="open"):
                class MockIssue:
                    def __init__(self, i_data):
                        self.number = i_data["number"]
                        self.title = i_data["title"]
                        class MockUser:
                            login = i_data["user"]["login"]
                        self.user = MockUser()
                        self.pull_request = i_data["pull_request"]
                return [MockIssue(i) for i in self._data["issues"]]
                
            def get_commits(self, **kwargs):
                class MockCommitObj:
                    def __init__(self, c_data):
                        self.sha = c_data["sha"]
                        class CommitDetails:
                            message = c_data["commit"]["message"]
                            class Author:
                                name = c_data["commit"]["author"]["name"]
                            author = Author()
                        self.commit = CommitDetails()
                return [MockCommitObj(c) for c in self._data["commits"]]
                
        return MockRepo(repo_data)

class MockGmailService(BaseMockProvider):
    # Simulated simple Gmail client
    def __init__(self):
        super().__init__()
        self.reset()
        
    def reset(self):
        super().reset()
        self.state = {
            "messages": [
                {"id": "msg_1", "snippet": "Mock snippet", "headers": {"Subject": "Mock", "From": "sender@mock.com", "Date": "2026-10-10"}}
            ]
        }
    def users(self): return self
    def messages(self): return self
    
    def list(self, userId, q=None, maxResults=5):
        self.check_failure()
        class RequestBuilder:
            def __init__(self, parent): self.parent = parent
            def execute(self): return {"messages": [{"id": m["id"]} for m in self.parent.state["messages"]]}
        return RequestBuilder(self)
        
    def get(self, userId, id, format='metadata', metadataHeaders=None):
        self.check_failure()
        class RequestBuilder:
            def __init__(self, parent, m_id, fmt):
                self.parent = parent
                self.m_id = m_id
                self.fmt = fmt
            def execute(self):
                msg = next((m for m in self.parent.state["messages"] if m["id"] == self.m_id), None)
                if not msg: raise Exception("404")
                
                payload = {"headers": [{"name": k, "value": v} for k, v in msg["headers"].items()]}
                if self.fmt == 'full':
                    import base64
                    payload["body"] = {"data": base64.urlsafe_b64encode(b"Mock body content").decode('utf-8')}
                
                return {"id": self.m_id, "snippet": msg["snippet"], "payload": payload}
        return RequestBuilder(self, id, format)

class MockDriveService(BaseMockProvider):
    # Simulated Drive client
    pass

# Global instances for the test run
calendar_mock = MockCalendarService()
github_mock = MockGithubClient()
gmail_mock = MockGmailService()
drive_mock = MockDriveService()
