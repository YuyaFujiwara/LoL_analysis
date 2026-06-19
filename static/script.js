document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const searchForm = document.getElementById('search-form');
    const riotIdInput = document.getElementById('riot_id');
    const searchBtn = document.getElementById('search-btn');
    const searchLoader = document.getElementById('search-loader');
    
    const dashboardLayout = document.getElementById('dashboard-layout');
    const profileHeader = document.getElementById('profile-header');
    const matchList = document.getElementById('match-list');
    
    const analyzeBtn = document.getElementById('analyze-btn');
    const analyzeLoader = document.getElementById('analyze-loader');
    const copyDataBtn = document.getElementById('copy-data-btn');
    const themeInput = document.getElementById('theme');
    const resultContainer = document.getElementById('result-container');
    const resultContent = document.getElementById('result-content');
    const copyResultBtn = document.getElementById('copy-result-btn');

    const profileSelect = document.getElementById('saved_profiles_select');
    const addBookmarkBtn = document.getElementById('add_bookmark_btn');
    const removeBookmarkBtn = document.getElementById('remove_bookmark_btn');

    let currentRawText = '';
    let currentRiotId = '';

    // Load saved profiles on boot
    async function loadProfiles() {
        try {
            const res = await fetch('/api/profiles');
            const data = await res.json();
            if (data.success) {
                profileSelect.innerHTML = '<option value="">-- お気に入りから選択 --</option>';
                data.profiles.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p;
                    opt.textContent = p;
                    profileSelect.appendChild(opt);
                });
            }
        } catch (e) { console.error(e); }
    }
    loadProfiles();

    // Profile Selection
    profileSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            riotIdInput.value = e.target.value;
        }
    });

    // Add Bookmark
    addBookmarkBtn.addEventListener('click', async () => {
        const id = riotIdInput.value.trim();
        if (!id) return alert('Riot IDを入力してください');
        await fetch('/api/profiles', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({riot_id: id})
        });
        loadProfiles();
    });

    // Remove Bookmark
    removeBookmarkBtn.addEventListener('click', async () => {
        const id = riotIdInput.value.trim();
        if (!id) return;
        await fetch('/api/profiles', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({riot_id: id})
        });
        loadProfiles();
        riotIdInput.value = '';
    });

    // Search (Fetch Matches & Show Dashboard)
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const riot_id = riotIdInput.value;
        const match_count = document.getElementById('match_count').value;
        const start_index = document.getElementById('start_index').value;

        searchBtn.disabled = true;
        searchLoader.classList.remove('hidden');
        dashboardLayout.classList.add('hidden');
        resultContainer.classList.add('hidden');

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ riot_id, match_count, start_index })
            });
            const data = await res.json();

            if (data.success) {
                currentRiotId = riot_id;
                currentRawText = data.raw_data_text;
                renderDashboard(data.player_data, riot_id);
                dashboardLayout.classList.remove('hidden');
            } else {
                alert('エラー: ' + data.error);
            }
        } catch (e) {
            alert('通信エラー');
        } finally {
            searchBtn.disabled = false;
            searchLoader.classList.add('hidden');
        }
    });

    function renderDashboard(playerData, riotId) {
        // Render Profile Header
        const winrate = playerData.ranked && playerData.ranked.length > 0 
            ? `${playerData.ranked[0].tier} ${playerData.ranked[0].rank} (${playerData.ranked[0].leaguePoints} LP)`
            : 'Unranked';

        profileHeader.innerHTML = `
            <div class="profile-icon">👤</div>
            <div class="profile-info">
                <h1>${riotId}</h1>
                <p>Level: ${playerData.summonerLevel} | Rank: <span style="color:var(--accent); font-weight:bold;">${winrate}</span></p>
            </div>
        `;

        // Render Match List
        matchList.innerHTML = '';
        const puuid = playerData.account.puuid;

        playerData.recent_matches.forEach(match => {
            const isWin = match.win;
            const cardClass = isWin ? 'win' : 'loss';
            const resultText = isWin ? 'Victory' : 'Defeat';
            const durationMins = Math.floor(match.game_duration / 60);
            const durationSecs = match.game_duration % 60;
            
            const kda = `${match.kills} / ${match.deaths} / ${match.assists}`;
            const dmgShare = match.dmgShare;
            const cs = match.totalMinionsKilled;
            const kp = match.team_kills > 0 ? Math.round(((match.kills + match.assists) / match.team_kills) * 100) : 0;
            const championName = match.champion;

            const card = document.createElement('div');
            card.className = `match-card ${cardClass}`;
            card.innerHTML = `
                <div class="match-result-col">
                    <div class="${isWin ? 'win-text' : 'loss-text'}">${resultText}</div>
                    <div class="time-text">${durationMins}m ${durationSecs}s</div>
                </div>
                <div class="match-stats-col">
                    <div class="champion-info">
                        <div class="champion-icon">${championName}</div>
                    </div>
                    <div class="kda-info">
                        <div class="kda-text">${kda}</div>
                        <div class="kp-text">KP: ${kp}%</div>
                    </div>
                    <div class="extra-stats">
                        <div>CS <span class="stat-highlight">${cs}</span></div>
                        <div>Dmg <span class="stat-highlight">${dmgShare.toFixed(1)}%</span></div>
                    </div>
                </div>
            `;
            matchList.appendChild(card);
        });
    }

    // AI Coaching
    analyzeBtn.addEventListener('click', async () => {
        analyzeBtn.disabled = true;
        analyzeLoader.classList.remove('hidden');
        resultContainer.classList.add('hidden');

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    riot_id: currentRiotId,
                    match_count: document.getElementById('match_count').value,
                    start_index: document.getElementById('start_index').value,
                    theme: themeInput.value
                })
            });
            const data = await res.json();

            if (data.success) {
                currentRawText = data.raw_data_text;
                const cleanHtml = DOMPurify.sanitize(marked.parse(data.raw_markdown));
                resultContent.innerHTML = cleanHtml;
                resultContainer.classList.remove('hidden');
                resultContainer.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert('AI分析エラー: ' + data.error);
            }
        } catch (e) {
            alert('通信エラー');
        } finally {
            analyzeBtn.disabled = false;
            analyzeLoader.classList.add('hidden');
        }
    });

    // Copy Data
    copyDataBtn.addEventListener('click', async () => {
        if (currentRawText) {
            navigator.clipboard.writeText(currentRawText);
            copyDataBtn.textContent = '✅ コピー完了';
            setTimeout(() => copyDataBtn.innerHTML = '📋 生データをコピー', 2000);
        } else {
             alert("データがまだロードされていません");
        }
    });

    copyResultBtn.addEventListener('click', () => {
        const text = resultContent.innerText;
        navigator.clipboard.writeText(text);
        copyResultBtn.textContent = '✅';
        setTimeout(() => copyResultBtn.textContent = '📋', 2000);
    });
});
