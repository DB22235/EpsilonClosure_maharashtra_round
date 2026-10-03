"""SingleIPBurstBot client profile for Fair Drop adversarial simulation."""

import asyncio
from typing import Any, Dict

from .base_profile import BaseProfile

class SingleIPBurstBot(BaseProfile):
    """Sends 500+ requests per minute from a single network_group_id."""
    
    profile_type = "single_ip_burst_bot"
    is_bot = True

    async def execute_registration_flow(self, campaign_id: str, identity: Dict[str, Any]) -> None:
        """Simulates burst traffic from one identity/IP."""
        identity_id = identity.get("participant_id", "burstbot_anon")
        requests_per_minute = identity.get("requests_per_minute", 500)
        network_group_id = identity.get("network_group_id", 1)
        
        headers = {"X-Network-Group-ID": str(network_group_id)}
        
        # Fire a burst of requests
        tasks = []
        for _ in range(min(50, requests_per_minute)):  # cap at 50 per burst to avoid huge overhead in sim
            tasks.append(self._make_request(
                method="POST",
                endpoint=f"/api/campaigns/{campaign_id}/register",
                json_data={"participant_id": identity_id},
                identity_id=identity_id,
                headers=headers,
            ))
            
        await asyncio.gather(*tasks, return_exceptions=True)
