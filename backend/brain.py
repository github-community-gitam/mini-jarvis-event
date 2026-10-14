import json
import os
from datetime import datetime, timezone
from groq import Groq
from config import GROQ_API_KEY, JARVIS_SYSTEM_PROMPT
import memory
from tool_registry import registry, safe_error
from actions import issue_record, consume_record
import tools_calendar
import tools_github
import tools_gmail
import tools_drive

HISTORY_CHAR_BUDGET = int(os.getenv('HISTORY_CHAR_BUDGET', '12000'))

def bounded_history(history, budget=HISTORY_CHAR_BUDGET):
    selected = []
    for msg in reversed(history):
        if budget <= 0: break
        text = str(msg['content'])[-budget:]
        if text:
            selected.append({'role': msg['role'], 'content': text})
            budget -= len(text)
    return list(reversed(selected))

def generate_response(user_text, conversation_id=None, tool_execution=None, message_saved=False):
    if not GROQ_API_KEY:
        return 'The language service is not configured. Please try again after setup.', None
    client = Groq(api_key=GROQ_API_KEY, timeout=20, max_retries=0)
    model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    messages = [{'role': 'system', 'content': JARVIS_SYSTEM_PROMPT + '\nCURRENT TIME: ' + datetime.now(timezone.utc).isoformat()}]
    # No shared process-global chat history: every history lookup is owner scoped.
    history = memory.get_recent_messages(conversation_id, limit=10) if conversation_id else []
    if user_text and not message_saved and conversation_id:
        memory.add_message(conversation_id, 'user', user_text)
    if user_text:
        older = memory.search_previous_conversations(user_text, conversation_id, 3) if conversation_id else []
        history = older + history
        # Current input is added separately and never truncated by history budget.
        if message_saved and history and history[-1]['role'] == 'user' and history[-1]['content'] == user_text:
            history = history[:-1]
    messages.extend(bounded_history(history))
    if user_text: messages.append({'role': 'user', 'content': user_text})
    if tool_execution:
        name, args = tool_execution['tool_name'], tool_execution['arguments']
        if tool_execution['approved']:
            try:
                result = registry.execute(name, args, tool_execution['action_id'], conversation_id)
            except (PermissionError, ValueError):
                raise
            except Exception as exc:
                # HTTP 409 must reach the client on replay.
                from fastapi import HTTPException
                if isinstance(exc, HTTPException): raise
                result = safe_error(exc)
        else:
            consume_record(tool_execution['action_id'], 'tool', str(conversation_id))
            result = 'User canceled the action.'
        messages.append({'role': 'user', 'content': f'Tool result: {str(result)[:20000]}. Summarize concisely.'})
    try:
        response = client.chat.completions.create(model=model, messages=messages,
            tools=registry.get_all_tools_for_llm() if not tool_execution else None,
            max_tokens=300, temperature=0.4)
        msg = response.choices[0].message
        if msg.tool_calls and not tool_execution:
            call = msg.tool_calls[0]
            try:
                if len(call.function.arguments.encode()) > 16384: raise ValueError('Too large')
                args = json.loads(call.function.arguments)
                tool = registry.validate(call.function.name, args)
                registry.check_permission(tool)
            except (ValueError, TypeError, RecursionError, PermissionError):
                return 'The requested tool or its arguments are invalid, or the integration needs reconnecting.', None
            if tool['requires_confirmation']:
                payload = {'tool_name': call.function.name, 'arguments': args}
                action = issue_record('tool', payload, str(conversation_id))
                text = 'I need your confirmation to proceed with this action.'
                if conversation_id: memory.add_message(conversation_id, 'assistant', text)
                return text, {**payload, 'action_id': action, 'message': tool['description']}
            try:
                result = registry.execute(call.function.name, args)
            except Exception as exc:
                result = safe_error(exc)
            messages.extend([{'role': 'assistant', 'content': None, 'tool_calls': [call.model_dump()]},
                {'role': 'tool', 'tool_call_id': call.id, 'name': call.function.name, 'content': str(result)[:20000]}])
            msg = client.chat.completions.create(model=model, messages=messages, max_tokens=300, temperature=0.4).choices[0].message
        text = (msg.content or '').strip() or 'No response was returned. Please try again.'
    except Exception as exc:
        safe_error(exc)
        return 'The language service is temporarily unavailable. Please try again.', None
    if conversation_id: memory.add_message(conversation_id, 'assistant', text)
    return text, None
