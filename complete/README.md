# TV Italia Complete

Modulo indipendente nello stesso repository TV Italia + Puglia. Non modifica il Worker 5.1.2, il suo manifest, gli audit o il file Wrangler principale. Nessun controllo audio/video, nessun FFmpeg, nessun accesso ai singoli stream durante l'aggregazione.

## Attivazione Cloudflare

1. Crea un Worker separato `tv-italia-complete` in Workers & Pages e pubblica il contenuto di `complete/worker.mjs` come modulo ES.
2. Crea un namespace KV dedicato e collegalo al Worker come binding `PLAYLISTS`.
3. Aggiungi il secret `ACCESS_TOKEN` con almeno 32 caratteri casuali alfanumerici.
4. Aggiungi il secret `PLAYLIST_SOURCES` come array JSON di oggetti {"name":"Nome lista","url":"https://.../playlist.m3u"}. Inserisci solo le playlist per le quali disponi dei diritti di accesso e utilizzo. Non pubblicare credenziali o playlist private nel repository pubblico. Il formato supportato è M3U; gli indici Markdown non sono direttamente supportati in questo modulo.
5. Aggiungi cron trigger `17 * * * *`. Scarica soltanto i file delle playlist, conserva la copia precedente in caso di errore e rimuove i duplicati esatti.
6. Apri `https://DOMINIO/TOKEN/status.json` per inizializzare. In Nuvio aggiungi `https://DOMINIO/TOKEN/manifest.json`. La lista unificata è disponibile su `https://DOMINIO/TOKEN/italia-completa.m3u`.

Le fonti sono configurabili senza modificare codice. Nessuna sorgente non approvata viene importata di default. Il catalogo raggruppa per nome normalizzato; può mantenere alias come voci separate. Non garantisce disponibilità, identità o qualità delle trasmissioni. Il modulo non effettua proxy, non aggira DRM né restrizioni geografiche; opzioni specifiche dei player possono non funzionare nel catalogo addon. Non condividere il manifest con il token.

Stato: codice nel repository, deployment e configurazione Cloudflare da completare. Il progetto di produzione rimane invariato.
