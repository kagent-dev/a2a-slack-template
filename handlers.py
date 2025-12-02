from slack_bolt.async_app import AsyncApp
from logging import Logger
from slack_sdk import WebClient
from slack_bolt import Say, Ack, BoltContext
import uuid
import httpx
import os
from a2a.client import A2AClient
from a2a.types import Message, TextPart, MessageSendParams, SendMessageRequest

async def invoke_a2a_agent(agent_url: str, input: str, logger: Logger):
    """
    Invokes the A2A agent and returns the response and usage information.
    """
    a2a_client = A2AClient(
        url=agent_url,
        httpx_client=httpx.AsyncClient(timeout=600.0)
    )

    # Create Pydantic models
    text_part = TextPart(text=input)
    message = Message(role="user", parts=[text_part], message_id=str(uuid.uuid4()))

    logger.info(f"Invoking the agent: {agent_url}")
    payload = MessageSendParams(message=message, message_id=str(uuid.uuid4()))
 
    response = await a2a_client.send_message(SendMessageRequest(id=str(uuid.uuid4()), params=payload))
    text = ""
    usage_info = ""

    # The API returns a Task object with history containing the message exchange
    if response.root and response.root.result:
        task = response.root.result
        
        # Parse the history to extract agent responses
        if hasattr(task, 'history') and task.history:
            for msg in task.history:
                # Look for agent messages (skip user messages)
                if hasattr(msg, 'role') and str(msg.role) == 'Role.agent':
                    if hasattr(msg, 'parts') and msg.parts:
                        for part in msg.parts:
                            if hasattr(part, 'root'):
                                part_root = part.root
                                
                                # Check the kind to determine what type of part it is
                                if hasattr(part_root, 'kind'):
                                    kind = part_root.kind
                                    
                                    # Handle text parts - these contain the final agent response
                                    if kind == 'text' and hasattr(part_root, 'text') and part_root.text:
                                        text += part_root.text + "\n"
                                    
                                    # Handle data parts - these contain function calls/responses
                                    # We can optionally parse these too, but the final text response is better
                                    elif kind == 'data' and hasattr(part_root, 'data'):
                                        data = part_root.data
                                        # Only extract text from function responses if no text parts found
                                        if isinstance(data, dict) and 'response' in data:
                                            response_data = data['response']
                                            if isinstance(response_data, dict) and 'result' in response_data:
                                                result = response_data['result']
                                                if isinstance(result, dict) and 'content' in result:
                                                    for content_item in result['content']:
                                                        if isinstance(content_item, dict) and content_item.get('type') == 'text':
                                                            # Only add raw function output if we don't have formatted text
                                                            if not text.strip():
                                                                text += content_item.get('text', '') + "\n"
            
            # Extract usage information from task metadata
            usage_info = extract_usage_info(task)
            
            if not text.strip():
                text = "No response content found"
        else:
            text = "No history found in the response"
    else:
        text = "No response from the agent"
    
    return text.strip(), usage_info

def extract_usage_info(task) -> str:
    """
    Extract usage information from the task metadata.
    """
    try:
        if hasattr(task, 'metadata') and task.metadata:
            metadata = task.metadata
            # Look for kagent_usage_metadata in the metadata
            if 'kagent_usage_metadata' in metadata:
                usage_meta = metadata['kagent_usage_metadata']
                prompt_tokens = usage_meta.get('promptTokenCount', 0)
                candidates_tokens = usage_meta.get('candidatesTokenCount', 0)
                total_tokens = usage_meta.get('totalTokenCount', 0)
                
                return f"💡 *Token Usage:* • Prompt: {prompt_tokens:,} • Response: {candidates_tokens:,} • Total: {total_tokens:,}"
        else:
            return ""
    except Exception:
        return ""

async def mykagent_command(
    client: WebClient, ack: Ack, command, say: Say, logger: Logger, context: BoltContext
):
    await ack()

    user_id = context["user_id"]
    channel_id = context["channel_id"]
    text = command.get("text")

    await client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text="Thinking...",
    )

    # Check if the KAGENT_A2A_URL environment variable is set
    kagent_a2a_url = os.getenv("KAGENT_A2A_URL")
    if not kagent_a2a_url:
        # TODO: Implement the logic for the /mykagent command
        await client.chat_postMessage(
            channel=channel_id,
            user=user_id,
            text="Hello! Once you set the KAGENT_A2A_URL environment variable, you can use the /mykagent command.",
        )
        return

    # Invoke the KAGENT A2A API
    try:
        response, usage_info = await invoke_a2a_agent(kagent_a2a_url, text, logger)
        if response and response.strip():
            # Create a sophisticated AI agent response UI using Block Kit
            response_blocks = [
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "image",
                            "image_url":"https://raw.githubusercontent.com/kagent-dev/main/img/kagent-mark.png",
                            "alt_text": "kagent response"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Query:* {text}"
                        },
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": response
                    }
                },
                {
                    "type": "divider"
                }
            ]
            
            # Only add usage info block if it's not empty
            if usage_info and usage_info.strip():
                response_blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": usage_info
                        }
                    ]
                })
            
            await client.chat_postMessage(
                channel=channel_id,
                blocks=response_blocks,
                text=f"AI Agent Response: {response[:100]}..." if len(response) > 100 else f"AI Agent Response: {response}"
            )
        else:
            await client.chat_postMessage(
                channel=channel_id,
                text="No response received from the agent."
            )
    except Exception as e:
        logger.error(f"Error: {e}")
        error_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "❌ Error",
                    "emoji": True
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Query:* {text}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error Details:*\n```{str(e)}```"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🔄 *Try again* or rephrase your question"
                    }
                ]
            }
        ]
        await client.chat_postMessage(
            channel=channel_id,
            blocks=error_blocks,
            text=f"AI Agent Error: {str(e)}"
        )


def register_handlers(app: AsyncApp):
    """
    Register all handlers for the bot.
    """

    # Commands
    app.command("/mykagent")(mykagent_command)