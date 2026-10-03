"""DatacenterBot client profile for Fair Drop adversarial simulation."""

from typing import Any, Dict

from .base_profile import BaseProfile

class DatacenterBot(BaseProfile):
    """Tagged with ip_class: 'datacenter' in request metadata."""
    
    profile_type = "datacenter_bot"
    is_bot = True

    async def execute_registration_flow(self, campaign_id: str, identity: Dict[str, Any]) -> None:
        """Simulates moderate requests from a datacenter IP class."""
        identity_id = identity.get("participant_id", "dcbot_anon")
        
        headers = {"X-IP-Class": "datacenter"}
        
        await self._make_request(
            method="POST",
            endpoint=f"/api/campaigns/{campaign_id}/register",
            json_data={"participant_id": identity_id, "ip_class": "datacenter"},
            identity_id=identity_id,
            headers=headers,
        )
