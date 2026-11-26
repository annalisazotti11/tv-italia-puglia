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
