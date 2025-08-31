"""
Add a test endpoint to main_simple.py to test the bot
"""

# Add this to main_simple.py after the other endpoints:

@app.post("/api/v1/test-bot")
async def test_bot(message: str = "Hello, I need help with the music system"):
    """Test the bot response capability"""
    try:
        from bot_simple import bot
        response = bot.generate_response(message, "Test User")
        return {
            "status": "success",
            "user_message": message,
            "bot_response": response,
            "ai_enabled": bot.AI_ENABLED if hasattr(bot, 'AI_ENABLED') else False
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }