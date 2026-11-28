# TV Italia Complete

Modulo indipendente nello stesso repository TV Italia + Puglia. Non modifica il Worker 5.1.2, il suo manifest, gli audit o il file Wrangler principale. Nessun controllo audio/video, nessun FFmpeg, nessun accesso ai singoli stream durante l'aggregazione.

## Attivazione Cloudflare

1. Crea un Worker separato `tv-italia-complete` in Workers & Pages e pubblica il contenuto di `complete/worker.mjs` come modulo ES.
2. Crea un namespace KV dedicato e collegalo al Worker come binding `PLAYLISTS`.
3. Aggiungi il secret `ACCESS_TOKEN` con almeno 32 caratteri casuali alfanumerici.
4. Aggiungi il secret `PLAYLIST_SOURCES` come array JSON di oggetti {"name":"Nome lista","url":"https://.../playlist.m3u"}. Inserisci solo le playlist per le quali disponi dei diritti di accesso e utilizzo. Non pubblicare credenziali o playlist private nel repository pubblico. Il formato supportato è M3U; gli indici Markdown non sono direttamente supportati in questo modulo.
5. Aggiungi cron trigger `*/12 * * * *` (cinque gruppi, ciascuna lista ogni ora). Scarica soltanto i file delle playlist, conserva la copia precedente in caso di errore e rimuove i duplicati esatti.
6. Apri `https://DOMINIO/TOKEN/status.json` per inizializzare. In Nuvio aggiungi `https://DOMINIO/TOKEN/manifest.json`. La lista unificata è disponibile su `https://DOMINIO/TOKEN/italia-completa.m3u`.

Le fonti sono configurabili senza modificare codice. Nessuna sorgente non approvata viene importata di default. Il catalogo raggruppa per nome normalizzato; può mantenere alias come voci separate. Non garantisce disponibilità, identità o qualità delle trasmissioni. Il modulo non effettua proxy, non aggira DRM né restrizioni geografiche; opzioni specifiche dei player possono non funzionare nel catalogo addon. Non condividere il manifest con il token.

Stato: codice nel repository, deployment e configurazione Cloudflare da completare. Il progetto di produzione rimane invariato.

## Deployment automatico con GitHub Actions

Il workflow [deploy-complete.yml](../.github/workflows/deploy-complete.yml) riutilizza i secret esistenti `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID` (o la variable per l'ID). Il token deve avere i permessi Workers Scripts Edit e Workers KV Storage Edit per l'account.

Nelle impostazioni del repository, Actions secrets, aggiungi:
- `TV_COMPLETE_ACCESS_TOKEN`: token personale casuale di almeno 32 caratteri (solo lettere, numeri, trattino, underscore).
- `TV_COMPLETE_PLAYLIST_SOURCES`: array JSON con le playlist che hai diritto di utilizzare, massimo 100. Nessuna credenziale nel codice o nei log.

Esempio di struttura (sostituisci con gli URL autorizzati):
```json
[{"name":"Lista 1","url":"https://example.com/authorized.m3u"}]
```

Avvia manualmente il workflow **TV Italia Complete - deploy separato** dalla scheda Actions dopo aver aggiunto i secret. Il workflow crea o riutilizza il namespace KV dedicato, genera una configurazione Wrangler temporanea, installa i secret direttamente su Cloudflare e attiva il cron a intervalli di 12 minuti, per cinque gruppi da massimo 20 liste. Non contatta gli stream durante il deploy. Non cambia il Worker tv-italia-puglia. Il trigger su push può fallire prima che i secret siano configurati; non significa che la produzione esistente abbia un problema. Il link di installazione è disponibile solo dopo il deployment riuscito: usa il dominio del nuovo Worker, il token personale e /manifest.json. Non condividere tale link.

## Versione 1.6.1

TGR Puglia, Rai 1–Canale 5, locali pugliesi e poi restanti canali per ascolto medio mensile Auditel; dati mancanti in fondo, non esclusi. Il numero LCN resta distinto dalla posizione del catalogo. Aggregazione con alias e metadati, indice URL per gruppo e cache breve. Loghi originali PNG centrati, senza alterare le proporzioni. Lo status privato riporta conteggi effettivi, errori, nomi unificati, conflitti e loghi mancanti. Le nuove raccolte della ricerca cumulativa sono candidate da verificare prima dell'importazione. La disponibilità del file M3U non certifica i diritti, il funzionamento del flusso o l'attualità. Il nuovo storico distingue cambiamenti osservati nel contenuto da date di modifica dichiarate. Nessun nuovo filtro dei canali, nessun test video. Il deployment effettivo va confermato in Actions.
