"""
Message Processing Worker for BMA Social Platform

This module is the core engine processing WhatsApp/Line messages at scale.
Architecture designed for 10,000+ venues with sub-minute response times.

Key Features:
- Redis queue consumption with automatic retry and DLQ
- Conversation state management with distributed session handling
- SLA tracking with real-time breach detection
- Intelligent error handling with circuit breakers
- Response routing to multiple messaging channels
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import traceback

from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.workers.celery_app import celery_app
from app.core.database import db_manager
from app.core.redis import redis_manager, CacheKeyBuilder
from app.models.conversation import (
    Conversation, Message, ConversationStatus, 
    MessageSenderType, ConversationPriority
)
from app.models.satisfaction import SatisfactionScore, SatisfactionStatus
from app.models.venue import Venue
from app.models.zone import Zone
from app.services.bot.intent_classifier import IntentClassifier, Intent, Sentiment
from app.services.bot.gemini_client import gemini_client
from app.services.soundtrack.client import soundtrack_client
from app.services.messaging.whatsapp import WhatsAppClient
from app.services.messaging.line import LineClient

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    DLQ = "dlq"  # Dead Letter Queue


class ActionType(Enum):
    """Soundtrack API action types"""
    VOLUME_CHANGE = "volume_change"
    PLAYLIST_CHANGE = "playlist_change"
    PLAY = "play"
    PAUSE = "pause"
    SKIP = "skip"
    STATUS_CHECK = "status_check"
    SCHEDULE = "schedule"


@dataclass
class MessageContext:
    """Context for message processing"""
    conversation_id: str
    venue_id: str
    zone_ids: List[str]
    channel: str
    customer_id: str
    customer_name: Optional[str]
    language: str
    session_data: Dict[str, Any]
    previous_messages: List[Dict[str, Any]]
    sla_deadline: datetime
    priority: ConversationPriority
    is_vip: bool
    metadata: Dict[str, Any]


@dataclass
class ProcessingResult:
    """Result of message processing"""
    status: ProcessingStatus
    response_text: str
    actions_taken: List[Dict[str, Any]]
    intent: Optional[Intent]
    sentiment: Optional[Sentiment]
    confidence: float
    sla_breach: bool
    escalation_required: bool
    satisfaction_triggered: bool
    error: Optional[str]
    processing_time_ms: int


class MessageProcessor(Task):
    """
    Core message processing task with production-grade features.
    Handles the entire lifecycle of a customer message.
    """
    
    name = "app.workers.tasks.message_processor.process_message"
    max_retries = 3
    default_retry_delay = 5  # seconds
    
    def __init__(self):
        super().__init__()
        self.intent_classifier = IntentClassifier()
        self.whatsapp_client = WhatsAppClient()
        self.line_client = LineClient()
        
        # Circuit breaker for external services
        self.circuit_breakers = {
            "soundtrack": {"failures": 0, "last_failure": None, "threshold": 5},
            "gemini": {"failures": 0, "last_failure": None, "threshold": 3},
        }
        
        # Performance metrics
        self.metrics = {
            "messages_processed": 0,
            "average_processing_time": 0,
            "sla_breaches": 0,
            "escalations": 0,
            "errors": 0,
        }
    
    def run(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing pipeline for incoming messages.
        
        Args:
            message_data: Message payload from queue
            
        Returns:
            Processing result dictionary
        """
        start_time = time.time()
        
        try:
            # 1. Load context and validate
            context = self._load_context(message_data)
            
            # 2. Check SLA status immediately
            if self._check_sla_breach(context):
                self._handle_sla_breach(context)
            
            # 3. Classify intent and extract entities
            classification = self.intent_classifier.classify(
                message_data["content"],
                context.session_data
            )
            
            # 4. Check if escalation is needed
            if classification.escalation_recommended or context.is_vip:
                return self._escalate_to_human(context, classification)
            
            # 5. Process based on intent
            action_results = self._execute_actions(context, classification)
            
            # 6. Generate response
            response = self._generate_response(
                context, classification, action_results
            )
            
            # 7. Send response to customer
            self._send_response(context, response)
            
            # 8. Update conversation state
            self._update_conversation_state(
                context, classification, action_results, response
            )
            
            # 9. Check if satisfaction survey should be triggered
            if self._should_trigger_satisfaction(context, classification):
                self._trigger_satisfaction_survey(context)
            
            # 10. Log metrics
            processing_time = int((time.time() - start_time) * 1000)
            self._log_metrics(context, classification, processing_time)
            
            return {
                "status": "completed",
                "conversation_id": context.conversation_id,
                "intent": classification.intent.value,
                "confidence": classification.confidence,
                "processing_time_ms": processing_time,
                "actions": action_results,
            }
            
        except Exception as e:
            logger.error(f"Message processing failed: {e}\n{traceback.format_exc()}")
            
            # Handle failure with retry logic
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))
            else:
                # Move to DLQ after max retries
                self._move_to_dlq(message_data, str(e))
                return {
                    "status": "failed",
                    "error": str(e),
                    "moved_to_dlq": True,
                }
    
    def _load_context(self, message_data: Dict[str, Any]) -> MessageContext:
        """
        Load complete context for message processing.
        Includes conversation history, venue info, and session data.
        """
        with db_manager.get_session() as session:
            # Load conversation
            from sqlalchemy.orm import selectinload
            conversation = session.execute(
                select(Conversation)
                .options(selectinload(Conversation.venue))
                .where(Conversation.id == message_data["conversation_id"])
            )
            conversation = conversation.scalar_one()
            
            # Load recent messages for context
            recent_messages = session.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(10)
            )
            recent_messages = recent_messages.scalars().all()
            
            # Load venue zones
            zones = session.execute(
                select(Zone)
                .where(Zone.venue_id == conversation.venue_id)
                .where(Zone.is_active == True)
            )
            zones = zones.scalars().all()
            
            # Get session from Redis
            session_key = CacheKeyBuilder.conversation_session(str(conversation.id))
            session_data = await redis_manager.get(session_key)
            session_data = json.loads(session_data) if session_data else {}
            
            # Build context
            return MessageContext(
                conversation_id=str(conversation.id),
                venue_id=str(conversation.venue_id),
                zone_ids=[str(z.id) for z in zones],
                channel=conversation.channel.value,
                customer_id=conversation.customer_id,
                customer_name=conversation.customer_name,
                language=conversation.language,
                session_data=session_data,
                previous_messages=[
                    {
                        "content": m.content,
                        "sender": m.sender_type.value,
                        "intent": m.intent,
                        "timestamp": m.created_at.isoformat(),
                    }
                    for m in recent_messages
                ],
                sla_deadline=conversation.sla_deadline,
                priority=conversation.priority,
                is_vip="vip" in (conversation.tags or []),
                metadata=conversation.metadata or {},
            )
    
    async def _check_sla_breach(self, context: MessageContext) -> bool:
        """Check if SLA has been breached"""
        if not context.sla_deadline:
            return False
        
        return datetime.utcnow() > context.sla_deadline
    
    async def _handle_sla_breach(self, context: MessageContext):
        """Handle SLA breach with immediate escalation"""
        logger.warning(f"SLA breach for conversation {context.conversation_id}")
        
        # Update metrics
        self.metrics["sla_breaches"] += 1
        
        # Send alert to management
        await redis_manager.publish(
            "alerts:sla_breach",
            {
                "conversation_id": context.conversation_id,
                "venue_id": context.venue_id,
                "priority": context.priority.value,
                "breach_time": datetime.utcnow().isoformat(),
            }
        )
        
        # Escalate to human immediately
        await self._escalate_to_human(context, None)
    
    async def _execute_actions(
        self, 
        context: MessageContext, 
        classification
    ) -> List[Dict[str, Any]]:
        """
        Execute actions based on intent classification.
        Handles Soundtrack API calls with circuit breaker.
        """
        actions = []
        
        # Check circuit breaker
        if self._is_circuit_open("soundtrack"):
            logger.warning("Soundtrack circuit breaker is open")
            return [{
                "type": "error",
                "message": "Music system temporarily unavailable",
            }]
        
        try:
            # Map intent to actions
            if classification.intent == Intent.VOLUME_ADJUST:
                # Extract volume parameters
                volume_entity = next(
                    (e for e in classification.entities if e.type == "volume_level"),
                    None
                )
                direction = next(
                    (e for e in classification.entities if e.type == "volume_direction"),
                    None
                )
                
                for zone_id in context.zone_ids[:5]:  # Limit to 5 zones per request
                    result = await self._adjust_volume(zone_id, volume_entity, direction)
                    actions.append(result)
            
            elif classification.intent == Intent.PLAYLIST_CHANGE:
                genre = next(
                    (e for e in classification.entities if e.type == "genre"),
                    None
                )
                
                if genre:
                    for zone_id in context.zone_ids[:5]:
                        result = await self._change_playlist(zone_id, genre.value)
                        actions.append(result)
            
            elif classification.intent == Intent.MUSIC_STOP:
                for zone_id in context.zone_ids[:5]:
                    result = await soundtrack_client.pause(zone_id)
                    actions.append({
                        "type": ActionType.PAUSE.value,
                        "zone_id": zone_id,
                        "success": True,
                        "result": result,
                    })
            
            elif classification.intent == Intent.MUSIC_START:
                for zone_id in context.zone_ids[:5]:
                    result = await soundtrack_client.play(zone_id)
                    actions.append({
                        "type": ActionType.PLAY.value,
                        "zone_id": zone_id,
                        "success": True,
                        "result": result,
                    })
            
            elif classification.intent == Intent.MUSIC_NOT_PLAYING:
                # Check status and attempt to restart
                for zone_id in context.zone_ids:
                    status = await soundtrack_client.get_device_status(zone_id)
                    
                    if not status.get("is_playing"):
                        result = await soundtrack_client.play(zone_id)
                        actions.append({
                            "type": ActionType.PLAY.value,
                            "zone_id": zone_id,
                            "success": True,
                            "result": result,
                            "diagnostic": "Music was stopped, now restarted",
                        })
                    else:
                        actions.append({
                            "type": ActionType.STATUS_CHECK.value,
                            "zone_id": zone_id,
                            "success": True,
                            "diagnostic": "Music is playing normally",
                        })
            
            # Reset circuit breaker on success
            self._reset_circuit("soundtrack")
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            self._record_circuit_failure("soundtrack")
            actions.append({
                "type": "error",
                "message": str(e),
                "success": False,
            })
        
        return actions
    
    async def _adjust_volume(
        self, 
        zone_id: str, 
        volume_entity, 
        direction_entity
    ) -> Dict[str, Any]:
        """Adjust volume for a specific zone"""
        try:
            # Get current status
            status = await soundtrack_client.get_device_status(zone_id)
            current_volume = status.get("volume", 50)
            
            # Calculate new volume
            if volume_entity and volume_entity.value.isdigit():
                new_volume = int(volume_entity.value)
            elif direction_entity:
                if direction_entity.value in ["up", "increase", "higher", "louder"]:
                    new_volume = min(100, current_volume + 10)
                else:
                    new_volume = max(0, current_volume - 10)
            else:
                new_volume = current_volume
            
            # Apply volume change
            result = await soundtrack_client.set_volume(zone_id, new_volume)
            
            return {
                "type": ActionType.VOLUME_CHANGE.value,
                "zone_id": zone_id,
                "previous_volume": current_volume,
                "new_volume": new_volume,
                "success": True,
                "result": result,
            }
            
        except Exception as e:
            logger.error(f"Volume adjustment failed for zone {zone_id}: {e}")
            return {
                "type": ActionType.VOLUME_CHANGE.value,
                "zone_id": zone_id,
                "success": False,
                "error": str(e),
            }
    
    async def _change_playlist(self, zone_id: str, genre: str) -> Dict[str, Any]:
        """Change playlist for a zone"""
        try:
            # Get available playlists
            playlists = await soundtrack_client.get_playlists()
            
            # Find matching playlist
            matching = [
                p for p in playlists 
                if genre.lower() in p.get("name", "").lower()
            ]
            
            if not matching:
                return {
                    "type": ActionType.PLAYLIST_CHANGE.value,
                    "zone_id": zone_id,
                    "success": False,
                    "error": f"No playlist found for genre: {genre}",
                }
            
            # Apply playlist
            result = await soundtrack_client.set_playlist(
                zone_id, 
                matching[0]["id"]
            )
            
            return {
                "type": ActionType.PLAYLIST_CHANGE.value,
                "zone_id": zone_id,
                "playlist": matching[0]["name"],
                "success": True,
                "result": result,
            }
            
        except Exception as e:
            logger.error(f"Playlist change failed for zone {zone_id}: {e}")
            return {
                "type": ActionType.PLAYLIST_CHANGE.value,
                "zone_id": zone_id,
                "success": False,
                "error": str(e),
            }
    
    async def _generate_response(
        self,
        context: MessageContext,
        classification,
        action_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate natural language response using Gemini.
        Falls back to templates if Gemini is unavailable.
        """
        # Check circuit breaker for Gemini
        if self._is_circuit_open("gemini"):
            return self._generate_template_response(
                classification.intent,
                action_results
            )
        
        try:
            # Prepare context for Gemini
            success_count = sum(1 for a in action_results if a.get("success"))
            failure_count = len(action_results) - success_count
            
            # Determine tone based on sentiment and results
            if classification.sentiment == Sentiment.URGENT:
                tone = "urgent_helpful"
            elif classification.sentiment == Sentiment.NEGATIVE:
                tone = "empathetic"
            elif failure_count > 0:
                tone = "apologetic"
            else:
                tone = "friendly"
            
            # Generate response
            response = await gemini_client.generate_response(
                intent=classification.intent.value,
                entities={e.type: e.value for e in classification.entities},
                action_result={
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "actions": action_results[:3],  # Limit details
                },
                tone=tone
            )
            
            # Reset circuit breaker on success
            self._reset_circuit("gemini")
            
            return response
            
        except Exception as e:
            logger.error(f"Gemini response generation failed: {e}")
            self._record_circuit_failure("gemini")
            
            # Fall back to template
            return self._generate_template_response(
                classification.intent,
                action_results
            )
    
    def _generate_template_response(
        self,
        intent: Intent,
        action_results: List[Dict[str, Any]]
    ) -> str:
        """Generate template-based response as fallback"""
        success_count = sum(1 for a in action_results if a.get("success"))
        failure_count = len(action_results) - success_count
        
        templates = {
            Intent.VOLUME_ADJUST: {
                "success": "Volume has been adjusted successfully.",
                "partial": f"Volume adjusted for {success_count} zones. {failure_count} zones had issues.",
                "failure": "Unable to adjust volume at this time. Please try again.",
            },
            Intent.PLAYLIST_CHANGE: {
                "success": "Playlist has been changed as requested.",
                "partial": f"Playlist changed for {success_count} zones. {failure_count} zones had issues.",
                "failure": "Unable to change playlist. Please check the genre name.",
            },
            Intent.MUSIC_STOP: {
                "success": "Music has been paused.",
                "failure": "Unable to pause music. Please try again.",
            },
            Intent.MUSIC_START: {
                "success": "Music is now playing.",
                "failure": "Unable to start music. Please check the system.",
            },
            Intent.MUSIC_NOT_PLAYING: {
                "success": "I've checked and restarted the music system.",
                "failure": "There seems to be an issue with the music system. Our team has been notified.",
            },
        }
        
        template_set = templates.get(intent, {
            "success": "Your request has been processed.",
            "failure": "Unable to process your request. Please try again.",
        })
        
        if failure_count == 0 and success_count > 0:
            return template_set.get("success", "Request completed.")
        elif failure_count > 0 and success_count > 0:
            return template_set.get("partial", template_set.get("success"))
        else:
            return template_set.get("failure", "Request failed. Our team will assist you.")
    
    async def _send_response(self, context: MessageContext, response: str):
        """Send response back to customer via appropriate channel"""
        try:
            if context.channel == "whatsapp":
                await self.whatsapp_client.send_message(
                    to=context.customer_id,
                    message=response,
                    conversation_id=context.conversation_id
                )
            elif context.channel == "line":
                await self.line_client.send_message(
                    to=context.customer_id,
                    message=response,
                    conversation_id=context.conversation_id
                )
            else:
                logger.warning(f"Unknown channel: {context.channel}")
                
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
            # Queue for retry
            await redis_manager.publish(
                "messages:send_retry",
                {
                    "conversation_id": context.conversation_id,
                    "channel": context.channel,
                    "customer_id": context.customer_id,
                    "message": response,
                    "retry_count": 0,
                }
            )
    
    async def _update_conversation_state(
        self,
        context: MessageContext,
        classification,
        action_results: List[Dict[str, Any]],
        response: str
    ):
        """Update conversation and session state"""
        async with get_async_session() as session:
            # Update conversation
            await session.execute(
                update(Conversation)
                .where(Conversation.id == context.conversation_id)
                .values(
                    last_activity_at=datetime.utcnow(),
                    bot_confidence_score=classification.confidence,
                    bot_handled=True,
                    message_count=Conversation.message_count + 1,
                    bot_message_count=Conversation.bot_message_count + 1,
                )
            )
            
            # Store bot response as message
            bot_message = Message(
                conversation_id=context.conversation_id,
                sender_type=MessageSenderType.BOT,
                sender_id="bot",
                sender_name="BMA Assistant",
                content=response,
                intent=classification.intent.value,
                entities={e.type: e.value for e in classification.entities},
                sentiment=classification.sentiment.value,
                confidence_score=classification.confidence,
                actions=action_results,
                action_results=action_results,
            )
            session.add(bot_message)
            
            await session.commit()
        
        # Update Redis session
        session_key = CacheKeyBuilder.conversation_session(context.conversation_id)
        session_data = context.session_data
        session_data.update({
            "last_intent": classification.intent.value,
            "last_confidence": classification.confidence,
            "last_action_count": len(action_results),
            "last_update": datetime.utcnow().isoformat(),
        })
        
        await redis_manager.setex(
            session_key,
            1800,  # 30 minutes TTL
            json.dumps(session_data)
        )
    
    async def _should_trigger_satisfaction(
        self,
        context: MessageContext,
        classification
    ) -> bool:
        """Determine if satisfaction survey should be triggered"""
        # Trigger on resolution intents
        resolution_intents = [
            Intent.THANKS,
            Intent.COMPLIMENT,
        ]
        
        if classification.intent in resolution_intents:
            return True
        
        # Check if conversation seems resolved
        if "fixed" in classification.entities or "solved" in classification.entities:
            return True
        
        # Check message count threshold
        if context.session_data.get("message_count", 0) > 10:
            return True
        
        return False
    
    async def _trigger_satisfaction_survey(self, context: MessageContext):
        """Trigger satisfaction survey for the conversation"""
        async with get_async_session() as session:
            # Check if survey already exists
            existing = await session.execute(
                select(SatisfactionScore)
                .where(SatisfactionScore.conversation_id == context.conversation_id)
            )
            
            if not existing.scalar():
                # Create satisfaction request
                satisfaction = SatisfactionScore(
                    conversation_id=context.conversation_id,
                    venue_id=context.venue_id,
                    channel=context.channel,
                    status=SatisfactionStatus.REQUESTED,
                    requested_at=datetime.utcnow(),
                )
                session.add(satisfaction)
                
                # Update conversation
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == context.conversation_id)
                    .values(
                        satisfaction_requested=True,
                        satisfaction_requested_at=datetime.utcnow(),
                    )
                )
                
                await session.commit()
                
                # Send survey message
                survey_message = (
                    "Thank you for using BMA Support! "
                    "How would you rate your experience today? (1-5 stars)"
                )
                
                await self._send_response(context, survey_message)
    
    async def _escalate_to_human(
        self,
        context: MessageContext,
        classification
    ):
        """Escalate conversation to human agent"""
        logger.info(f"Escalating conversation {context.conversation_id} to human")
        
        async with get_async_session() as session:
            # Update conversation status
            await session.execute(
                update(Conversation)
                .where(Conversation.id == context.conversation_id)
                .values(
                    status=ConversationStatus.WAITING_TEAM,
                    bot_escalated=True,
                    bot_escalation_reason=(
                        f"Low confidence: {classification.confidence}" 
                        if classification 
                        else "SLA breach"
                    ),
                )
            )
            await session.commit()
        
        # Notify team
        await redis_manager.publish(
            "escalations:new",
            {
                "conversation_id": context.conversation_id,
                "venue_id": context.venue_id,
                "priority": context.priority.value,
                "reason": "bot_escalation",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        # Send message to customer
        escalation_message = (
            "I'm connecting you with our support team who can better assist you. "
            "Someone will be with you shortly."
        )
        await self._send_response(context, escalation_message)
        
        self.metrics["escalations"] += 1
        
        return {
            "status": "escalated",
            "conversation_id": context.conversation_id,
            "reason": "bot_escalation",
        }
    
    async def _move_to_dlq(self, message_data: Dict[str, Any], error: str):
        """Move failed message to Dead Letter Queue"""
        dlq_item = {
            "original_message": message_data,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
            "retries": self.request.retries,
        }
        
        # Store in DLQ (Redis list)
        await redis_manager.redis.lpush(
            "messages:dlq",
            json.dumps(dlq_item)
        )
        
        # Alert ops team
        await redis_manager.publish(
            "alerts:dlq",
            {
                "conversation_id": message_data.get("conversation_id"),
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    async def _log_metrics(
        self,
        context: MessageContext,
        classification,
        processing_time: int
    ):
        """Log processing metrics for monitoring"""
        # Update local metrics
        self.metrics["messages_processed"] += 1
        
        # Calculate running average
        current_avg = self.metrics["average_processing_time"]
        count = self.metrics["messages_processed"]
        self.metrics["average_processing_time"] = (
            (current_avg * (count - 1) + processing_time) / count
        )
        
        # Log to monitoring system
        metric_data = {
            "conversation_id": context.conversation_id,
            "venue_id": context.venue_id,
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "processing_time_ms": processing_time,
            "priority": context.priority.value,
            "channel": context.channel,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await redis_manager.publish("metrics:message_processing", metric_data)
        
        # Store in time-series for analytics
        metric_key = f"metrics:processing:{datetime.utcnow().strftime('%Y%m%d:%H')}"
        await redis_manager.redis.zadd(
            metric_key,
            {json.dumps(metric_data): time.time()}
        )
        await redis_manager.redis.expire(metric_key, 86400 * 7)  # 7 days retention
    
    # Circuit Breaker Methods
    
    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for a service"""
        breaker = self.circuit_breakers.get(service)
        if not breaker:
            return False
        
        # Check if we should reset
        if breaker["last_failure"]:
            time_since_failure = time.time() - breaker["last_failure"]
            if time_since_failure > 60:  # 1 minute cooldown
                breaker["failures"] = 0
                breaker["last_failure"] = None
                return False
        
        return breaker["failures"] >= breaker["threshold"]
    
    def _record_circuit_failure(self, service: str):
        """Record a failure for circuit breaker"""
        breaker = self.circuit_breakers.get(service)
        if breaker:
            breaker["failures"] += 1
            breaker["last_failure"] = time.time()
            
            if breaker["failures"] == breaker["threshold"]:
                logger.warning(f"Circuit breaker opened for {service}")
    
    def _reset_circuit(self, service: str):
        """Reset circuit breaker for a service"""
        breaker = self.circuit_breakers.get(service)
        if breaker:
            breaker["failures"] = 0
            breaker["last_failure"] = None


# Register the task
message_processor = MessageProcessor()
celery_app.register_task(message_processor)


@celery_app.task(name="app.workers.tasks.message_processor.consume_queue")
def consume_message_queue():
    """
    Background task to consume messages from Redis queue.
    Runs continuously and dispatches to processor.
    """
    asyncio.run(_consume_queue())


async def _consume_queue():
    """Async queue consumer"""
    logger.info("Starting message queue consumer")
    
    while True:
        try:
            # Pop message from queue (blocking with timeout)
            message = await redis_manager.redis.brpop(
                "messages:incoming",
                timeout=5
            )
            
            if message:
                # Parse message
                _, data = message
                message_data = json.loads(data)
                
                # Dispatch to processor
                message_processor.delay(message_data)
                
                logger.debug(f"Dispatched message from conversation {message_data.get('conversation_id')}")
            
        except Exception as e:
            logger.error(f"Queue consumer error: {e}")
            await asyncio.sleep(1)


@celery_app.task(name="app.workers.tasks.message_processor.process_dlq")
def process_dead_letter_queue():
    """
    Process messages in Dead Letter Queue.
    Runs periodically to retry or escalate failed messages.
    """
    asyncio.run(_process_dlq())


async def _process_dlq():
    """Process DLQ items"""
    logger.info("Processing Dead Letter Queue")
    
    # Get items from DLQ
    items = await redis_manager.redis.lrange("messages:dlq", 0, 100)
    
    for item in items:
        try:
            dlq_data = json.loads(item)
            original_message = dlq_data["original_message"]
            
            # Check if we should retry
            failed_time = datetime.fromisoformat(dlq_data["failed_at"])
            time_since_failure = datetime.utcnow() - failed_time
            
            if time_since_failure < timedelta(hours=1):
                # Recent failure - escalate to human
                await redis_manager.publish(
                    "escalations:dlq",
                    {
                        "conversation_id": original_message.get("conversation_id"),
                        "error": dlq_data["error"],
                        "requires_manual_intervention": True,
                    }
                )
            else:
                # Old failure - archive
                await redis_manager.redis.lpush(
                    "messages:dlq:archive",
                    item
                )
            
            # Remove from DLQ
            await redis_manager.redis.lrem("messages:dlq", 1, item)
            
        except Exception as e:
            logger.error(f"DLQ processing error: {e}")


# Health check task
@celery_app.task(name="app.workers.tasks.message_processor.health_check")
def health_check():
    """Health check for message processor"""
    return {
        "status": "healthy",
        "metrics": message_processor.metrics,
        "circuit_breakers": message_processor.circuit_breakers,
        "timestamp": datetime.utcnow().isoformat(),
    }