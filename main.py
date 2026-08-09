import os
import time
import requests
import urllib.parse
from dotenv import load_dotenv
from keep_alive import keep_alive

# Inicia o mini servidor web para manter 24h online
keep_alive()

load_dotenv()

API_KEY = os.getenv("API_SPORTS_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8603856699:AAEObp_Uxzu3-nV4qiUq4MB3GukUPakGeMM")
CHAT_ID = os.getenv("CHAT_ID", "-1003991961267")

URL_LIVE = "https://v3.football.api-sports.io/fixtures?live=all"
headers = {"x-apisports-key": API_KEY}

sinais_gols_enviados = set()
sinais_cantos_enviados = set()

def enviar_telegram(mensagem, casa="", fora=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    time_busca = urllib.parse.quote(casa) if casa else ""
    link_sportingbet = f"https://www.sportingbet.bet.br/pt-br/sports/pesquisa?query={time_busca}" if time_busca else "https://www.sportingbet.bet.br/pt-br/sports"
    link_betfair = f"https://www.betfair.bet.br/apostas/pesquisa?query={time_busca}" if time_busca else "https://www.betfair.bet.br/apostas/"

    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": f"🎲 Buscar {casa} (Sportingbet)", "url": link_sportingbet},
                    {"text": f"📈 Buscar {casa} (Betfair)", "url": link_betfair}
                ]
            ]
        }
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem no Telegram: {e}")

def obter_estatisticas(fixture_id):
    url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        stats_list = res.get("response", [])
        
        if not stats_list or len(stats_list) < 2:
            return None

        stats_dict = {
            "shots_total": [0, 0],
            "shots_on_goal": [0, 0],
            "shots_off_goal": [0, 0],
            "blocked_shots": [0, 0],
            "dangerous_attacks": [0, 0],
            "corners": [0, 0],
            "yellow_cards": [0, 0]
        }
        
        for idx, team_stats in enumerate(stats_list):
            for stat in team_stats.get("statistics", []):
                tipo = stat.get("type")
                val = stat.get("value") or 0
                
                if tipo == "Total Shots":
                    stats_dict["shots_total"][idx] = val
                elif tipo == "Shots on Goal":
                    stats_dict["shots_on_goal"][idx] = val
                elif tipo == "Shots off Goal":
                    stats_dict["shots_off_goal"][idx] = val
                elif tipo == "Blocked Shots":
                    stats_dict["blocked_shots"][idx] = val
                elif tipo == "Dangerous Attacks":
                    stats_dict["dangerous_attacks"][idx] = val
                elif tipo == "Corner Kicks":
                    stats_dict["corners"][idx] = val
                elif tipo == "Yellow Cards":
                    stats_dict["yellow_cards"][idx] = val
                    
        return stats_dict
    except Exception as e:
        print(f"⚠️ Erro nas stats do jogo {fixture_id}: {e}")
        return None

def analisar_jogos():
    print("\n==================================================")
    print("[+] Monitorando jogos ao vivo (SPORTINGBET + BETFAIR)...")
    try:
        response = requests.get(URL_LIVE, headers=headers, timeout=20)
        dados_api = response.json()
        jogos = dados_api.get("response", [])
        
        total_jogos_ao_vivo = len(jogos)

        if total_jogos_ao_vivo == 0:
            print("⚠️ Nenhum jogo ao vivo retornado pela API no momento.")
            return

        jogos_na_janela_tempo = 0
        jogos_placar_parelho = 0
        stats_analisadas = 0
        sinais_gols = 0
        sinais_cantos = 0

        for jogo in jogos:
            fixture_id = jogo["fixture"]["id"]
            tempo = jogo["fixture"]["status"]["elapsed"]
            
            if not tempo or tempo < 20 or tempo > 88:
                continue
            jogos_na_janela_tempo += 1

            gols_casa = jogo["goals"]["home"] or 0
            gols_fora = jogo["goals"]["away"] or 0
            diff = abs(gols_casa - gols_fora)

            if diff > 1:
                continue
            jogos_placar_parelho += 1

            precisa_gols = (20 <= tempo <= 80) and (fixture_id not in sinais_gols_enviados)
            precisa_cantos = (75 <= tempo <= 87) and (fixture_id not in sinais_cantos_enviados)

            if not (precisa_gols or precisa_cantos):
                continue

            stats = obter_estatisticas(fixture_id)
            if not stats:
                continue
            stats_analisadas += 1

            pais = jogo["league"]["country"].upper()
            casa = jogo["teams"]["home"]["name"]
            fora = jogo["teams"]["away"]["name"]

            att_casa, att_fora = stats["dangerous_attacks"][0], stats["dangerous_attacks"][1]
            
            att_time_pressionado = 0
            if gols_casa <= gols_fora:
                att_time_pressionado += att_casa
            if gols_fora <= gols_casa:
                att_time_pressionado += att_fora

            appm_pressionado = att_time_pressionado / tempo if tempo > 0 else 0

            chutes_gol_casa, chutes_gol_fora = stats["shots_on_goal"][0], stats["shots_on_goal"][1]
            total_chutes_gol = chutes_gol_casa + chutes_gol_fora
            c_casa, c_fora = stats["corners"][0], stats["corners"][1]
            total_cantos = c_casa + c_fora
            chutes_bloqueados = stats["blocked_shots"][0] + stats["blocked_shots"][1]
            finalizacoes = stats["shots_total"][0] + stats["shots_total"][1]
            total_amarelos = stats["yellow_cards"][0] + stats["yellow_cards"][1]

            # ⚽ ALERTA DE GOLS
            if precisa_gols:
                if (appm_pressionado >= 0.70 and 
                    finalizacoes >= 6 and 
                    total_chutes_gol >= 2 and 
                    total_amarelos <= 4):

                    line_gol = gols_casa + gols_fora + 0.5
                    msg_gol = (
                        f"🚨 ALERTA DE GOL - PRESSÃO ALTA ⚽\n\n"
                        f"🏴 {pais}\n"
                        f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                        f"⏱️ {tempo}\x27\x27 minutos\n\n"
                        f"📊 ESTATÍSTICAS DE PRESSÃO:\n"
                        f"• APPM (Pressão): {appm_pressionado:.2f}/min\n"
                        f"• Finalizações: {finalizacoes} (No Gol: {total_chutes_gol})\n"
                        f"• Ataques Perigosos: {att_casa} x {att_fora}\n"
                        f"• Escanteios Totais: {total_cantos}\n\n"
                        f"🎯 RECOMENDAÇÃO:\n"
                        f"👉 Over {line_gol} Gols\n"
                        f"💡 Odd Recomendada: 1.65 até 2.05\n\n"
                        f"👇 Clique abaixo para buscar o time nas casas:"
                    )
                    print(f"🔥 SINAL DISPARADO [GOL]: {casa} x {fora} ({tempo}\x27\x27)")
                    enviar_telegram(msg_gol, casa=casa, fora=fora)
                    sinais_gols_enviados.add(fixture_id)
                    sinais_gols += 1

            # 🚩 ALERTA DE ESCANTEIOS
            if precisa_cantos:
                if total_cantos >= 5 and appm_pressionado >= 0.65 and (finalizacoes >= 9 or chutes_bloqueados >= 2):
                    canto_limite = total_cantos + 0.5

                    msg_canto = (
                        f"🚩 ALERTA CANTO LIMITE (RETA FINAL) ⚽\n\n"
                        f"🏴 {pais}\n"
                        f"⚽ {casa} {gols_casa} x {gols_fora} {fora}\n"
                        f"⏱️ {tempo}\x27\x27 minutos\n\n"
                        f"📊 PRESSÃO NOS ESCANTEIOS:\n"
                        f"• Cantos Atuais: {total_cantos} ({c_casa} x {c_fora})\n"
                        f"• Chutes Bloqueados: {chutes_bloqueados}\n"
                        f"• APPM Reta Final: {appm_pressionado:.2f}\n\n"
                        f"🎯 RECOMENDAÇÃO:\n"
                        f"👉 Over {canto_limite} Escanteios\n"
                        f"💡 Odd Recomendada: 1.60+\n\n"
                        f"👇 Clique abaixo para buscar o time nas casas:"
                    )
                    print(f"🔥 SINAL DISPARADO [CANTOS]: {casa} x {fora} ({tempo}\x27\x27)")
                    enviar_telegram(msg_canto, casa=casa, fora=fora)
                    sinais_cantos_enviados.add(fixture_id)
                    sinais_cantos += 1

        print(f"🔎 FUNIL DE ANÁLISE:")
        print(f"  └ Total Ao Vivo: {total_jogos_ao_vivo}")
        print(f"  └ Na janela de tempo: {jogos_na_janela_tempo}")
        print(f"  └ Placar parelho (diff <= 1): {jogos_placar_parelho}")
        print(f"  └ Stats consultadas: {stats_analisadas}")
        print(f"  └ Sinais Disparados -> Gols: {sinais_gols} | Cantos: {sinais_cantos}")

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Oscilação na conexão com a API ({e}). Aguardando próximo ciclo...")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    print("=== BOT DUAL 24H INICIADO ===")
    while True:
        analisar_jogos()
        time.sleep(120)
