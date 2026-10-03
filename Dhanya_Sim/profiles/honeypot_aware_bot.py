"""HoneypotAwareBot client profile for Fair Drop adversarial simulation."""

from typing import Any, Dict

from .base_profile import BaseProfile

class HoneypotAwareBot(BaseProfile):
    """Sophisticated bot that parses the page DOM and identifies decoy elements."""
    
    profile_type = "honeypot_aware_bot"
    is_bot = True

    async def execute_registration_flow(self, campaign_id: str, identity: Dict[str, Any]) -> None:
        """Simulates smart bot flow, skipping decoy endpoints and hidden fields."""
        identity_id = identity.get("participant_id", "smartbot_anon")
        
        # Smart bot avoids the decoy API endpoint
        
        # Register without the hidden honeypot field
        await self._make_request(
            method="POST",
            endpoint=f"/api/campaigns/{campaign_id}/register",
            json_data={
                "participant_id": identity_id,
            },
            identity_id=identity_id,
        )
