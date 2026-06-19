import os
import sys
import json
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from riot_api import RiotAPIClient
from analyzer import LoLAnalyzer

def main():
    # Load environment variables
    load_dotenv(override=True)
    riot_api_key = os.getenv("RIOT_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not riot_api_key or riot_api_key == "your_riot_api_key_here":
        print("エラー: .env ファイルに RIOT_API_KEY が設定されていません。")
        sys.exit(1)
        
    if not gemini_api_key or gemini_api_key == "your_gemini_api_key_here":
        print("エラー: .env ファイルに GEMINI_API_KEY が設定されていません。")
        sys.exit(1)

    print("=== League of Legends AI Analyst ===")
    riot_id_input = input("分析したいプレイヤーのRiot IDを入力してください (例: PlayerName#TAG): ").strip()
    
    if "#" not in riot_id_input:
        print("エラー: Riot IDは '名前#タグ' の形式で入力してください。")
        sys.exit(1)
        
    mode_input = input("実行モードを選んでください (1: AI分析, 2: JSONダンプ, 3: 過去データの一括テキスト化) [1]: ").strip()
    
    default_count = 100 if mode_input == "3" else 10
    match_count_input = input(f"取得する試合数を入力してください (デフォルト: {default_count}): ").strip()
    match_count = int(match_count_input) if match_count_input.isdigit() else default_count
    
    start_index_input = input("何試合前から取得しますか？ (直近からなら0、10試合前からなら10) [0]: ").strip()
    start_index = int(start_index_input) if start_index_input.isdigit() else 0
    
    user_topic = ""
    if mode_input == "1" or mode_input == "":
        user_topic = input("分析のテーマや特に聞きたいことはありますか？ (空欄でEnterを押すと全体的な分析をします): ").strip()
        
    game_name, tag_line = riot_id_input.split("#", 1)
    
    try:
        # Initialize clients
        model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        riot_client = RiotAPIClient(riot_api_key)
        ai_analyzer = LoLAnalyzer(gemini_api_key, model_id=model_id)
        
        # 1. Fetch data from Riot API
        print(f"\n[{game_name}#{tag_line}] のデータをRiot APIから取得しています...")
        player_data = riot_client.get_player_full_profile(game_name, tag_line, match_count=match_count, start_index=start_index)
        
        # Always dump data
        dump_filename = f"dump_{game_name}.json"
        with open(dump_filename, "w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
            
        text_dump_filename = f"dump_{game_name}.txt"
        if mode_input == "3":
            text_dump_filename = f"history_{game_name}_{match_count}matches.txt"
            
        with open(text_dump_filename, "w", encoding="utf-8") as f:
            compact_text = ai_analyzer.format_data_for_prompt(player_data)
            f.write(compact_text)
            
        if mode_input in ["2", "3"]:
            print(f"\n✅ データを保存しました！")
            if mode_input == "2":
                print(f"  - {dump_filename} (生の全データ)")
            print(f"  - {text_dump_filename} (AI送信用に極限までコンパクトに整形したテキスト)")
        else:
            # 2. Analyze data with Gemini API
            print("\nGemini APIでデータを分析しています...")
            analysis_result = ai_analyzer.analyze_player(player_data, user_topic=user_topic)
            
            # 3. Output results
            print("\n================ 分析結果 ================\n")
            print(analysis_result)
            print("\n=========================================\n")
        
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        print("APIキーが間違っているか、存在しないRiot IDの可能性があります。")

if __name__ == "__main__":
    main()
