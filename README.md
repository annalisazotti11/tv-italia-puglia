# TV Italia + Puglia — Nuvio

Catalogo TV italiano con monitoraggio notturno delle playlist M3U/HLS/DASH.

## Stato e copertura

- **217 canali monitorati** nell'ultima scansione: playlist originale, 39 emittenti aggiuntive, Sky/Sky Cinema/Sky Sport, news internazionali e TV locali pugliesi. Il numero può variare con gli aggiornamenti. La presenza nel database non garantisce una diretta funzionante.
- **18 raccolte pubbliche o curate** controllate automaticamente, comprese quattro nuove playlist italiane. Sono presenti **42 sorgenti aggiuntive curate**. Il numero di canali riproducibili può variare a ogni scansione: consulta [il rapporto](data/stream-report.md).
- Le locandine in Nuvio compaiono **solo se esiste una sorgente verificata** o se una verifica aggiuntiva effettuata dal Worker conferma manifest e segmento video.
- I canali non confermati restano nella scansione notturna, ma **non vengono eliminati definitivamente**.
- Le dirette a pagamento non vengono aggirate né decriptate.

## Architettura

1. `scripts/nightly_check.py`: recupera playlist M3U, confronta nomi/LCN e verifica gli stream. Controlla manifest HLS e segmenti o manifest DASH non protetti.
2. `.github/workflows/nightly-tv-check.yml`: esegue i test e rigenera `data/verified-streams.json`, `data/stream-report.md` e la guida `data/epg-guide.json` ogni notte alle **02:17 UTC**.
3. `scripts/update_epg.py`: acquisisce XMLTV da TvIt/SuperGuidaTV e IPTV-EPG Italia; associa solo nomi non ambigui, converte gli orari UTC e scarta i titoli fittizi come «No Data».
4. `cloudflare/worker-tv-v4.1.0.js`: conserva ID, catalogo e ordine originale, ma aggiunge locandine con loghi, informazioni «Ora in onda» e «A seguire», orari locali, guide TV web e JSON. Accetta le sorgenti verificate e ricontrolla le fonti geograficamente incerte nei limiti del piano gratuito.

### Interfaccia TV versione 4.1

- Le locandine ora hanno sfondo antracite neutro, bordo discreto e niente enorme riquadro bianco. I loghi nuovi rilevati dalla scansione vengono preferiti a quelli vecchi, con fallback se l'immagine principale non è più raggiungibile. Per i PNG opachi viene attenuato/rimosso il bianco del fondale, senza modificare i nomi dei canali.
- **Rai 3 TGR Puglia** è prioritario: ID stabile `tvip_103_rai-3-tgr-puglia`, numero visualizzato come **3 Puglia**, prima posizione nella lista, loghi dedicati e nuova verifica HbbTV. Se la scansione rileva soltanto un errore HLS ambiguo può mantenere per massimo 36 ore l'ultima sorgente davvero verificata, indicandola come non più fresca; la riproduzione viene ricontrollata all'apertura.
- Le schede Nuvio riportano **programma in onda, orari e programma successivo** soltanto se esiste un palinsesto XMLTV affidabile; altrimenti indicano che la programmazione non è disponibile.
- La pagina `/guida` permette ricerca, filtri per categoria, stato LIVE e avanzamento del programma. I programmi possono cambiare senza preavviso.
- Gli stream non verificati rimangono nascosti e i canali Sky premium non vengono aggirati.
- La guida e la disponibilità dipendono dalle sorgenti esterne. Nuvio può conservare i metadati nella sua cache; aggiornare la Home o riaprire la scheda per vedere le ultime informazioni.

La localizzazione del visitatore **non garantisce** che il server Cloudflare effettui richieste con un IP italiano. Per questo un 403 rimane un esito incerto e non viene trasformato in `verified`.

## Link

- [Ultima scansione](data/verified-streams.json)
- [Rapporto canali e sorgenti](data/stream-report.md)
- [Lista originale](TV_Italia_Puglia_con_loghi.m3u)
- [39 emittenti aggiuntive](data/additional-channels.m3u)
- [Sky, news internazionali e altre emittenti monitorate](data/channel-watchlist.json)
- [Sorgenti gratuite curate e verificate dalla scansione](data/extended-sources.m3u)
- [Guida EPG con programmi e orari](data/epg-guide.json)
- [Template responsive della guida TV](data/guide-ui.html)
- [Worker 4.1.0](cloudflare/worker-tv-v4.1.0.js)

## Quarantena sicurezza — 4.9.2

La versione [4.9.2](cloudflare/worker-tv-v4.9.2.js) preserva il ranking e la singola sorgente della 4.9.1, applicando la quarantena anche nel Worker, escludendo URL duplicati tra canali e richiedendo per Canale 5 una sorgente Mediaset con audio/video confermati e nessun reindirizzamento. Consulta il [rapporto di revisione del 25 novembre](data/source-identity-audit.md). Aggiornare il Worker effettivamente installato in Nuvio (manifest già in uso) con il codice 4.9.2. La versione live deve essere verificata dopo il Deploy.

## Pubblicazione in Cloudflare

L'aggiornamento dello script GitHub **non pubblica automaticamente il Worker**.

1. Accedi a Cloudflare → **Workers & Pages** → Worker `tv-italia-puglia` (usa il nome esatto mostrato nella dashboard).
2. Apri **Edit code**, incolla tutto il contenuto di `cloudflare/worker-tv-v4.9.2.js` e premi **Deploy**.
3. Apri `https://tv-italia-puglia.annalisazotti11.workers.dev/manifest.json` e verifica che la versione sia `4.9.2`.
4. Apri `/guida` per la nuova guida visiva, `/api/guida.json` per i programmi in corso, `/debug/notte.json` per gli esiti della scansione oppure `/debug/italia.json` da una connessione italiana per la seconda verifica.

Mantieni lo stesso Worker e lo stesso manifest già installato in Nuvio: l'ID addon non cambia.

### Limiti

«Tutti i canali» significa tutti quelli **monitorati** nel database, non che tutte le emittenti abbiano una diretta riproducibile. I 403 possono dipendere dalla geolocalizzazione. I collegamenti senza prova positiva non fanno comparire nuove locandine. I canali premium richiedono sorgenti autorizzate e, se necessario, l'abbonamento del titolare.
