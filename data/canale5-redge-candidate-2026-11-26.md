# Canale 5 — candidato Redge Media (26 novembre 2026)

## Candidato principale emerso
Canale 5 HD (1080p) è ora presente nel catalogo upstream iptv-org:
https://github.com/iptv-org/iptv/blob/master/streams/it.m3u

URL dichiarato:
https://n-5-1.eu.cdn-redge.media/livehls/oeu/mt/live/canale_5/live.livx/playlist.m3u8

La richiesta di inserimento upstream #58904 è chiusa come completata e ha le etichette `approved` e `check:passed`; il richiedente ha dichiarato `Geo-blocked: No`.
https://github.com/iptv-org/iptv/issues/58904

Questa è una conferma più forte rispetto alle vecchie copie della sorgente Mediaset: è un endpoint HLS separato, su CDN Redge, segnalato a 1080p e non etichettato come geo-bloccato dal progetto. Tuttavia, l'approvazione di iptv-org è una verifica del progetto e non certifica da sola i diritti di ridistribuzione, né garantisce la riproduzione dalla rete italiana.

## Riscontri indipendenti
- 91 Live pubblica lo stesso endpoint nella lista Italia, ma specifica che il controllo automatico è eseguito da Singapore e che molti flussi esteri possono essere geo-limitati:
  https://www.91zhibo.net/iptv/overseas/?country=IT
- B2OG elenca Canale 5 HD 1080p sullo stesso host:
  https://iptv.b2og.com/list/o_all.list
- Reefquiet Italia include lo stesso URL:
  https://github.com/reefquiet/iptv-playlists/blob/main/countries/it.m3u
- IPTV-CH mantiene anche una playlist Redge dedicata con un alias host `r.eu.cdn-redge.media` per Canale 5; è un alias non ancora verificato:
  https://github.com/iptv-ch/iptv-ch.github.io/blob/master/redgemedia.m3u

## Modifiche al progetto dell'utente
- Aggiunta `91 Live Overseas index` al registro come `index_only`.
- Aggiunta `IPTV-CH Redge Media index` al registro come `index_only`.
- Inclusi entrambi i nomi nel report automatico di copertura.
- Nessun URL è stato aggiunto alla playlist di produzione, alla allowlist di pubblicazione o al Worker.

## Stato
Candidato HLS concreto, separato dagli endpoint Mediaset già falliti. Non ancora testato dalla rete italiana né attivato in Nuvio. La prossima verifica deve distinguere risposta HTTP, manifest HLS, segmenti audio/video, geografia e autorizzazione; un semplice HTTP 200 non basta.

## Esito del test tecnico automatico (26 novembre 2026, 16:46 UTC)

GitHub Actions run #45861841423:
https://github.com/annalisazotti11/tv-italia-puglia/actions/runs/45861841423

- Manifest principale: HTTP 200, `application/x-mpegURL`.
- Tipo: master HLS.
- Risoluzione dichiarata dalla variante migliore: 1080p.
- Playlist variante: HTTP 200.
- Segmento media: HTTP 200, campione di 4.096 byte, MIME `video/MP2T`.
- Host manifest, variante e segmento: `n-5-1.eu.cdn-redge.media`.
- Il flusso ha quindi superato il controllo tecnico di raggiungibilità dal runner GitHub.

Limiti non superati:
- Il runner non si trova sulla rete domestica italiana dell'utente: la riproduzione in Italia resta da verificare.
- Il controllo non verifica diritti di ritrasmissione o autorizzazione all'inserimento in una playlist di terzi.
- Nessun contenuto è stato salvato; il parametro firmato presente nella variante HLS è usato solo in memoria e non viene registrato.
- Nessuna modifica alla playlist pubblica, al Worker o alla configurazione di produzione Nuvio.

**Stato aggiornato:** HLS 1080p tecnicamente raggiungibile e con segmento video leggibile da GitHub Actions; test di riproduzione dalla rete italiana e autorizzazione ancora pendenti.

## Conferma VLC dalla connessione italiana (26 novembre 2026)

L'utente ha confermato che il flusso si riproduce in VLC dalla propria connessione italiana. La raggiungibilità e la riproduzione su PC sono quindi confermate per questo test, oltre alla verifica tecnica automatica del manifest HLS e di un segmento video.

La pagina ufficiale di GO Malta elenca Canale 5 HD al canale 125 nella propria offerta TV: https://www.go.com.mt/tv-channel-list/ . Redge si descrive come piattaforma OTT/CDN per operatori e titolari dei contenuti: https://r.dcs.redcdn.pl/file/o2/redge/brochure/Redge%20Media%20SECURITY.pdf . Questi elementi indicano un contesto distributivo professionale, ma non provano che questo specifico URL sia autorizzato alla ridistribuzione in una playlist indipendente o in un addon pubblico.

## Stato aggiornato

- HLS 1080p e segmento MPEG-TS: test tecnico automatico superato.
- Riproduzione VLC sulla connessione italiana dell'utente: confermata dall'utente.
- Fire TV/Nuvio: non ancora verificati.
- Autorizzazione alla redistribuzione nell'addon pubblico: non dimostrata.
- Il candidato resta fuori dalla playlist di produzione e dal Worker pubblico finché non è chiarito il diritto di utilizzo/ridistribuzione.

## Conferma VLC e verifica dei diritti (26 novembre 2026)

L'utente ha confermato che l'endpoint Redge si riproduce in VLC dalla propria connessione italiana. Questo prova la raggiungibilità e la riproduzione in VLC nel momento del test; non prova che il titolare del flusso ne autorizzi l'inserimento in un addon pubblico.

### Distinzione sul provider
La presenza di Canale 5 HD nel catalogo ufficiale GO Malta (canale 125) non dimostra, da sola, che l'endpoint Redge trovato in iptv-org sia un endpoint GO né che sia autorizzato alla redistribuzione. Le playlist pubbliche che riportano lo stesso URL sono indici di terze parti, non licenze.

### GO TV: percorso ufficiale alternativo
La documentazione GO indica il supporto dell'app ufficiale su Fire TV e l'accesso browser su `https://gotv.go.com.mt/`. GO elenca Canale 5 HD al canale 125. Le condizioni GO TV standalone OTT aggiornate a marzo 2026:
- limitano il servizio all'uso personale e non commerciale;
- consentono l'uso fuori Malta negli altri Paesi UE solo su base temporanea;
- vietano copia, registrazione, ritrasmissione e redistribuzione dei contenuti;
- prevedono requisiti di idoneità/residenza a Malta per la sottoscrizione.

Fonti ufficiali:
- https://www.go.com.mt/go-tv-app-device/
- https://www.go.com.mt/tv-channel-list/
- https://www.go.com.mt/support/will-i-be-able-to-use-the-go-tv-app-when-travelling/
- https://prodcms.go.com.mt/wp-content/uploads/2026/03/TV_Standalone_OTT_0_TC.pdf

### Decisione tecnica
- Non aggiungere l'URL Redge alla playlist di produzione, alla allowlist di pubblicazione o al Worker pubblico senza conferma scritta del titolare dei diritti.
- La versione sorgente Worker 4.9.4 aggiunge, come alternativa esterna e non come stream, il player ufficiale GO TV (`https://gotv.go.com.mt/`) accanto a Mediaset Infinity. Il link GO TV richiede un abbonamento e credenziali GO idonei.
- L'app GO TV ufficiale è compatibile con Fire TV; ciò non significa che l'app sia integrata dentro Nuvio.
- La 4.9.4 è stata aggiornata nel repository ma non è ancora deployata su Cloudflare. La 4.9.3 resta la versione precedentemente pubblicata.

## Integrazione diretta nel codice addon (4.9.5)

Su richiesta dell'utente, la M3U8 è stata inserita come sorgente diretta hardcoded nel Worker 4.9.5:
`https://n-5-1.eu.cdn-redge.media/livehls/oeu/mt/live/canale_5/live.livx/playlist.m3u8`

- Nuvio riceve il campo `url` HLS diretto; non è un collegamento browser `externalUrl`.
- La riproduzione VLC sulla connessione italiana è stata confermata dall'utente il 26/11/2026.
- Restano disponibili i fallback esterni ufficiali Mediaset Infinity e GO TV Malta.
- La sorgente è community/non ufficiale; la licenza di redistribuzione non è stata accertata.
- La sorgente non è aggiunta alla allowlist di identità e non viene marcata come ufficialmente autorizzata.
- Worker 4.9.5 nel repository; deployment Cloudflare non eseguito.
