import asyncio
import uuid
import httpx
from a2a.client import A2AClient
from a2a.types import Message, TextPart, MessageSendParams, SendMessageRequest
import json

async def test_agent():
    agent_url = "http://127.0.0.1:8083/api/a2a/kagent/my-k8s-agent/"
    
    a2a_client = A2AClient(
        url=agent_url,
        httpx_client=httpx.AsyncClient(timeout=600.0)
    )

    # Create request
    text_part = TextPart(text="list pods in kagent namespace")
    message = Message(role="user", parts=[text_part], message_id=str(uuid.uuid4()))
    payload = MessageSendParams(message=message, message_id=str(uuid.uuid4()))
    
    print("Sending request...")
    response = await a2a_client.send_message(SendMessageRequest(id=str(uuid.uuid4()), params=payload))
    
    print("\n=== Response Root ===")
    print(f"Type: {type(response.root)}")
    print(f"Has result: {hasattr(response.root, 'result')}")
    
    if response.root and response.root.result:
        task = response.root.result
        print(f"\n=== Task ===")
        print(f"Type: {type(task)}")
        print(f"Has history: {hasattr(task, 'history')}")
        print(f"Has metadata: {hasattr(task, 'metadata')}")
        print(f"Has status: {hasattr(task, 'status')}")
        print(f"Has artifacts: {hasattr(task, 'artifacts')}")
        
        if hasattr(task, 'status') and task.status:
            print(f"\n=== Status ===")
            print(f"Status type: {type(task.status)}")
            if hasattr(task.status, 'state'):
                print(f"State: {task.status.state}")
            if hasattr(task.status, 'message'):
                print(f"Has message: {task.status.message is not None}")
        
        if hasattr(task, 'artifacts') and task.artifacts:
            print(f"\n=== Artifacts ({len(task.artifacts)}) ===")
            for i, artifact in enumerate(task.artifacts):
                print(f"Artifact {i}: {type(artifact)}")
        
        if hasattr(task, 'history') and task.history:
            print(f"\n=== History ({len(task.history)} messages) ===")
            for i, msg in enumerate(task.history):
                print(f"\nMessage {i}:")
                print(f"  Type: {type(msg)}")
                print(f"  Role: {getattr(msg, 'role', 'N/A')}")
                print(f"  Has parts: {hasattr(msg, 'parts')}")
                
                if hasattr(msg, 'parts') and msg.parts:
                    print(f"  Parts count: {len(msg.parts)}")
                    for j, part in enumerate(msg.parts):
                        print(f"\n  Part {j}:")
                        print(f"    Type: {type(part)}")
                        print(f"    Has root: {hasattr(part, 'root')}")
                        
                        if hasattr(part, 'root'):
                            part_root = part.root
                            print(f"    Root type: {type(part_root)}")
                            print(f"    Root has text: {hasattr(part_root, 'text')}")
                            print(f"    Root has data: {hasattr(part_root, 'data')}")
                            print(f"    Root has kind: {hasattr(part_root, 'kind')}")
                            
                            if hasattr(part_root, 'kind'):
                                print(f"    Kind: {part_root.kind}")
                            
                            if hasattr(part_root, 'text'):
                                text = part_root.text
                                print(f"    Text preview: {text[:100] if text else 'None'}...")
                            
                            if hasattr(part_root, 'data'):
                                print(f"    Data type: {type(part_root.data)}")
                                # Try to convert to dict
                                if hasattr(part_root.data, 'model_dump'):
                                    data_dict = part_root.data.model_dump()
                                    print(f"    Data keys: {list(data_dict.keys()) if isinstance(data_dict, dict) else 'N/A'}")
                                else:
                                    print(f"    Data: {part_root.data}")
        
        if hasattr(task, 'metadata'):
            print(f"\n=== Metadata ===")
            print(f"Type: {type(task.metadata)}")
            if task.metadata:
                print(f"Keys: {list(task.metadata.keys()) if isinstance(task.metadata, dict) else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(test_agent())
