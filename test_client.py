# test_client.py
from app.llm_client import client, MODEL

print(f"Provider : {__import__('os').getenv('LLM_PROVIDER')}")
print(f"Model    : {MODEL}")

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "You are a code reviewer."},
        {"role": "user",   "content": "What is a null pointer dereference in one sentence?"},
    ],
    max_tokens=60,
)

print(f"Response : {response.choices[0].message.content}")
print(f"Tokens   : {response.usage.total_tokens}")

tools = [
    {
        "type": "function",
        "function": {
            "name": "flag_issue",
            "description": "Flag a code issue found in a PR diff",
            "parameters": {
                "type": "object",
                "properties": {
                    "line":       {"type": "integer", "description": "Line number"},
                    "severity":   {"type": "string",  "enum": ["low", "medium", "high"]},
                    "reason":     {"type": "string",  "description": "Why it's an issue"},
                    "suggestion": {"type": "string",  "description": "How to fix it"},
                },
                "required": ["line", "severity", "reason", "suggestion"],
            },
        },
    }
]

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "You are a code reviewer. Use the flag_issue tool."},
        {"role": "user",   "content": "Review this: `x = None; print(x.name)` at line 5."},
    ],
    tools=tools,
    tool_choice="auto",
    max_tokens=200,
)

msg = response.choices[0].message
if msg.tool_calls:
    print("Function calling works!")
    print("Tool called:", msg.tool_calls[0].function.name)
    print("Arguments :", msg.tool_calls[0].function.arguments)
else:
    print("No tool call — check model supports function calling")