"""
Google Maps Scraper — Wszystkie firmy bez www
Uruchom: python app.py → http://localhost:5000
"""

from flask import Flask, render_template, jsonify, send_file, Response
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import threading, time, csv, re, json, os
from datetime import datetime

app = Flask(__name__)

# ─── 40 największych miast ────────────────────────────────────────────────────
MIASTA = [
    "Warszawa", "Kraków", "Łódź", "Wrocław", "Poznań",
    "Gdańsk", "Szczecin", "Bydgoszcz", "Lublin", "Katowice",
    "Białystok", "Gdynia", "Częstochowa", "Radom", "Sosnowiec",
    "Toruń", "Kielce", "Rzeszów", "Gliwice", "Zabrze",
    "Olsztyn", "Bielsko-Biała", "Bytom", "Zielona Góra", "Rybnik",
    "Ruda Śląska", "Opole", "Tychy", "Gorzów Wielkopolski", "Elbląg",
    "Płock", "Dąbrowa Górnicza", "Wałbrzych", "Włocławek", "Tarnów",
    "Chorzów", "Koszalin", "Kalisz", "Legnica", "Grudziądz",
]

# ─── Branże do pominięcia ─────────────────────────────────────────────────────
POMIJANE_BRANZE = {
    "siedziba główna", "siedziba firmy", "biuro główne", "biuro zarządu",
    "holding", "korporacja", "spółka holdingowa", "park biznesowy",
    "centrum biznesowe", "inkubator przedsiębiorczości",
    "corporate headquarters", "headquarters", "corporate office",
    "business center", "office building", "office complex",
    "government office", "embassy", "consulate",
    "urząd", "urząd gminy", "urząd miasta", "urząd skarbowy",
    "starostwo", "ambasada", "konsulat", "ministerstwo",
    "agencja rządowa", "instytucja rządowa",
}

POMIJANE_SLOWA_W_NAZWIE = [
    "headquarters", " hq", "head office", "siedziba główna",
    "zarząd główny", "dyrekcja generalna", "centrala sp",
]


def czy_pominac(nazwa: str, branza: str):
    nazwa_low  = nazwa.lower()
    branza_low = branza.lower()
    for slowo in POMIJANE_SLOWA_W_NAZWIE:
        if slowo in nazwa_low:
            return True, f"nazwa zawiera '{slowo}'"
    for b in POMIJANE_BRANZE:
        if b in branza_low:
            return True, f"branża: '{branza}'"
    return False, ""


# ─── Stan ─────────────────────────────────────────────────────────────────────
state = {
    "running": False, "done": False, "error": None,
    "progress": [], "results": [], "output_file": None,
    "stats": {
        "total": 0, "bez_www": 0, "pominieto": 0,
        "ma_www": 0, "brak_danych": 0,
        "cities_done": 0, "cities_total": len(MIASTA),
        "current_city": "", "cities_stats": {},
        "start_time": None, "elapsed_sec": 0,
    },
}
lock = threading.Lock()
_start_ts = None


def reset():
    with lock:
        state.update(
            running=True, done=False, error=None,
            progress=[], results=[], output_file=None,
            stats={
                "total": 0, "bez_www": 0, "pominieto": 0,
                "ma_www": 0, "brak_danych": 0,
                "cities_done": 0, "cities_total": len(MIASTA),
                "current_city": "", "cities_stats": {},
                "start_time": datetime.now().isoformat(),
                "elapsed_sec": 0,
            }
        )


def log(msg, typ="info"):
    entry = {"msg": msg, "typ": typ, "ts": datetime.now().strftime("%H:%M:%S")}
    with lock:
        state["progress"].append(entry)
    print(f"[{entry['ts']}] {msg}")


def accept_cookies(page):
    log("  🍪 Szukam okna cookies...", "detail")
    try:
        b = page.locator('button:has-text("Zaakceptuj wszystko"), button:has-text("Accept all")')
        if b.count():
            b.first.click()
            log("  🍪 Cookies zaakceptowane", "detail")
            time.sleep(1)
        else:
            log("  🍪 Brak okna cookies", "detail")
    except Exception as e:
        log(f"  🍪 Błąd cookies: {e}", "detail")


def get_links(page, miasto, max_results=80):
    url = f"https://www.google.com/maps/search/firmy+{miasto.replace(' ', '+')}"
    log(f"  🌐 GET {url}", "detail")
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        log(f"  🌐 Załadowano, czekam 3s...", "detail")
        time.sleep(3)
        accept_cookies(page)
        time.sleep(1)
    except Exception as e:
        log(f"  ❌ Błąd ładowania {miasto}: {e}", "error")
        return []

    links = set()
    prev = 0
    no_change = 0

    for scroll_n in range(30):
        if len(links) >= max_results:
            break
        els = page.locator('a[href*="/maps/place/"]').all()
        before = len(links)
        for el in els:
            href = el.get_attribute("href") or ""
            if "/maps/place/" in href:
                links.add(re.sub(r'\?.*', '', href))
        new_found = len(links) - before
        log(f"  🔄 Scroll {scroll_n+1}: +{new_found} nowych (łącznie: {len(links)})", "detail")

        if len(links) == prev:
            no_change += 1
            if no_change >= 4:
                log(f"  ⏹ Koniec listy po {scroll_n+1} scrollach", "detail")
                break
        else:
            no_change = 0
        prev = len(links)

        try:
            page.locator('div[role="feed"]').evaluate("el => el.scrollBy(0, 800)")
        except:
            pass
        time.sleep(1.2)

    return list(links)[:max_results]


def get_firm_data(page, url, n, total):
    slug = url.split('/place/')[-1][:45].replace('+', ' ')
    log(f"  🔍 [{n}/{total}] {slug}", "detail")

    try:
        page.goto(url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(1.5)

        d = {
            "nazwa": "", "branza": "", "adres": "", "telefon": "",
            "strona_www": "", "ocena": "", "liczba_opinii": "",
            "godziny": "", "url_gmaps": url,
        }

        try:
            d["nazwa"] = page.locator('h1').first.inner_text(timeout=3000).strip()
            log(f"     📛 {d['nazwa'][:55]}", "detail")
        except:
            log(f"     ⚠️  Brak nazwy", "detail")

        try:
            kat = page.locator('button[jsaction*="category"], button.DkEaL').first
            if kat.count():
                d["branza"] = kat.inner_text(timeout=2000).strip()
                log(f"     🏷  Branża: {d['branza']}", "detail")
        except:
            pass

        try:
            el = page.locator('[data-item-id="address"]').first
            if el.count():
                v = el.get_attribute("aria-label", timeout=2000) or ""
                d["adres"] = v.replace("Adres: ", "").strip()
                log(f"     📍 {d['adres'][:55]}", "detail")
            else:
                log(f"     📍 brak adresu", "detail")
        except:
            pass

        try:
            el = page.locator('[data-item-id*="phone"]').first
            if el.count():
                v = el.get_attribute("aria-label", timeout=2000) or ""
                d["telefon"] = re.sub(r'^(Telefon|Phone): ', '', v).strip()
                log(f"     📞 {d['telefon']}", "detail")
            else:
                log(f"     📞 brak telefonu", "detail")
        except:
            pass

        try:
            el = page.locator('[data-item-id="authority"]').first
            if el.count():
                v = el.get_attribute("aria-label", timeout=2000) or ""
                d["strona_www"] = re.sub(r'^(Witryna|Website): ', '', v).strip()
                log(f"     🌐 WWW: {d['strona_www'][:50]}", "detail")
            else:
                log(f"     🌐 brak strony www ✅", "detail")
        except:
            pass

        try:
            el = page.locator('div.F7nice span[aria-hidden="true"]').first
            if el.count():
                d["ocena"] = el.inner_text(timeout=2000).strip()
        except:
            pass

        try:
            el = page.locator('div.F7nice span[aria-label*="opini"], div.F7nice span[aria-label*="review"]').first
            if el.count():
                label = el.get_attribute("aria-label", timeout=2000) or ""
                nums = re.findall(r'\d+', label.replace(",", "").replace(" ", ""))
                if nums:
                    d["liczba_opinii"] = nums[0]
            if d["ocena"]:
                log(f"     ⭐ {d['ocena']} ({d['liczba_opinii']} opinii)", "detail")
        except:
            pass

        try:
            el = page.locator('[data-item-id*="oh"]').first
            if el.count():
                v = el.get_attribute("aria-label", timeout=2000) or ""
                d["godziny"] = v[:80].strip()
        except:
            pass

        return d

    except Exception as e:
        log(f"     ❌ Błąd: {e}", "error")
        return None


def save_csv(results):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"firmy_bez_www_{ts}.csv")
    fields = ["nazwa", "branza", "adres", "telefon", "ocena", "liczba_opinii", "godziny", "url_gmaps"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    return path


def scrape_worker():
    global _start_ts
    _start_ts = time.time()
    try:
        log(f"🚀 Start — {len(MIASTA)} miast, wszystkie branże", "start")
        log(f"🚫 Aktywny filtr: pomijam siedziby główne, biura, urzędy", "start")
        log(f"", "info")

        with sync_playwright() as p:
            log("🖥  Uruchamiam Chromium (headless)...", "detail")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="pl-PL"
            )
            page = ctx.new_page()
            log("🖥  Przeglądarka gotowa", "detail")

            for i, miasto in enumerate(MIASTA):
                with lock:
                    if not state["running"]:
                        log("⏹ Zatrzymano przez użytkownika", "error")
                        break
                    state["stats"]["current_city"] = miasto

                log(f"", "info")
                log(f"━━━ MIASTO [{i+1}/{len(MIASTA)}]: {miasto.upper()} ━━━", "city")

                links = get_links(page, miasto)
                log(f"  ✔ Zebrano {len(links)} linków", "info")

                city_stats = {"sprawdzono": 0, "bez_www": 0, "ma_www": 0, "pominieto": 0, "brak_danych": 0}

                for j, link in enumerate(links):
                    with lock:
                        if not state["running"]: break
                        state["stats"]["elapsed_sec"] = int(time.time() - _start_ts)

                    data = get_firm_data(page, link, j + 1, len(links))

                    if not data or not data["nazwa"]:
                        log(f"  ⚠️  [{j+1}/{len(links)}] Brak danych — pomijam", "detail")
                        city_stats["brak_danych"] += 1
                        with lock: state["stats"]["brak_danych"] += 1
                        time.sleep(0.5)
                        continue

                    with lock: state["stats"]["total"] += 1
                    city_stats["sprawdzono"] += 1

                    pominac, powod = czy_pominac(data["nazwa"], data["branza"])
                    if pominac:
                        log(f"  🚫 [{j+1}/{len(links)}] POMINIĘTO ({powod}): {data['nazwa'][:40]}", "skip")
                        city_stats["pominieto"] += 1
                        with lock: state["stats"]["pominieto"] += 1
                        time.sleep(1.0)
                        continue

                    if not data["strona_www"]:
                        with lock:
                            state["results"].append(data)
                            state["stats"]["bez_www"] += 1
                        city_stats["bez_www"] += 1
                        branza = f" [{data['branza']}]" if data["branza"] else ""
                        tel = f" ☎{data['telefon']}" if data["telefon"] else ""
                        log(f"  ✅ [{j+1}/{len(links)}] BRAK WWW: {data['nazwa'][:40]}{branza}{tel}", "found")
                    else:
                        city_stats["ma_www"] += 1
                        with lock: state["stats"]["ma_www"] += 1
                        log(f"  🌐 [{j+1}/{len(links)}] Ma WWW: {data['nazwa'][:35]} → {data['strona_www'][:30]}", "detail")

                    time.sleep(1.0 + (j % 3) * 0.2)

                with lock:
                    state["stats"]["cities_done"] = i + 1
                    state["stats"]["cities_stats"][miasto] = city_stats

                log(f"", "info")
                log(f"  📊 {miasto}: sprawdzono={city_stats['sprawdzono']} | bez_www={city_stats['bez_www']} | ma_www={city_stats['ma_www']} | pominięto={city_stats['pominieto']} | brak_danych={city_stats['brak_danych']}", "info")

            log(f"", "info")
            log("🖥  Zamykam przeglądarkę...", "detail")
            browser.close()
            log("🖥  Przeglądarka zamknięta", "detail")

        with lock:
            results = state["results"][:]
            stats = state["stats"].copy()

        if results:
            log(f"", "info")
            log(f"💾 Zapisuję {len(results)} firm do pliku CSV...", "info")
            path = save_csv(results)
            with lock: state["output_file"] = path
            log(f"💾 Zapisano: {os.path.basename(path)}", "done")

        elapsed = int(time.time() - _start_ts)
        m, s = divmod(elapsed, 60)
        log(f"", "info")
        log(f"🏁 ══════════ PODSUMOWANIE KOŃCOWE ══════════", "done")
        log(f"   ⏱  Czas trwania:        {m}m {s}s", "done")
        log(f"   🏙  Miast przeskanowano: {stats['cities_done']} / {len(MIASTA)}", "done")
        log(f"   🔎 Sprawdzono firm:     {stats['total']}", "done")
        log(f"   ✅ Bez strony www:      {stats['bez_www']}", "done")
        log(f"   🌐 Ma stronę www:       {stats['ma_www']}", "done")
        log(f"   🚫 Pominięto (filtr):   {stats['pominieto']}", "done")
        log(f"   ⚠️  Brak danych:         {stats['brak_danych']}", "done")
        if stats["total"] > 0:
            pct = round(stats["bez_www"] / stats["total"] * 100, 1)
            log(f"   📈 % firm bez www:      {pct}%", "done")
        log(f"🏁 ═════════════════════════════════════════", "done")

    except Exception as e:
        log(f"❌ Krytyczny błąd: {e}", "error")
        import traceback
        log(traceback.format_exc(), "error")
        with lock: state["error"] = str(e)
    finally:
        with lock:
            state["running"] = False
            state["done"] = True
            state["stats"]["elapsed_sec"] = int(time.time() - _start_ts)


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index(): return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    with lock:
        if state["running"]: return jsonify(ok=False, error="Już działa")
    reset()
    threading.Thread(target=scrape_worker, daemon=True).start()
    return jsonify(ok=True)

@app.route("/stop", methods=["POST"])
def stop():
    with lock: state["running"] = False
    return jsonify(ok=True)

@app.route("/status")
def status():
    with lock:
        s = state["stats"].copy()
        if state["running"] and _start_ts:
            s["elapsed_sec"] = int(time.time() - _start_ts)
        return jsonify(
            running=state["running"], done=state["done"],
            stats=s, results_count=len(state["results"]),
            has_file=state["output_file"] is not None, error=state["error"]
        )

@app.route("/stream")
def stream():
    def generate():
        sent = 0
        while True:
            with lock:
                prog = state["progress"][:]
                done = state["done"]
            while sent < len(prog):
                yield f"data: {json.dumps(prog[sent], ensure_ascii=False)}\n\n"
                sent += 1
            if done and sent >= len(prog):
                yield 'data: {"typ":"end"}\n\n'
                break
            time.sleep(0.2)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/results")
def results():
    with lock: return jsonify(state["results"][:500])

@app.route("/download")
def download():
    with lock: path = state["output_file"]
    if not path or not os.path.exists(path): return "Brak pliku", 404
    return send_file(path, as_attachment=True, mimetype="text/csv")

if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    print("\n✅ Otwórz http://localhost:5000\n")
    app.run(debug=False, port=5000, threaded=True)
