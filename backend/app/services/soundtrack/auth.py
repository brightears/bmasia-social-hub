"""OAuth 2.0 Authentication Manager for Soundtrack Your Brand API"""

import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import jwt
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class OAuth2Manager:
    """
    Manages OAuth 2.0 authentication for Soundtrack Your Brand API.
    Handles token refresh, caching, and validation automatically.
    """
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        base_url: str = None,
        token_endpoint: str = "/oauth/token",
        scope: str = "zones.read zones.write playlists.read volume.write"
    ):
        self.client_id = client_id or settings.soundtrack_client_id
        self.client_secret = client_secret or settings.soundtrack_client_secret
        self.base_url = base_url or settings.soundtrack_base_url
        self.token_endpoint = token_endpoint
        self.scope = scope
        
        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_type: str = "Bearer"
        
        # Lock for thread-safe token refresh
        self._refresh_lock = asyncio.Lock()
        
        # Performance tracking
        self._last_refresh_time: Optional[datetime] = None
        self._refresh_count: int = 0
        self._failed_refresh_count: int = 0
        
    @property
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired"""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Add 60-second buffer before expiration
        buffer = timedelta(seconds=60)
        return datetime.utcnow() < (self._token_expires_at - buffer)
    
    @property
    def token_remaining_seconds(self) -> int:
        """Get remaining seconds until token expiration"""
        if not self._token_expires_at:
            return 0
        
        remaining = self._token_expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds()))
    
    async def get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.
        Thread-safe with automatic retry logic.
        """
        # Fast path: token is valid
        if self.is_token_valid:
            return self._access_token
        
        # Acquire lock for token refresh
        async with self._refresh_lock:
            # Double-check after acquiring lock
            if self.is_token_valid:
                return self._access_token
            
            # Refresh token
            await self._refresh_access_token()
            return self._access_token
    
    async def _refresh_access_token(self) -> None:
        """
        Refresh access token using client credentials or refresh token.
        Implements exponential backoff for retries.
        """
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                if self._refresh_token:
                    # Use refresh token if available
                    token_data = await self._refresh_with_refresh_token()
                else:
                    # Use client credentials flow
                    token_data = await self._refresh_with_client_credentials()
                
                # Update token data
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token", self._refresh_token)
                
                # Calculate expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                self._token_type = token_data.get("token_type", "Bearer")
                
                # Update metrics
                self._last_refresh_time = datetime.utcnow()
                self._refresh_count += 1
                
                logger.info(
                    f"Token refreshed successfully. Expires in {expires_in} seconds. "
                    f"Total refreshes: {self._refresh_count}"
                )
                return
                
            except Exception as e:
                self._failed_refresh_count += 1
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                
                logger.error(
                    f"Token refresh attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay} seconds..."
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                else:
                    raise Exception(f"Failed to refresh token after {max_retries} attempts: {e}")
    
    async def _refresh_with_client_credentials(self) -> Dict[str, Any]:
        """Refresh token using client credentials flow"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{self.token_endpoint}",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise Exception(
                    f"Token refresh failed with status {response.status_code}: "
                    f"{error_data.get('error_description', 'Unknown error')}"
                )
            
            return response.json()
    
    async def _refresh_with_refresh_token(self) -> Dict[str, Any]:
        """Refresh token using refresh token flow"""
        if not self._refresh_token:
            # Fall back to client credentials
            return await self._refresh_with_client_credentials()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{self.token_endpoint}",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            
            if response.status_code != 200:
                # If refresh token is invalid, try client credentials
                logger.warning("Refresh token invalid, falling back to client credentials")
                self._refresh_token = None
                return await self._refresh_with_client_credentials()
            
            return response.json()
    
    def get_authorization_header(self) -> Dict[str, str]:
        """Get authorization header for API requests"""
        if not self._access_token:
            raise ValueError("No access token available. Call get_access_token() first.")
        
        return {"Authorization": f"{self._token_type} {self._access_token}"}
    
    async def revoke_token(self) -> bool:
        """
        Revoke current access token.
        Returns True if successful, False otherwise.
        """
        if not self._access_token:
            return True
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/oauth/revoke",
                    data={
                        "token": self._access_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    self._access_token = None
                    self._refresh_token = None
                    self._token_expires_at = None
                    logger.info("Token revoked successfully")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def decode_token(self) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token to inspect claims (if token is JWT).
        Returns None if token is not JWT or cannot be decoded.
        """
        if not self._access_token:
            return None
        
        try:
            # Try to decode without verification (for inspection only)
            return jwt.decode(
                self._access_token,
                options={"verify_signature": False}
            )
        except Exception:
            # Token is not JWT or cannot be decoded
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authentication metrics"""
        return {
            "is_authenticated": self.is_token_valid,
            "token_remaining_seconds": self.token_remaining_seconds,
            "refresh_count": self._refresh_count,
            "failed_refresh_count": self._failed_refresh_count,
            "last_refresh_time": self._last_refresh_time.isoformat() if self._last_refresh_time else None,
            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None
        }