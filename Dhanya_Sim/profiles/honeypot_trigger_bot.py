"""HoneypotTriggerBot client profile for Fair Drop adversarial simulation."""

from typing import Any, Dict

from .base_profile import BaseProfile

class HoneypotTriggerBot(BaseProfile):
    """Naive automation bot that blindly interacts with every element on the page."""
    
    profile_type = "honeypot_trigger_bot"
    is_bot = True

    async def execute_registration_flow(self, campaign_id: str, identity: Dict[str, Any]) -> None:
        """Simulates full bot flow, hitting the decoy endpoint and hidden fields."""
        identity_id = identity.get("participant_id", "bot_anon")
        
        # 1. Trigger the decoy API endpoint
        await self._make_request(
            method="POST",
            endpoint=f"/api/campaigns/{campaign_id}/signals/decoy",
            json_data={"nonce": "decoy_nonce_123"},
            identity_id=identity_id,
        )

        # 2. Register with a hidden honeypot field
        await self._make_request(
            method="POST",
            endpoint=f"/api/campaigns/{campaign_id}/register",
            json_data={
                "participant_id": identity_id,
                "website_url": "http://spam.com",  # Honeypot field
            },
            identity_id=identity_id,
        )
