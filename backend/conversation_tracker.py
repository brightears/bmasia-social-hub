"""
Track conversations between WhatsApp/LINE and Google Chat
Maintains mapping between customer conversations and Google Chat threads
"""

import json
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ConversationTracker:
    """Track active conversations between messaging platforms and Google Chat"""
    
    def __init__(self):
        # In-memory storage (in production, use Redis or database)
        self.conversations = {}
        # Map thread_key to customer info
        self.thread_mapping = {}
        
    def create_conversation(
        self,
        customer_phone: str,
        customer_name: str,
        venue_name: str,
        platform: str = "WhatsApp",
        thread_key: str = None
    ) -> str:
        """Create a new conversation and return the thread key"""
        
        if not thread_key:
            # Generate thread key: platform_phone_timestamp
            thread_key = f"{platform.lower()}_{customer_phone}_{int(time.time())}"
            
        conversation_id = f"conv_{customer_phone}_{int(time.time())}"
        
        self.conversations[conversation_id] = {
            "conversation_id": conversation_id,
            "thread_key": thread_key,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
            "venue_name": venue_name,
            "platform": platform,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_message": datetime.now().isoformat(),
            "messages": []
        }
        
        # Map thread to conversation for quick lookup
        self.thread_mapping[thread_key] = conversation_id
        
        logger.info(f"Created conversation {conversation_id} with thread {thread_key}")
        return thread_key
        
    def get_conversation_by_thread(self, thread_key: str) -> Optional[Dict]:
        """Get conversation details by Google Chat thread key"""
        
        conversation_id = self.thread_mapping.get(thread_key)
        if conversation_id:
            return self.conversations.get(conversation_id)
        return None
        
    def get_active_conversation(self, customer_phone: str) -> Optional[Dict]:
        """Get the most recent active conversation for a customer"""
        
        # Find conversations for this phone number
        customer_convs = [
            conv for conv in self.conversations.values()
            if conv["customer_phone"] == customer_phone and conv["status"] == "active"
        ]
        
        if not customer_convs:
            return None
            
        # Return the most recent one
        return max(customer_convs, key=lambda x: x["last_message"])
        
    def add_message(
        self,
        thread_key: str,
        message: str,
        sender: str,
        direction: str = "inbound"
    ):
        """Add a message to the conversation history"""
        
        conversation_id = self.thread_mapping.get(thread_key)
        if not conversation_id:
            logger.warning(f"No conversation found for thread {thread_key}")
            return
            
        conversation = self.conversations.get(conversation_id)
        if conversation:
            conversation["messages"].append({
                "timestamp": datetime.now().isoformat(),
                "sender": sender,
                "message": message,
                "direction": direction  # inbound (from customer) or outbound (to customer)
            })
            conversation["last_message"] = message  # Store the actual message text
            conversation["last_message_time"] = datetime.now().isoformat()
            logger.info(f"Added message to conversation {conversation_id}")
            
    def close_conversation(self, thread_key: str):
        """Mark a conversation as closed"""
        
        conversation_id = self.thread_mapping.get(thread_key)
        if conversation_id and conversation_id in self.conversations:
            self.conversations[conversation_id]["status"] = "closed"
            self.conversations[conversation_id]["closed_at"] = datetime.now().isoformat()
            logger.info(f"Closed conversation {conversation_id}")
            
    def cleanup_old_conversations(self, hours: int = 24):
        """Clean up conversations older than specified hours"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for conv_id in list(self.conversations.keys()):
            conv = self.conversations[conv_id]
            last_message_time = datetime.fromisoformat(conv["last_message"])
            
            if last_message_time < cutoff_time and conv["status"] == "active":
                conv["status"] = "expired"
                logger.info(f"Expired conversation {conv_id} due to inactivity")
                
    def get_conversation_summary(self, thread_key: str) -> str:
        """Get a summary of the conversation for display"""
        
        conversation = self.get_conversation_by_thread(thread_key)
        if not conversation:
            return "No conversation history found"
            
        summary = f"Conversation with {conversation['customer_name']} ({conversation['customer_phone']})\n"
        summary += f"Venue: {conversation['venue_name']}\n"
        summary += f"Platform: {conversation['platform']}\n"
        summary += f"Started: {conversation['created_at']}\n\n"
        summary += "Messages:\n"
        
        for msg in conversation["messages"][-10:]:  # Last 10 messages
            direction = "→" if msg["direction"] == "outbound" else "←"
            summary += f"{msg['timestamp'][:19]} {direction} {msg['sender']}: {msg['message']}\n"
            
        return summary

# Global instance
conversation_tracker = ConversationTracker()