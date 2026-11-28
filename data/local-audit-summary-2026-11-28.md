# Rapporto diagnostico locale — 28 novembre 2026

Rapporto utente `rapporto-locale-20261128-092042.json`, timestamp dichiarato 09:20:42 UTC; snapshot server 09:17:52 UTC. Nessun URL o dato di rete personale copiato.

- 95 rotte testate su 45 canali; 41 rotte con pacchetti audio/video su 28 canali.
- 13 riserve tecniche positive oltre alle 28 prime scelte.
- Esiti negativi: 44 probe_failed, 4 not_found, 3 access_denied_403, 2 timeout, 1 missing_av_packets.
- Migliore risoluzione per canale: 1 a 2160p, 17 a 1080p, 9 a 720p, 1 a 234p.
- Identità visiva non verificata dal programma; le misurazioni non attestano autorizzazione alla distribuzione. Le rotte sono identificate da numeri progressivi, non da hash o revisione del registro. Non importare questi numeri automaticamente in produzione.
- La conferma manuale Rai 1 è registrata separatamente.

## Graduatoria tecnica

Ordine di scelta: risoluzione decrescente, successo al primo tentativo, tempo FFprobe crescente. Il tempo FFprobe non è il tempo al primo fotogramma. Antenna Sud ha richiesto due tentativi.

| Canale | Altezza | FFprobe ms | Rotta nel rapporto | Rotte A/V positive |
|---|---:|---:|---:|---:|
| Rai 1 HD | 720 | 983 | 1 | 1 |
| Rai 2 HD | 720 | 957 | 1 | 1 |
| Rai 3 HD | 720 | 947 | 1 | 1 |
| Rete 4 HD | 1080 | 3312 | 2 | 4 |
| Canale 5 HD | 1080 | 3393 | 1 | 2 |
| Italia 1 HD | 1080 | 3256 | 1 | 2 |
| Rai 4K (HbbTV) | 2160 | 1613 | 1 | 1 |
| Rai 4 | 720 | 818 | 1 | 1 |
| Rai 5 | 720 | 1369 | 1 | 1 |
| Rai Movie | 720 | 1340 | 1 | 1 |
| Rai Storia | 720 | 760 | 1 | 1 |
| 20 Mediaset HD | 1080 | 3709 | 1 | 1 |
| Iris | 1080 | 2610 | 2 | 2 |
| 27 Twentyseven | 1080 | 3215 | 2 | 2 |
| La5 | 1080 | 3356 | 2 | 2 |
| Cine34 | 1080 | 2390 | 2 | 3 |
| Focus | 1080 | 3302 | 1 | 2 |
| Top Crime | 1080 | 3030 | 1 | 2 |
| Boing | 1080 | 2982 | 1 | 1 |
| Cartoonito | 1080 | 2873 | 1 | 1 |
| Italia 2 | 1080 | 3381 | 1 | 2 |
| Mediaset Extra | 1080 | 3304 | 1 | 1 |
| Radionorba TV | 1080 | 1825 | 1 | 1 |
| Antenna Sud | 1080 | 7546 | 1 | 1 |
| Studio 100 | 1080 | 1008 | 1 | 1 |
| Tele Foggia | 720 | 1327 | 1 | 1 |
| TeleMajg | 720 | 1253 | 1 | 1 |
| TV2000 | 234 | 1597 | 1 | 1 |

## Nessun successo A/V locale

Rai 3 TGR Puglia, Byoblu, Warner TV, K2, Frisbee, TGCOM24, Sportitalia, Donna TV, Supertennis, ALMA TV, RTV San Marino, Radio TV Serie A con RDS, La Nuova TV, Telenorba, Tele Sud Puglia, Sky News, TRM h24.

Questo documento non modifica il Worker o la lista delle fonti pubblicabili.
