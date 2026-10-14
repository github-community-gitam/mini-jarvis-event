import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextvars import copy_context
from threading import BoundedSemaphore
from jsonschema import Draft202012Validator
from integrations import get_integration_token

MAX_ARGUMENT_BYTES = int(os.getenv('MAX_ARGUMENT_BYTES', '16384'))
MAX_ARGUMENT_DEPTH = int(os.getenv('MAX_ARGUMENT_DEPTH', '8'))
executor = ThreadPoolExecutor(max_workers=8)
slots = BoundedSemaphore(8)

class ToolErrorResult(str):
    pass

def provider_call(function):
    from functools import wraps
    @wraps(function)
    def wrapped(*args, **kwargs):
        try: return function(*args, **kwargs)
        except (ValueError, PermissionError): raise
        except Exception as exc: return ToolErrorResult(safe_error(exc))
    return wrapped

class ToolFailure(Exception):
    pass

def safe_error(exc):
    correlation = uuid.uuid4().hex[:12]
    logging.getLogger('jarvis').warning('provider_failure id=%s type=%s', correlation, type(exc).__name__)
    return f'Error: provider unavailable. Reference {correlation}.'

def validate_bounds(arguments):
    if not isinstance(arguments, dict):
        raise ValueError('Tool arguments must be an object')
    def depth(value, level=0):
        if level > MAX_ARGUMENT_DEPTH:
            raise ValueError('Tool arguments are too deeply nested')
        if isinstance(value, dict):
            for child in value.values(): depth(child, level + 1)
        elif isinstance(value, list):
            for child in value: depth(child, level + 1)
    depth(arguments)
    if len(json.dumps(arguments).encode()) > MAX_ARGUMENT_BYTES:
        raise ValueError('Tool arguments are too large')

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name, description, parameters, func, requires_confirmation=False, required_permissions='', timeout=15, retries=1):
        schema = {**parameters, 'additionalProperties': False}
        for field in ('limit', 'max_results'):
            if field in schema.get('properties', {}):
                schema['properties'][field].update(minimum=1, maximum=50)
        if name == 'list_github_pull_requests':
            schema['properties']['state']['enum'] = ['open', 'closed', 'all']
        self.tools[name] = dict(name=name, description=description, parameters=schema, func=func,
            requires_confirmation=requires_confirmation, required_permissions=required_permissions,
            timeout=timeout, retries=0 if requires_confirmation else retries)

    def get_tool(self, name):
        return self.tools.get(name)

    def validate(self, name, arguments):
        tool = self.get_tool(name)
        if not tool: raise ValueError('Unknown tool')
        validate_bounds(arguments)
        if not Draft202012Validator(tool['parameters']).is_valid(arguments):
            raise ValueError('Invalid tool arguments')
        return tool

    def check_permission(self, tool):
        permission = tool['required_permissions']
        if not permission: return
        provider, _, scope = permission.partition(':')
        token = get_integration_token(provider)
        if not token or not token.get('access_token'):
            raise PermissionError('Integration is disconnected')
        scopes = set((token.get('scopes') or '').replace(',', ' ').split())
        if scope and scope not in scopes:
            # Full calendar scope also grants event read/write access.
            if not (scope.startswith('https://www.googleapis.com/auth/calendar') and
                    'https://www.googleapis.com/auth/calendar' in scopes):
                raise PermissionError('Integration permission is missing')

    def execute(self, name, arguments, approval_id=None, conversation_id=None):
        tool = self.validate(name, arguments)
        self.check_permission(tool)
        if tool['requires_confirmation']:
            if not approval_id: raise PermissionError('Approval required')
            from actions import consume_record
            stored = consume_record(approval_id, 'tool', str(conversation_id))
            if stored != {'tool_name': name, 'arguments': arguments}:
                raise PermissionError('Approval does not match action')
        for attempt in range(tool['retries'] + 1):
            if not slots.acquire(blocking=False):
                raise ToolFailure('Tool capacity exceeded')
            try:
                future = executor.submit(copy_context().run, tool['func'], **arguments)
            except Exception:
                slots.release()
                raise
            future.add_done_callback(lambda _: slots.release())
            try:
                result = future.result(timeout=tool['timeout'])
                if isinstance(result, ToolErrorResult): raise ToolFailure('Provider failed')
                return result
            except FutureTimeout:
                # Python cannot cancel an in-flight HTTP request. Do not overlap retries.
                future.cancel()
                raise ToolFailure('Tool timed out') from None
            except (PermissionError, ValueError):
                raise
            except Exception:
                if attempt == tool['retries']:
                    raise ToolFailure('Provider failed') from None

    def get_all_tools_for_llm(self):
        return [{'type': 'function', 'function': {k: t[k] for k in ('name', 'description', 'parameters')}} for t in self.tools.values()]

registry = ToolRegistry()
