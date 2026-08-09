import os
import time
import requests
import urllib.parse
from dotenv import load_dotenv
from keep_alive import keep_alive

# Inicia o servidor web interno para o Render
keep_alive()

# Carrega as variáveis de ambiente
load_dotenv()

FOOTBALL_DATA_KEY = os.getenv("API_SPORTS_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Dicionário em memória para evitar alertas duplicados na mesma partida
jogos_notificados = {}

def enviar_mensagem_telegram(mensagem, link_sportingbet=None, link_betfair=None):
    """Envia alerta formatado para o canal ou grupo do Telegram com botões seguros."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }

    if link_sportingbet and link_betfair:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "🎯 Sportingbet", "url": link_sportingbet},
                    {"text": "🔥 Betfair", "url": link_betfair}
                ]
            ]
        }
        
    try:
        r = requests.post(url, json=payload, timeout=10)
        
        # Se falhar com os botões, tenta enviar pelo menos o texto para não perder o sinal
        if r.status_code != 200 and "reply_markup" in payload:
            print(f"⚠️ Alerta: Erro no envio com botões ({r.text}). Enviando sem botões...")
            del payload["reply_markup"]
            r = requests.post(url, json=payload, timeout=10)
            
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem no Telegram: {e}")
        return False

def analisar_jogos_ao_vivo():
    """Busca jogos ao vivo na Football-Data.org e envia sinais."""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code != 200:
            print(f"⚠️ Erro ao consultar API ({res.status_code}): {res.text}")
            return

        data = res.json()
        matches = data.get("matches", [])
        
        if not matches:
            print("ℹ️ Nenhum jogo ao vivo no momento.")
            return

        print(f"🔎 Jogos em andamento encontrados: {len(matches)}")

        for match in matches:
            match_id = match.get("id")
            home_team = match.get("homeTeam", {}).get("name", "Casa")
            away_team = match.get("awayTeam", {}).get("name", "Fora")
            competition = match.get("competition", {}).get("name", "Futebol")
            
            score = match.get("score", {}).get("fullTime", {})
            gols_casa = score.get("home", 0) or 0
            gols_fora = score.get("away", 0) or 0
            
            # Evita disparar sinal repetido para o mesmo jogo
            if match_id in jogos_notificados:
                continue

            # REGRA DE FILTRO: Placar Parelho (diferença de no máximo 1 gol)
            diff = abs(gols_casa - gols_fora)
            if diff <= 1:
                # Formata os nomes para URLs seguras no Telegram
                termo_busca = urllib.parse.quote(f"{home_team} {away_team}")
                link_sb = f"https://sports.sportingbet.br/pt-br/sports/busca?q={termo_busca}"
                link_bf = f"https://www.betfair.com/br/busca?q={termo_busca}"

                msg = (
                    f"🔥 <b>OPORTUNIDADE DE SINAL (24H)</b> 🔥\n\n"
                    f"🏆 <b>Competição:</b> {competition}\n"
                    f"⚽ <b>Confronto:</b> {home_team} {gols_casa} x {gols_fora} {away_team}\n"
                    f"📊 <b>Cenário:</b> Jogo parelho em andamento!\n\n"
                    f"💡 <i>Gols esperados / Pressão no final da partida.</i>"
                )

                if enviar_mensagem_telegram(msg, link_sb, link_bf):
                    print(f"✅ Sinal enviado com sucesso: {home_team} x {away_team}")
                    jogos_notificados[match_id] = True

    except Exception as e:
        print(f"❌ Erro na requisição dos jogos: {e}")

if __name__ == "__main__":
    print("=== BOT DUAL 24H INICIADO (FOOTBALL-DATA.ORG) ===")
    print("[+] Monitorando jogos ao vivo com limite ampliado...")
    
    # Teste de botão seguro ao iniciar
    link_sb_teste = "https://sports.sportingbet.br"
    link_bf_teste = "https://www.betfair.com/br"
    enviar_mensagem_telegram(
        "🧪 <b>TESTE DE BOTOES</b>\n\nVerificando funcionamento dos botões inline abaixo:",
        link_sb_teste,
        link_bf_teste
    )
    
    while True:
        analisar_jogos_ao_vivo()
        time.sleep(60)  # Checa a cada 60 segundos
