import os
import json
# pyrefly: ignore [missing-import]
from google import genai

class LoLAnalyzer:
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash"):
        """
        Initialize the analyzer with Gemini API key.
        :param api_key: Gemini API Key
        :param model_id: Gemini model ID to use
        """
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def format_data_for_prompt(self, player_data: dict, user_topic: str = "") -> str:
        """
        Formats the raw JSON from Riot API into a clean text prompt for Gemini.
        """
        account = player_data.get('account', {})
        riot_id = f"{account.get('gameName')}#{account.get('tagLine')}"
        
        ranked_info = player_data.get('ranked', [])
        rank_str = "Unranked"
        for entry in ranked_info:
            if entry.get('queueType') == 'RANKED_SOLO_5x5':
                tier = entry.get('tier', 'Unknown')
                rank = entry.get('rank', '')
                lp = entry.get('leaguePoints', 0)
                wins = entry.get('wins', 0)
                losses = entry.get('losses', 0)
                winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                rank_str = f"{tier} {rank} ({lp} LP) - {wins}W {losses}L (Winrate: {winrate:.1f}%)"
                break
        
        matches = player_data.get('recent_matches', [])
        
        prompt = f"以下はLeague of Legendsのプレイヤー「{riot_id}」の直近のデータです。\n"
        prompt += f"レベル: {player_data.get('summonerLevel')}\n"
        prompt += f"ソロキューランク: {rank_str}\n\n"
        prompt += "【直近の試合履歴】\n"
        
        for i, match in enumerate(matches):
            result = "勝利" if match['win'] else "敗北"
            kda = f"{match['kills']}/{match['deaths']}/{match['assists']}"
            duration = match.get('game_duration', 0)
            duration_m = duration // 60
            duration_s = duration % 60
            
            team_kills = match.get('team_kills', 0)
            kp = 0
            if team_kills > 0:
                kp = round((match['kills'] + match['assists']) / team_kills * 100)
            
            prompt += f"\n--- 試合{i+1}: {result} ({duration_m}分{duration_s}秒) ---\n"
            prompt += f"対面相手のランク: {match.get('opponent_rank', 'Unknown')}\n"
            prompt += f"あなた: {match['champion']} ({match['role']}) | KDA: {kda} (KP: {kp}%) | CS: {match.get('totalMinionsKilled', 0)} (10分: {match.get('cs10m', 0)}) | 視界: {match.get('visionScore', 0)} (ピンク: {match.get('wards', 0)}) | ソロキル: {match.get('soloKills', 0)}\n"
            prompt += f"与ダメ: {match.get('damageDealt', 0)} (シェア: {match.get('dmgShare', 0)}%) | 被ダメ: {match.get('damageTaken', 0)} | 獲得G: {match.get('goldEarned', 0)} | 対物ダメ: {match.get('objDmg', 0)}\n"
            
            ally_team = match.get('ally_team', [])
            enemy_team = match.get('enemy_team', [])
            
            if ally_team and enemy_team:
                
                prompt += "[味方チーム]\n"
                for p in ally_team:
                    pkda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
                    prompt += f"  - {p['role']}: {p['champion']} (KDA: {pkda}, 与ダメ: {p.get('damageDealt', 0)} [{p.get('dmgShare', 0)}%], 対物: {p.get('objDmg', 0)}, G: {p.get('goldEarned', 0)}, ソロ: {p.get('soloKills', 0)})\n"
                
                prompt += "[敵チーム]\n"
                for p in enemy_team:
                    pkda = f"{p['kills']}/{p['deaths']}/{p['assists']}"
                    prompt += f"  - {p['role']}: {p['champion']} (KDA: {pkda}, 与ダメ: {p.get('damageDealt', 0)} [{p.get('dmgShare', 0)}%], 対物: {p.get('objDmg', 0)}, G: {p.get('goldEarned', 0)}, ソロ: {p.get('soloKills', 0)})\n"

        prompt += "\nこのデータに基づいて、プレイヤーとしての強み、弱み、傾向、改善点などを、コーチのように詳しく分析してアドバイスを日本語で提供してください。\n"
        prompt += "以下の点に特に注目して深く分析してください：\n"
        prompt += "1. 【マッチアップの相性】: 自身のチャンピオンと対面の敵チャンピオン（同ロール）の有利不利（メタや一般的な相性）をあなたの知識から評価し、その有利不利を前提とした上でパフォーマンスを評価してください（有利な相性で負けていたら厳しく指摘）。\n"
        prompt += "2. 【ゴールド変換効率】: 獲得ゴールドに対して適切にダメージを出せているか（お金だけ持っていて火力を出せていない＝罪が重い）をチェックしてください。\n"
        prompt += "3. 【試合への影響力】: 対面のランク差（格下相手にキャリーできたか/負けていないか）やキル関与率（KP）から、自身の存在感を評価してください。\n"
        prompt += "4. 【敗因の所在】: 味方のスタッツが全体的に悪すぎて「しょうがない試合」だったか、それとも自身の責任（キャリーしきれなかった、対面に負けた等）が大きいかを客観的に判断してください。\n"
        prompt += "OP.GGのような戦績サイトのプロファイリングを意識して、具体的で役立つフィードバックを心がけてください。\n"
        
        if user_topic:
            prompt += f"\n【ユーザーからの特記事項・質問事項】\n「{user_topic}」について重点的に分析・回答してください。\n"
        
        return prompt

    def analyze_player(self, player_data: dict, user_topic: str = "") -> str:
        """
        Sends the formatted data to Gemini API and returns the analysis.
        """
        prompt = self.format_data_for_prompt(player_data, user_topic)
        
        print(f"Sending data to Gemini API for analysis (Model: {self.model_id})...")
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
        )
        return response.text

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("Please set GEMINI_API_KEY in .env file.")
    else:
        analyzer = LoLAnalyzer(api_key)
        # Dummy data test
        dummy_data = {
            "account": {"gameName": "Faker", "tagLine": "T1"},
            "summonerLevel": 300,
            "ranked": [{"queueType": "RANKED_SOLO_5x5", "tier": "CHALLENGER", "rank": "I", "leaguePoints": 1000, "wins": 150, "losses": 100}],
            "recent_matches": [
                {"win": True, "game_mode": "CLASSIC", "role": "MIDDLE", "champion": "Azir", "kills": 10, "deaths": 2, "assists": 8, "totalMinionsKilled": 300, "visionScore": 40}
            ]
        }
        print(analyzer.analyze_player(dummy_data))
