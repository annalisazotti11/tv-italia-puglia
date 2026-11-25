# Verifica associazioni dei canali — 25 novembre 2026

La scansione ha esaminato i metadati di tutte le 219 voci del database. Non è stato riprodotto il video delle fonti sospette: un manifest valido o la presenza di pacchetti video/audio non provano che il flusso corrisponda al canale.

La versione attiva accertata del Worker `tv` è **3.7.6**. Il suo endpoint Canale 5 restituisce la sorgente originale Mediaset, non quella IPTV Mate presente nello snapshot. Non è quindi possibile attribuire con certezza l'episodio al Worker: verificare anche TvVoo e cache Nuvio. La versione 4.3.0 richiede pubblicazione esplicita sulla stessa istanza Cloudflare.

## Intervento mirato

- 42 voci in 26 canali rimosse dalle liste verificate, regionali o candidate.
- Canale 5: solo indirizzi specifici Mediaset approvati; in assenza di controllo positivo non viene servito, e un redirect viene rifiutato.
- Esclusione di tutte le voci di un aggregatore opaco e delle associazioni palesemente ambigue (regioni, paesi, duplicati o emittenti omonime).
- Rai 3 TGR Puglia preservato. Gli altri canali rimangono invariati, compreso il catalogo con 219 voci monitorate.
- La quarantena è applicata nello scanner notturno e nel Worker nuovo.

| Canale | Voci rimosse | Fonti tecnicamente verificate rimaste |
|---|---:|---:|
| Rai 1 HD | 1 | 3 |
| Rai Movie | 1 | 0 |
| Gambero Rosso | 1 | 1 |
| Cielo | 1 | 1 |
| Rai 2 HD | 1 | 2 |
| Real Time | 1 | 2 |
| QVC | 6 | 1 |
| Focus | 1 | 0 |
| Giallo | 1 | 2 |
| Top Crime | 1 | 0 |
| Rai 3 HD | 5 | 3 |
| Hell's Kitchen Italy | 1 | 4 |
| K2 | 1 | 0 |
| Rete 4 HD | 1 | 1 |
| DMAX | 1 | 2 |
| Italiana | 3 | 0 |
| Discovery Turbo | 1 | 1 |
| Canale 5 HD | 6 | 0 |
| CLUB TV | 1 | 0 |
| Italia 1 HD | 1 | 1 |
| LA7 HD | 1 | 5 |
| Sky News | 1 | 1 |
| Boomerang | 1 | 0 |
| Cartoon Network | 1 | 0 |
| Sky Uno | 1 | 0 |
| Sky Uno + | 1 | 0 |

## Revisione più restrittiva (non attiva)

Il file `data/source-identity-review.json` contiene 91 canali con 150 indirizzi selezionati mediante controllo statico di host e percorso o lista curata. Non è una certificazione di origine né un nuovo test di riproduzione. Attivare un'allowlist esclusiva può ridurre sensibilmente il catalogo: richiede verifica del titolare e nuove prove positive prima del deployment.

Per le dirette a pagamento e non autorizzate, utilizzare soltanto i servizi e le applicazioni ufficiali. Non aggirare DRM o restrizioni di accesso.

## Deploy effettivo — 25 novembre 2026

- Worker principale `tv-italia-puglia`: **4.9.2** (dal 4.9.1, selezione singola, filtro quarantena ed esclusione URL ambigui tra ID), deployment Cloudflare `f620a2e0`.
- Worker storico `tv`: **3.7.7** (dal 3.7.6, stessa quarantena; Canale 5 delegato al solo risultato confermato del principale), deployment `6296a316`. KV e Cron lasciati invariati. [Patch legacy](../cloudflare/worker-tv-v3.7.7-quarantine.patch).
- Verifica live: entrambi i manifest riportano la nuova versione; entrambi gli endpoint Canale 5 restituiscono zero sorgenti. Il catalogo principale ha 219 canali monitorati e 93 mostrati, con Rai 3 TGR Puglia presente e un solo indirizzo restituito.
- Canale 5 resta nascosto fino a un controllo positivo audio/video di una fonte Mediaset ammessa; il Worker non segue redirect. Il test non certifica fotogrammi o contenuto di tutte le trasmissioni; TVVoo rimane un addon distinto.
- Test locali della 4.9.2 e della modifica legacy passati.
