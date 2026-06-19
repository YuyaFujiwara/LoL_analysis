import os
import requests
import db
from urllib.parse import quote

class RiotAPIClient:
    def __init__(self, api_key: str, region: str = "jp1", routing_region: str = "asia"):
        """
        :param api_key: Riot API Key
        :param region: e.g., 'jp1', 'kr', 'na1'
        :param routing_region: e.g., 'asia', 'americas', 'europe'
        """
        self.api_key = api_key
        self.region = region
        self.routing_region = routing_region
        self.headers = {
            "X-Riot-Token": self.api_key
        }

    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict:
        """Get account info (PUUID) by Riot ID."""
        url = f"https://{self.routing_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{quote(game_name)}/{quote(tag_line)}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_summoner_by_puuid(self, puuid: str) -> dict:
        """Get summoner info by PUUID."""
        url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_league_entries_by_puuid(self, puuid: str) -> list:
        """Get ranked stats by PUUID."""
        url = f"https://{self.region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_match_ids_by_puuid(self, puuid: str, start: int = 0, count: int = 10) -> list:
        """Get recent match IDs (Ranked matches only), handles count > 100 by paginating."""
        all_match_ids = []
        remaining = count
        current_start = start
        
        while remaining > 0:
            fetch_count = min(remaining, 100)
            url = f"https://{self.routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start={current_start}&count={fetch_count}&type=ranked"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            ids = response.json()
            if not ids:
                break
                
            all_match_ids.extend(ids)
            current_start += fetch_count
            remaining -= fetch_count
            
        return all_match_ids

    def get_match_by_id(self, match_id: str) -> dict:
        """Get detailed match info."""
        cached_match = db.get_match_from_db(match_id)
        if cached_match:
            print(f"      [DB Cache Hit] {match_id}")
            return cached_match

        url = f"https://{self.routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        match_data = response.json()
        
        # Save to DB
        game_creation = match_data.get('info', {}).get('gameCreation', 0)
        db.save_match_to_db(match_id, game_creation, match_data)
        
        return match_data

    def get_player_full_profile(self, game_name: str, tag_line: str, match_count: int = 5, start_index: int = 0) -> dict:
        """Aggregates all relevant data for a player to simulate OP.GG."""
        print(f"Fetching account info for {game_name}#{tag_line}...")
        account = self.get_account_by_riot_id(game_name, tag_line)
        puuid = account['puuid']

        print("Fetching summoner profile...")
        summoner = self.get_summoner_by_puuid(puuid)
        
        print("Fetching ranked entries...")
        ranked_entries = self.get_league_entries_by_puuid(puuid)

        print(f"Fetching {match_count} matches (starting from offset {start_index})...")
        match_ids = self.get_match_ids_by_puuid(puuid, start=start_index, count=match_count)
        
        matches_data = []
        for i, m_id in enumerate(match_ids):
            print(f"Fetching details for match {m_id} ({i+1}/{match_count})...")
            match_data = self.get_match_by_id(m_id)
            
            # Find the participant data for our player
            player_match_stats = None
            for participant in match_data['info']['participants']:
                if participant['puuid'] == puuid:
                    player_match_stats = participant
                    break
            
            if player_match_stats:
                ally_team = []
                enemy_team = []
                player_won = player_match_stats.get('win', False)
                for p in match_data['info']['participants']:
                    p_info = {
                        "puuid": p.get('puuid'),
                        "champion": p.get('championName'),
                        "role": p.get('teamPosition', 'UNKNOWN'),
                        "kills": p.get('kills', 0),
                        "deaths": p.get('deaths', 0),
                        "assists": p.get('assists', 0),
                        "damageDealt": p.get('totalDamageDealtToChampions', 0),
                        "goldEarned": p.get('goldEarned', 0),
                        "soloKills": p.get('challenges', {}).get('soloKills', 0),
                        "dmgShare": round(p.get('challenges', {}).get('teamDamagePercentage', 0) * 100, 1),
                        "cs": p.get('totalMinionsKilled', 0) + p.get('neutralMinionsKilled', 0),
                        "cs10m": p.get('challenges', {}).get('laneMinionsFirst10Minutes', 0),
                        "objDmg": p.get('damageDealtToObjectives', 0),
                        "wards": p.get('visionWardsBoughtInGame', 0)
                    }
                    if p.get('win', False) == player_won:
                        ally_team.append(p_info)
                    else:
                        enemy_team.append(p_info)
                        
                team_kills = sum(p['kills'] for p in ally_team)
                
                # Find opponent rank
                opponent_rank_str = "Unknown"
                player_role = player_match_stats.get('teamPosition', 'UNKNOWN')
                if player_role != 'UNKNOWN':
                    for ep in enemy_team:
                        if ep['role'] == player_role:
                            try:
                                opp_ranked = self.get_league_entries_by_puuid(ep['puuid'])
                                for entry in opp_ranked:
                                    if entry.get('queueType') == 'RANKED_SOLO_5x5':
                                        opponent_rank_str = f"{entry.get('tier')} {entry.get('rank')}"
                                        break
                            except Exception:
                                pass
                            break
                # Extract only relevant details to save token context
                matches_data.append({
                    "match_id": m_id,
                    "game_mode": match_data['info'].get('gameMode', 'UNKNOWN'),
                    "game_duration": match_data['info'].get('gameDuration', 0),
                    "champion": player_match_stats.get('championName'),
                    "kills": player_match_stats.get('kills', 0),
                    "deaths": player_match_stats.get('deaths', 0),
                    "assists": player_match_stats.get('assists', 0),
                    "win": player_match_stats.get('win', False),
                    "totalMinionsKilled": player_match_stats.get('totalMinionsKilled', 0) + player_match_stats.get('neutralMinionsKilled', 0),
                    "goldEarned": player_match_stats.get('goldEarned', 0),
                    "visionScore": player_match_stats.get('visionScore', 0),
                    "damageDealt": player_match_stats.get('totalDamageDealtToChampions', 0),
                    "damageTaken": player_match_stats.get('totalDamageTaken', 0),
                    "soloKills": player_match_stats.get('challenges', {}).get('soloKills', 0),
                    "dmgShare": round(player_match_stats.get('challenges', {}).get('teamDamagePercentage', 0) * 100, 1),
                    "cs10m": player_match_stats.get('challenges', {}).get('laneMinionsFirst10Minutes', 0),
                    "objDmg": player_match_stats.get('damageDealtToObjectives', 0),
                    "wards": player_match_stats.get('visionWardsBoughtInGame', 0),
                    "role": player_role,
                    "team_kills": team_kills,
                    "opponent_rank": opponent_rank_str,
                    "ally_team": ally_team,
                    "enemy_team": enemy_team
                })

        return {
            "account": account,
            "summonerLevel": summoner['summonerLevel'],
            "ranked": ranked_entries,
            "recent_matches": matches_data
        }

if __name__ == "__main__":
    # Test script if executed directly
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key or api_key == "your_riot_api_key_here":
        print("Please set RIOT_API_KEY in .env file.")
    else:
        client = RiotAPIClient(api_key)
        # Uncomment and put your name to test
        # print(client.get_player_full_profile("YourName", "TAG", match_count=2))
