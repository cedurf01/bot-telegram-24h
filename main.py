import os
import time
import requests
import urllib.parse
from dotenv import load_dotenv
from keep_alive import keep_alive

# Inicia o servidor web interno para manter o robô ativo no Render
keep_alive()

# Carrega as variáveis de ambiente (.env)
load_dotenv()

FOOTBALL_DATA_KEY = os.getenv("API_SPORTS_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Dicionário em memória para evitar alertas duplicados no mesmo jogo
jogos_notificados = {}

def enviar_mensagem_telegram(mensagem, link_sportingbet=None, link_betfair=None):
    """Envia o alerta formatado com botões inline interativos para o Telegram."""
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
        
        # Backup de segurança: se houver falha na estrutura dos botões, envia ao menos o texto
        if r.status_code != 200 and "reply_markup" in payload:
            print(f"⚠️ Aviso: Falha no envio dos botões ({r.text}). Enviando mensagem simples...")
            del payload["reply_markup"]
            r = requests.post(url, json=payload, timeout=10)
            
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Erro na comunicação com a API do Telegram: {e}")
        return False

def analisar_jogos_ao_vivo():
    """Varre as partidas ao vivo via Football-Data.org e aplica o filtro de sinais."""
    url = "https://api.football-data.org/v4/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    params = {"status": "IN_PLAY"}
    
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code != 200:
            print(f"⚠️ Falha na API ({res.status_code}): {res.text}")
            return

        data = res.json()
        matches = data.get("matches", [])
        
        if not matches:
            print("ℹ️ Nenhum jogo ao vivo nas ligas monitoradas no momento.")
            return

        print(f"🔎 Partidas em andamento detectadas: {len(matches)}")

        for match in matches:
            match_id = match.get("id")
            home_team = match.get("homeTeam", {}).get("name", "Casa")
            away_team = match.get("awayTeam", {}).get("name", "Fora")
            competition = match.get("competition", {}).get("name", "Futebol")
            
            score = match.get("score", {}).get("fullTime", {})
            gols_casa = score.get("home", 0) or 0
            gols_fora = score.get("away", 0) or 0
            
            # Não envia mais de uma vez o mesmo jogo
            if match_id in jogos_notificados:
                continue

            # FILTRO: Apenas partidas parelhas (diferença de no máximo 1 gol)
            diff = abs(gols_casa - gols_fora)
            if diff <= 1:
                time_casa_encode = urllib.parse.quote(home_team)
                
                link_sb = f"https://sports.sportingbet.br/pt-br/sports/busca?q={time_casa_encode}"
                link_bf = f"https://www.betfair.com/br/exchange/football"

                msg = (
                    f"🔥 <b>OPORTUNIDADE DE SINAL (24H)</b> 🔥\n\n"
                    f"🏆 <b>Competição:</b> {competition}\n"
                    f"⚽ <b>Confronto:</b> {home_team} {gols_casa} x {gols_fora} {away_team}\n"
                    f"📊 <b>Cenário:</b> Jogo parelho em andamento!\n\n"
                    f"💡 <i>Gols esperados / Pressão na reta final.</i>"
                )

                if enviar_mensagem_telegram(msg, link_sb, link_bf):
                    print(f"✅ Sinal enviado com sucesso: {home_team} x {away_team}")
                    jogos_notificados[match_id] = True

    except Exception as e:
        print(f"❌ Erro ao analisar jogos: {e}")

if __name__ == "__main__":
    print("=== BOT DUAL 24H INICIADO (FOOTBALL-DATA.ORG) ===")
    print("[+] Monitoramento em tempo real ativo...")
    
    # MENSAGEM DE TESTE INICIAL COM OS NOVOS BOTÕES CORRIGIDOS
    link_sb_teste = "https://sports.sportingbet.br"
    link_bf_teste = "https://www.betfair.com/br/exchange/football"
    enviar_mensagem_telegram(
        "🧪 <b>TESTE DOS BOTÕES CORRIGIDOS</b>\n\nClique nos botões abaixo para confirmar que ambos abrem sem erro:",
        link_sb_teste,
        link_bf_teste
    )
    
    while True:
        analisar_jogos_ao_vivo()
        time.sleep(60)  # Varredura automatizada a cada 60 segundos
