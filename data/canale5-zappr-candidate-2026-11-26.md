# Canale 5 — nuova pista Zappr/Netplus (26 novembre 2026)

## Candidato individuato
La playlist community iptv-ch pubblica un endpoint HLS etichettato Canale 5 HD 720p:
https://netplus.zappr.stream/canale5.m3u8
Fonte: https://github.com/iptv-ch/iptv-ch.github.io/blob/master/netplus-zappr.m3u8
La stessa playlist include altri canali Mediaset/italiani sul medesimo host. Aria TV lo etichetta "stable", ma è un'affermazione della comunità e non una prova indipendente di disponibilità in Italia.

## Distinzione fondamentale
- Il dominio ufficiale dell'operatore è netplus.ch; zappr.stream è un dominio distinto di terza parte.
- Non è stata trovata una dichiarazione pubblica che autorizzi Zappr a ridistribuire Canale 5 in un player esterno.
- Il flusso non è stato verificato tecnicamente né per autenticità, né per riproduzione in Italia.
- Non inserirlo nel catalogo di produzione e non dichiararlo funzionante.

## Azione sul repository
La playlist "Swiss Netplus Zappr" in data/playlist-sources.json è stata spostata da scope "fta" a "index_only". Rimane disponibile per individuare metadati, ma non può promuovere automaticamente URL nel catalogo.

## Contesto provider
Melita Malta elenca ufficialmente Canale 5 HD (canale 154) e NexTV App, ma l'app è riservata ai clienti Melita con NexTV box/Flexi Bundle; non è una M3U pubblica.
Fonti:
- https://www.melita.com/tv-channels/canale-5-hd/
- https://www.melita.com/help/television/nextv-app/downloading-and-accessing-the-app/can-i-buy-the-melita-nextv-everywhere-service/
Zattoo Switzerland elenca Canale 5 HD, ma fuori dalla Svizzera non consente live TV; solo registrazioni.
Fonte: https://support.zattoo.com/hc/en-us/articles/39380958496274-Using-Zattoo-at-home-and-abroad

## Stato
Nessuna nuova sorgente M3U autorizzata e utilizzabile in Italia confermata. Worker e catalogo di produzione invariati.
