# Canale 5 Redge — verifica autorizzazione e compatibilità (26 novembre 2026)

## Esito tecnico già acquisito
- L'utente conferma la riproduzione del candidato Redge in VLC dalla propria connessione italiana.
- GitHub Actions ha verificato il manifest HLS, una variante 1080p e un piccolo campione di segmento MPEG-TS.
- Questi test provano la raggiungibilità tecnica; non identificano il distributore contrattuale e non autorizzano la redistribuzione.

## Cosa risulta dalle fonti ufficiali GO
1. GO elenca **Canale 5 HD al canale 125**: https://www.go.com.mt/tv-channel-list/
2. La pagina ufficiale di configurazione dichiara che l'app GO TV è disponibile su **Fire TV** e che si accede con credenziali fornite da GO: https://www.go.com.mt/go-tv-app-device/
3. GO dichiara che il servizio può essere usato durante viaggi in Italia e in altri Paesi UE elencati: https://www.go.com.mt/support/will-i-be-able-to-use-the-go-tv-app-when-travelling/
4. Le condizioni GO TV Standalone OTT aggiornate a marzo 2026 dicono che il servizio è per uso personale/non commerciale, limitano l'uso fuori Malta a soggiorni temporanei negli altri Paesi UE e vietano copia, registrazione, rebroadcast e redistribuzione dei contenuti. I criteri di sottoscrizione possono richiedere la residenza a Malta:
   https://prodcms.go.com.mt/wp-content/uploads/2026/03/TV_Standalone_OTT_0_TC.pdf

## Cosa NON è dimostrato
Il fatto che GO distribuisca Canale 5 HD e che l'URL candidato utilizzi il dominio Redge non dimostra che quello specifico endpoint sia fornito da GO, né che sia autorizzato a essere pubblicato in un addon di terzi. La presenza in iptv-org, 91 Live o altre playlist comunitarie è un indizio di reperibilità, non una licenza.

## Decisione per TV Italia + Puglia
- Non pubblicare l'URL Redge in M3U, snapshot verificato, allowlist o Worker pubblico senza conferma scritta del titolare dei diritti.
- Mantenere il fallback Mediaset Infinity ufficiale.
- Preparare Worker 4.9.4 con un secondo collegamento `externalUrl` al player ufficiale GO TV (`https://gotv.go.com.mt/`), esplicitamente indicato come servizio con credenziali e abbonamento GO. È un collegamento al player ufficiale, non un relay dello stream.
- La GO TV app ufficiale è compatibile con Fire TV; la compatibilità è separata da Nuvio e non inserisce il canale nel catalogo Nuvio come flusso diretto.
- La 4.9.4 è solo nel repository fino a deployment esplicito su Cloudflare.

## Prossimo controllo pratico
Se l'utente possiede già un account GO TV valido registrato a Malta, provare l'app ufficiale su Fire TV durante il soggiorno in Italia. In assenza di un account idoneo, usare il fallback ufficiale Mediaset Infinity; non utilizzare account condivisi o endpoint terzi non autorizzati.

## Modifica codice addon 4.9.5

Su richiesta dell'utente, la M3U8 Redge è stata inserita direttamente nel codice del Worker 4.9.5 come stream HLS:
`https://n-5-1.eu.cdn-redge.media/livehls/oeu/mt/live/canale_5/live.livx/playlist.m3u8`

Nuvio riceve il campo `url` diretto, non `externalUrl`. La riproduzione VLC sulla connessione italiana è stata confermata dall'utente il 26/11/2026. I fallback Mediaset Infinity e GO TV Malta restano come scelte esterne ufficiali. La sorgente community non viene descritta come ufficiale e l'autorizzazione alla redistribuzione resta non accertata. Il Worker 4.9.5 è nel repository, ma non è stato distribuito su Cloudflare.
