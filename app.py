import os
import json
import traceback
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from riot_api import RiotAPIClient
from analyzer import LoLAnalyzer

# Load environment variables
load_dotenv()
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

app = Flask(__name__)

# Verify API keys on startup
if not RIOT_API_KEY or RIOT_API_KEY == "your_riot_api_key_here":
    print("WARNING: RIOT_API_KEY is not set properly in .env")
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    print("WARNING: GEMINI_API_KEY is not set properly in .env")

import db

@app.route("/")
def index():
    return render_template("index.html")

# --- Profiles API ---
@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    profiles = db.get_saved_profiles()
    return jsonify({"success": True, "profiles": profiles})

@app.route("/api/profiles", methods=["POST"])
def add_profile():
    data = request.json
    riot_id = data.get("riot_id")
    if riot_id and "#" in riot_id:
        db.add_saved_profile(riot_id)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid Riot ID"})

@app.route("/api/profiles", methods=["DELETE"])
def remove_profile():
    data = request.json
    riot_id = data.get("riot_id")
    if riot_id:
        db.remove_saved_profile(riot_id)
        return jsonify({"success": True})
    return jsonify({"success": False})

# --- Dashboard API ---
@app.route("/api/search", methods=["POST"])
def search_player():
    data = request.json
    riot_id = data.get("riot_id", "")
    match_count = int(data.get("match_count", 10))
    start_index = int(data.get("start_index", 0))

    if "#" not in riot_id:
        return jsonify({"success": False, "error": "Riot ID は '名前#タグ' の形式で入力してください。"})

    game_name, tag_line = riot_id.split("#", 1)

    try:
        riot_client = RiotAPIClient(RIOT_API_KEY)
        ai_analyzer = LoLAnalyzer(GEMINI_API_KEY, model_id=GEMINI_MODEL)
        
        # Fetch data (will be cached)
        player_data = riot_client.get_player_full_profile(game_name, tag_line, match_count=match_count, start_index=start_index)
        
        # Save JSON dump as backup
        dump_filename = f"dump_{game_name}.json"
        with open(dump_filename, "w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)

        # Format compact text
        compact_text = ai_analyzer.format_data_for_prompt(player_data)

        return jsonify({
            "success": True, 
            "player_data": player_data,
            "raw_data_text": compact_text
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/analyze", methods=["POST"])
def analyze_player():
    data = request.json
    riot_id = data.get("riot_id", "")
    match_count = int(data.get("match_count", 10))
    start_index = int(data.get("start_index", 0))
    user_topic = data.get("theme", "").strip()

    if "#" not in riot_id:
        return jsonify({"success": False, "error": "Invalid Riot ID"})

    game_name, tag_line = riot_id.split("#", 1)

    try:
        riot_client = RiotAPIClient(RIOT_API_KEY)
        ai_analyzer = LoLAnalyzer(GEMINI_API_KEY, model_id=GEMINI_MODEL)

        # Re-fetch data (mostly hits cache immediately)
        player_data = riot_client.get_player_full_profile(game_name, tag_line, match_count=match_count, start_index=start_index)
        
        # Format text for AI
        compact_text = ai_analyzer.format_data_for_prompt(player_data)
        
        prompt = compact_text
        if user_topic:
            prompt += f"\n\nユーザーからの特別なリクエスト・分析テーマ:\n「{user_topic}」\nこれに重点を置いて回答してください。"
        
        ai_response = ai_analyzer.analyze_data(prompt)
        
        return jsonify({"success": True, "raw_markdown": ai_response, "raw_data_text": compact_text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
