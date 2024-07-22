import asyncio
from aiortc import RTCIceCandidate, RTCIceGatherer, RTCIceServer


async def stun_turn_test(stun_server: str, turn_server: str, username: str, credential: str):
    ice_servers = [
        RTCIceServer(urls=[stun_server]),
        RTCIceServer(urls=[turn_server], username=username, credential=credential)
    ]
    ice_gatherer = RTCIceGatherer(iceServers=ice_servers)

    async def gather_candidates():
        await ice_gatherer.gather()
        return ice_gatherer.getLocalCandidates()

    candidates = await gather_candidates()
    return candidates


if __name__ == "__main__":
    stun_server = "stun:stun.kanonen-studio.de:3478"
    turn_server = "turn:turn.kanonen-studio.de:3478"
    username = "kanoni"
    credential = "test"

    candidates = asyncio.run(stun_turn_test(stun_server, turn_server, username, credential))

    for candidate in candidates:
        print(f"Candidate: {candidate}")
        print(f"  Type: {candidate.type}")
        print(f"  Foundation: {candidate.foundation}")
        print(f"  IP: {candidate.ip}")
        print(f"  Port: {candidate.port}")
        print(f"  Priority: {candidate.priority}")
        print(f"  Protocol: {candidate.protocol}")
        if candidate.relatedAddress:
            print(f"  Related Address: {candidate.relatedAddress}")
        if candidate.relatedPort:
            print(f"  Related Port: {candidate.relatedPort}")
        print("\n")
