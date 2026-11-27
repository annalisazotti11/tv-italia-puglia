# TV Italia + Puglia — Nuvio

Catalogo TV italiano con monitoraggio notturno delle playlist M3U/HLS/DASH.

## Stato e copertura

- **226 canali monitorati** nell'ultima scansione: playlist originale, 39 emittenti aggiuntive, Sky/Sky Cinema/Sky Sport, news internazionali e TV locali pugliesi. Il numero può variare con gli aggiornamenti. La presenza nel database non garantisce una diretta funzionante.
- **19 raccolte pubbliche o curate** controllate automaticamente, comprese quattro nuove playlist italiane. Sono presenti **42 sorgenti aggiuntive curate**. Il numero di canali riproducibili può variare a ogni scansione: consulta [il rapporto](data/stream-report.md).
- L'inventario `data/playlist-sources.json` contiene **80 voci** di playlist e indici; include anche voci `index_only` e mirror/fork, quindi non equivale a 79 sorgenti indipendenti, funzionanti o autorizzate.
- Le sorgenti candidate trovate negli indici pubblici non diventano automaticamente sorgenti di riproduzione: devono superare i controlli di identità, provenienza, autorizzazione e riproducibilità.
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
- Gli stream non verificati rimangono esclusi su tutti i canali. I canali premium non vengono aggirati.
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
- [Piattaforme ufficiali e canali premium, con canali Sky Go confermati](data/official-platform-catalog.json)
- [Manifest candidati trovati su pagine ufficiali (da verificare, non pubblicati)](data/official-manifest-candidates-2026-11-27.json)
- [Indici community metadata-only, senza endpoint di streaming](data/community-channel-indexes.json)
- [Worker 4.1.0](cloudflare/worker-tv-v4.1.0.js)
- [Worker 5.1.0](cloudflare/worker-tv-v5.1.0.js)
- [Watchlist canali](data/channel-watchlist.json)
- [Configurazione Wrangler](wrangler.jsonc)
- [Test Worker 5.1.0](scripts/test_worker_v510.mjs)
- [Workflow test Worker](.github/workflows/test-worker.yml)
- [Workflow deployment Cloudflare](.github/workflows/deploy-worker.yml)

## Canale 5 — stato della sorgente Redge

Il flusso Redge individuato in una playlist community è stato riprodotto tecnicamente in VLC, ma la sola raggiungibilità non dimostra che il distributore sia il titolare o che la redistribuzione nell'addon sia autorizzata. Per questo l'override diretto introdotto durante la prova 4.9.6 è stato ritirato prima del deployment e il relativo file è stato rimosso dal ramo `main`.

**Non distribuire né utilizzare copie locali delle versioni 4.9.5/4.9.6 che contengono l'override Redge.** Il collegamento ufficiale Mediaset Infinity e le sorgenti Mediaset ammesse restano il riferimento per Canale 5. La nota tecnica conserva lo storico della verifica e della decisione: [revisione tecnica e dei diritti](data/canale5-redge-authorization-review-2026-11-26.md).

La ricerca automatica può continuare a individuare nuove voci nelle playlist pubbliche, ma la presenza in una lista, un manifest HLS valido o un test VLC non costituiscono prova di autorizzazione. Le candidate non approvate restano in revisione e non vengono pubblicate come dirette in Nuvio.

## Worker 5.1.0 — watchlist e deployment controllato

La nuova pipeline [audited-tv.yml](.github/workflows/audited-tv.yml) gira ogni notte alle **02:47 UTC** (03:47 in Italia in inverno, 04:47 in estate). La ricerca nelle playlist registrate rimane nel workflow notturno precedente. Una nuova voce community non viene promossa automaticamente: il nuovo controllo apre esclusivamente i percorsi emittente/CDN già revisionati, rispettando la quarantena e senza aggirare DRM o limitazioni geografiche. La revisione tecnica non costituisce una licenza generale di redistribuzione.

Per ciascun percorso il controllo verifica manifest, pacchetti audio/video, risoluzione rilevata e almeno tre fotogrammi in RAM, analizzati con il rilevatore locale NudeNet. Se il modello non è disponibile, il campione è insufficiente o viene rilevato contenuto esplicito, la sorgente non viene inserita nell'indice. Nessun fotogramma viene pubblicato. Il campionamento non garantisce l'identità del canale o l'assenza futura di contenuti espliciti: il riconoscimento di watermark necessita di riferimenti autentici, attualmente mancanti.

La graduatoria considera risoluzione fino a 2160p, storico dei successi, tempi di verifica e codec. Il [Worker 5.1.0](cloudflare/worker-tv-v5.1.0.js) legge il nuovo indice separato `data/audited-streams.json`, scarta esiti più vecchi di 36 ore e restituisce la sola sorgente meglio classificata. Restano invariati ID addon, ID canali, EPG e priorità TGR Puglia. Le riserve sono nell'indice, non vengono esposte tutte al player. Canale 5 mantiene il collegamento ufficiale se non esiste uno stream diretto verificato. Il Worker 5.1.0 integra anche `data/channel-watchlist.json` come metadati: i sette nuovi candidati sono presenti nel monitoraggio e in `/debug/channels.json`, ma non entrano nel catalogo Nuvio finché non superano il controllo visivo e la revisione d'identità. Gli endpoint delle fonti community `index_only` non vengono esposti.

**Primo run (27 novembre 2026, ore 00:53 italiane):** 150 sorgenti testate, 31 passate, 30 canali con controllo completo. La scansione precedente rilevava audio e video su 72 canali; 44 di questi non sono presenti nel nuovo indice. Tra gli esiti negativi figurano 48 HTTP 403, 35 manifest non disponibili, 14 redirect HTTP 301/302 e 10 timeout FFprobe. Non sono tutti errori geografici accertati.

**Aggiornamento:** un secondo tentativo è previsto solo per gli errori temporanei; nessun retry su HTTP 403 o allarme esplicito. La diagnostica per canale distingue le fonti fallite dai canali privi di sorgenti revisionate; non pubblica URL falliti. Il Worker ricontrolla anche il registro di revisione corrente prima di servire le sorgenti. Il codice supporta il riscontro dei watermark autentici quando si forniscono i relativi template; al momento il registro dei template è vuoto. Il nuovo run e i nuovi test non sono ancora confermati.

**Copertura attuale:** l'ultimo indice visivo ha 30 canali visibili su 219 monitorati. La nuova release mantiene questa soglia qualitativa: i candidati non revisionati non vengono promossi automaticamente. Il deployment 5.1.0 viene avviato soltanto dopo il completamento positivo dell'audit visivo e dei test automatici.

## Pubblicazione in Cloudflare

Il deployment è gestito da direttamente in [audited-tv.yml](.github/workflows/audited-tv.yml), dopo il completamento positivo dell'audit visivo e dei test. Prima del rilascio vengono eseguiti i test automatici del Worker 5.1.0. Il workflow usa [wrangler.jsonc](wrangler.jsonc), aggiorna il Worker esistente `tv-italia-puglia`, verifica `/manifest.json` e `/debug/channels.json` e registra l'esito in [deployment-status.json](data/deployment-status.json). Richiede i GitHub Actions secrets `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID` (l'account ID può essere anche una repository variable con lo stesso nome). Il token deve avere permesso di modifica dei Workers; non va inserito nel repository. **Non distribuire la build 4.9.6 ritirata.**

Per verificare la versione attualmente attiva apri `/manifest.json` sul dominio Worker già configurato in Nuvio. Dopo una release validata, il deployment avverrà sullo stesso Worker e manterrà invariato l'ID addon.
## Pilota analisi del contenuto (Canale 5)

Il [workflow pilota](.github/workflows/content-identity-pilot.yml) è separato dai flussi di produzione e si esegue ogni ora o manualmente. Campiona alcuni fotogrammi in RAM dalle quattro rotte Mediaset ammesse e da Rai 3 TGR Puglia, Radio Italia TV e Il Sole 24 Ore TV usati come controlli. I risultati confrontano scene distinte (impronte percettive), eseguono uno screening locale per contenuti espliciti e, quando è disponibile una sagoma del marchio in onda validata, il riconoscimento del watermark. Un logo generico non viene considerato prova sufficiente.

L'output è un piccolo report JSON negli artifact di GitHub Actions: nessuna immagine, audio, video o URL non autorizzato viene salvato; un mancato accesso geografico resta incerto. I gruppi di sorgenti precedentemente esclusi restano in una coda di revisione di sola metadatazione. Le fonti fuori allowlist non vengono aperte senza prova della loro autorizzazione. Nessun esito del pilota cambia il catalogo o riabilita sorgenti automaticamente. Per un controllo al momento del Play serve un validatore accessibile sulla rete del titolare, non il solo Worker. 

Avvio manuale: `PYTHONPATH=scripts python -m unittest discover -s pilot_tests -v`; analisi: `python scripts/content_identity.py --output artifacts/content-identity-pilot-report.json` (FFmpeg, Pillow e NudeNet installati). Il modello di sicurezza ha possibili falsi negativi/positivi: un'assenza di allarme non garantisce la sicurezza del contenuto.

### Analisi di campioni autorizzati locali

Il [programma locale](tools/local-sample-analysis/LEGGIMI.txt) accetta esclusivamente video o immagini già disponibili sul computer, non URL o playlist. Confronta un campione della diretta autentica con un candidato acquisito legalmente nello stesso intervallo; genera un JSON senza conservare i fotogrammi. Il test diretto con Chrome ha mostrato ERR_BLOCKED_BY_CLIENT per le rotte Mediaset HLS e DASH: non è stato possibile analizzare il contenuto e non si tenta di aggirare il blocco. Nessun esito locale modifica il catalogo automaticamente.


### Nuove fonti community — sola identificazione

`nicolofajette/Canali` è registrata come `index_only`: il workflow legge i nomi dei canali ma non prova gli endpoint della playlist. È stata aggiunta anche `untiiis/liste` con la stessa modalità e filtro sul `group-title` Italia (51 voci italiane, anziché usare le 1.473 voci globali). Le etichette community non confermate (per esempio Sky Cinema Due e alcune voci DAZN) restano nella watchlist come metadati e non vengono mostrate in Nuvio senza una sorgente verificata e autorizzata. Gli indici non-M3U sono documentati in `data/community-channel-indexes.json`.
