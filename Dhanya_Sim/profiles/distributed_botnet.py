"""DistributedBotnet client profile for Fair Drop adversarial simulation."""

import uuid
from typing import Any, Dict

from .base_profile import BaseProfile

class DistributedBotnet(BaseProfile):
    """Each bot instance gets a UNIQUE network_group_id."""
    
    profile_type = "distributed_botnet"
    is_bot = True

    async def execute_registration_flow(self, campaign_id: str, identity: Dict[str, Any]) -> None:
        """Simulates IP rotation."""
        identity_id = identity.get("participant_id", "distbot_anon")
        
        # Each request uses a unique network group ID to simulate IP rotation
        network_group_id = hash(uuid.uuid4())
        
        headers = {"X-Network-Group-ID": str(network_group_id)}
        
        await self._make_request(
            method="POST",
            endpoint=f"/api/campaigns/{campaign_id}/register",
            json_data={"participant_id": identity_id},
            identity_id=identity_id,
            headers=headers,
        )
