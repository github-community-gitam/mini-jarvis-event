import json
from groq import Groq
from config import GROQ_API_KEY, JARVIS_SYSTEM_PROMPT
import memory
from tool_registry import registry
import tools_calendar # Ensure calendar tools are registered
import tools_github # Ensure github tools are registered
import tools_gmail # Ensure gmail tools are registered
import tools_drive # Ensure drive tools are registered


# Fallback memory if DB is unavailable
fallback_messages = [
    {"role": "system", "content": JARVIS_SYSTEM_PROMPT}
]

def generate_response(user_text, conversation_id=None, tool_execution=None):
    """
    Sends the user's text to the Groq LLM and retrieves JARVIS's response.
    Returns (response_text, tool_call_dict_or_none)
    """
    if not GROQ_API_KEY:
        return "Sir, my systems are currently offline. The Groq API key is missing.", None
        
    client = Groq(api_key=GROQ_API_KEY)
    
    print("\r[THINKING]                ", end="")
    
    import datetime
    current_time = datetime.datetime.now().astimezone().isoformat()
    # Construct context
    messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT + f"\nCURRENT DATE AND TIME: {current_time}"}]
    
    # Check if this is a response to a tool execution confirmation
    if tool_execution:
        # Load history
        if conversation_id:
            recent = memory.get_recent_messages(conversation_id, limit=10)
            for msg in recent:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        tool_name = tool_execution["tool_name"]
        arguments = tool_execution["arguments"]
        approved = tool_execution["approved"]
        
        if approved:
            # Execute the tool
            tool = registry.get_tool(tool_name)
            if tool:
                try:
                    result = tool["func"](**arguments)
                    tool_result_str = str(result)
                except Exception as e:
                    tool_result_str = f"Error executing tool: {e}"
            else:
                tool_result_str = f"Tool {tool_name} not found."
        else:
            tool_result_str = "User canceled the action."
            
        # Add the tool result to messages to let LLM generate final response
        messages.append({
            "role": "user",
            "content": f"Tool '{tool_name}' execution result: {tool_result_str}. Please summarize this for the user concisely."
        })
        
    else:
        # Standard flow
        if conversation_id:
            memory.add_message(conversation_id, "user", user_text)
            
            # Retrieve older relevant context across all conversations
            older_context = memory.search_previous_conversations(user_text, current_conversation_id=conversation_id, limit=3)
            if older_context:
                context_str = "Recall from previous conversations:\n"
                for msg in older_context:
                    context_str += f"- {msg.get('role')}: {msg.get('content')}\n"
                messages.append({"role": "system", "content": context_str})
            
            # Retrieve recent conversation context
            recent = memory.get_recent_messages(conversation_id, limit=10)
            for msg in recent:
                # Need to be careful with tool messages if we store them, but currently we just store text.
                # Actually, our memory system stores text, so it's fine.
                messages.append({"role": msg["role"], "content": msg["content"]})
        else:
            # Fallback in-memory context
            fallback_messages.append({"role": "user", "content": user_text})
            messages = list(fallback_messages)
            
    # LLM Call
    try:
        tools = registry.get_all_tools_for_llm()
        
        response = client.chat.completions.create(
            model="llama3-70b-8192", # Replaced gpt-oss-20b with Groq standard model
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else "none",
            max_tokens=300,
            temperature=0.4
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            # LLM wants to call a tool
            tool_call = response_message.tool_calls[0]
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            tool = registry.get_tool(tool_name)
            if tool and tool["requires_confirmation"]:
                # Pause and ask for confirmation
                confirmation_req = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "message": f"I am about to {tool['description']}. Shall I proceed?"
                }
                return "I need your confirmation to proceed with this action.", confirmation_req
            elif tool:
                # Execute immediately if read-only
                try:
                    result = tool["func"](**arguments)
                    tool_result_str = str(result)
                except Exception as e:
                    tool_result_str = f"Error: {e}"
                    
                # Call LLM again with result
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call.model_dump()]
                })
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": tool_result_str,
                })
                
                final_response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.4
                )
                jarvis_text = final_response.choices[0].message.content.strip()
                if conversation_id:
                    memory.add_message(conversation_id, "assistant", jarvis_text)
                return jarvis_text, None
            else:
                jarvis_text = f"I tried to use a tool called {tool_name} but it was not found."
                if conversation_id:
                    memory.add_message(conversation_id, "assistant", jarvis_text)
                return jarvis_text, None
        else:
            # Normal response
            jarvis_text = response_message.content.strip()
            
            if conversation_id:
                memory.add_message(conversation_id, "assistant", jarvis_text)
            else:
                fallback_messages.append({"role": "assistant", "content": jarvis_text})
                if len(fallback_messages) > 11:
                    fallback_messages.pop(1)
                    fallback_messages.pop(1)
                
            return jarvis_text, None
            
    except Exception as e:
        print(f"\n[Brain Error: {e}]")
        return "I apologize sir, but I am experiencing cognitive difficulties at the moment.", None
