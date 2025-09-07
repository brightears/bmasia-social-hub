"""
Simple web interface for customer support replies
Allows team to reply to WhatsApp messages from a web form
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# HTML template for the reply form (embedded for simplicity)
REPLY_FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BMA Support Reply</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .info {
            background: #f0f7ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
        }
        .info p {
            margin: 5px 0;
        }
        .customer-message {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }
        textarea {
            width: 100%;
            min-height: 150px;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            resize: vertical;
        }
        button {
            background: #2196F3;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background: #1976D2;
        }
        .success {
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 20px 0;
            display: none;
        }
        .error {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin: 20px 0;
            display: none;
        }
        .label {
            font-weight: 600;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 Reply to Customer</h1>
        
        <div class="info">
            <p><span class="label">Venue:</span> {{ venue_name }}</p>
            <p><span class="label">Customer:</span> {{ customer_name }}</p>
            <p><span class="label">Phone:</span> {{ phone }}</p>
            <p><span class="label">Platform:</span> {{ platform }}</p>
        </div>
        
        {% if message %}
        <div class="customer-message">
            <p><span class="label">Customer Message:</span></p>
            <p>{{ message }}</p>
        </div>
        {% endif %}
        
        <form id="replyForm" method="post">
            <textarea name="reply" placeholder="Type your reply here..." required></textarea>
            <input type="hidden" name="phone" value="{{ phone }}">
            <input type="hidden" name="platform" value="{{ platform }}">
            <button type="submit">Send Reply</button>
        </form>
        
        <div id="success" class="success">
            ✅ Reply sent successfully!
        </div>
        
        <div id="error" class="error">
            ❌ Failed to send reply. Please try again.
        </div>
    </div>
    
    <script>
        document.getElementById('replyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const response = await fetch(window.location.pathname, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                document.getElementById('success').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                e.target.reset();
                setTimeout(() => {
                    document.getElementById('success').style.display = 'none';
                }, 3000);
            } else {
                document.getElementById('error').style.display = 'block';
                document.getElementById('success').style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

def create_reply_endpoint(app: FastAPI):
    """Add reply endpoint to existing FastAPI app"""
    
    @app.get("/reply/{thread_key}", response_class=HTMLResponse)
    async def show_reply_form(thread_key: str):
        """Show reply form for a specific conversation"""
        
        # Import here to avoid circular dependency
        from conversation_tracker import conversation_tracker
        
        # Get conversation details
        conversation = conversation_tracker.get_conversation_by_thread(thread_key)
        
        if not conversation:
            return HTMLResponse(
                content="<h1>Conversation not found</h1>",
                status_code=404
            )
        
        # Get recent messages for context
        messages = conversation_tracker.get_conversation_history(thread_key, limit=5)
        latest_message = messages[0] if messages else None
        
        # Render the form with conversation details
        html_content = REPLY_FORM_HTML.replace("{{ venue_name }}", conversation.get("venue_name", "Unknown"))
        html_content = html_content.replace("{{ customer_name }}", conversation.get("customer_name", "Customer"))
        html_content = html_content.replace("{{ phone }}", conversation.get("customer_phone", ""))
        html_content = html_content.replace("{{ platform }}", conversation.get("platform", "WhatsApp"))
        
        if latest_message:
            html_content = html_content.replace("{{ message }}", latest_message.get("message", ""))
        else:
            html_content = html_content.replace("{% if message %}", "{% if False %}")
        
        return HTMLResponse(content=html_content)
    
    @app.post("/reply/{thread_key}")
    async def send_reply(
        thread_key: str,
        reply: str = Form(...),
        phone: str = Form(...),
        platform: str = Form(...)
    ):
        """Send reply to customer via WhatsApp/LINE"""
        
        # Import here to avoid circular dependency
        from conversation_tracker import conversation_tracker
        
        try:
            # Log the reply
            conversation_tracker.add_message(
                thread_key=thread_key,
                message=reply,
                sender="Support Team",
                direction="outbound"
            )
            
            # Send via appropriate platform
            if platform.lower() == "whatsapp":
                from whatsapp_sender import send_whatsapp_message
                success = await send_whatsapp_message(phone, reply)
            else:
                # LINE implementation would go here
                logger.warning(f"LINE replies not yet implemented for {phone}")
                success = False
            
            if success:
                logger.info(f"Reply sent to {phone}: {reply[:50]}...")
                return {"status": "success"}
            else:
                raise HTTPException(status_code=500, detail="Failed to send message")
                
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    logger.info("Reply interface endpoints added to app")