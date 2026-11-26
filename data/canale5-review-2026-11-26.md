# Canale 5 — verifica candidati 26 novembre 2026

Revisione di sola metadatazione, senza riproduzione dei flussi e senza modifica della produzione.

- Quattro host già nell'allowlist di revisione per tvip_5_canale-5-hd: live03-col, live02-seg, Akamai live2 e Akamai live3. Il pilota precedente ha restituito due 403 e due manifest indisponibili.
- Due varianti non presenti nell'elenco di revisione: live02-col e CDN live2. Segnalate da liste terze, senza prova di autorizzazione per player esterni né identità verificata. Non attivare.
- Ulteriore operatore individuato: net+ Svizzera; servizio in abbonamento con limiti di diffusione, non candidato alla pubblicazione in Italia.
- Public IPTV riporta un controllo fallito per live02-seg; non costituisce una verifica locale.
- Mediaset Infinity resta il fallback ufficiale. Nessuna sorgente nuova confermata; nessuna modifica ad allowlist, quarantena, Worker o catalogo.

Fonti: https://github.com/domenicomarfe-crypto/CANALI-IPTV/blob/main/IPTV.ITALIA.json.m3u ; https://www.emanueledemaria.com/tv/ ; https://publiciptv.com/channels/canale5it ; https://www.netplus.ch/fr/academie/trucs-astuces/support-television/ ; https://help.mediasetinfinity.mediaset.it/hc/it/articles/4402322887953-Mediaset-Infinity-all-estero ; data/source-identity-review.json ; data/source-identity-audit.md.
