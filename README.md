# TV Italia + Puglia — Nuvio

Catalogo TV italiano con monitoraggio notturno delle playlist M3U/HLS/DASH.

## Stato e copertura

- **152 canali monitorati** nell'ultima scansione (il conteggio cambia quando si correggono le numerazioni o si elimina un duplicato): 39 nella playlist originale, emittenti gratuite aggiuntive, 61 nuovi nomi Sky/pay TV e 6 voci DTT in una watchlist separata. Non tutti hanno uno streaming accessibile.
- **13 playlist pubbliche** controllate automaticamente, oltre alle sorgenti aggiuntive curate.
- Le locandine in Nuvio compaiono **solo se esiste una sorgente verificata** o se una verifica aggiuntiva effettuata dal Worker conferma manifest e segmento video.
- I canali non confermati restano nella scansione notturna, ma **non vengono eliminati definitivamente**.
- Le dirette a pagamento non vengono aggirate né decriptate.

## Architettura

1. `scripts/nightly_check.py`: recupera playlist M3U, confronta nomi/LCN e verifica gli stream. Controlla manifest HLS e segmenti o manifest DASH non protetti.
2. `.github/workflows/nightly-tv-check.yml`: esegue i test e rigenera `data/verified-streams.json` + `data/stream-report.md` ogni notte alle **02:17 UTC**.
3. `cloudflare/worker-tv-v3.9.1.js`: fornisce manifest, catalogo, loghi e stream a Nuvio, mantenendo gli ID originali. Accetta le sorgenti verificate e prova, entro un limite di richieste, quelle inconcludenti quando arriva una richiesta dall'Italia.

La localizzazione del visitatore **non garantisce** che il server Cloudflare effettui richieste con un IP italiano. Per questo un 403 rimane un esito incerto e non viene trasformato in `verified`.

## Link

- [Ultima scansione](data/verified-streams.json)
- [Rapporto canali e sorgenti](data/stream-report.md)
- [Lista originale](TV_Italia_Puglia_con_loghi.m3u)
- [39 emittenti aggiuntive](data/additional-channels.m3u)
- [Sky e altre emittenti monitorate](data/channel-watchlist.json)
- [Worker 3.9.1](cloudflare/worker-tv-v3.9.1.js)

## Pubblicazione in Cloudflare

L'aggiornamento dello script GitHub **non pubblica automaticamente il Worker**.

1. Accedi a Cloudflare → **Workers & Pages** → Worker `tv` (usa il nome esatto mostrato nella dashboard).
2. Apri **Edit code**, incolla tutto il contenuto di `cloudflare/worker-tv-v3.9.1.js` e premi **Deploy**.
3. Apri `https://tv.annalisazotti11.workers.dev/manifest.json` e verifica che la versione sia `3.9.1`.
4. Apri `/debug/notte.json` per i canali notturni oppure `/debug/italia.json` da connessione italiana per la seconda verifica.

Mantieni lo stesso Worker e lo stesso manifest già installato in Nuvio: l'ID addon non cambia.

### Limiti

«Tutti i canali» significa tutti quelli **monitorati** nel database, non che tutte le emittenti abbiano una diretta riproducibile. I 403 possono dipendere dalla geolocalizzazione. I collegamenti senza prova positiva non fanno comparire nuove locandine. I canali premium richiedono sorgenti autorizzate e, se necessario, l'abbonamento del titolare.
