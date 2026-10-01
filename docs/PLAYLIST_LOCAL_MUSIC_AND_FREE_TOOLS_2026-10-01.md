# Playlist music source audit — 2026-10-01 KST

## Owner decision and local source

The owner confirmed that all music in `OneDrive/Desktop/음악원본` was downloaded
under a paid Suno plan and may be used. This supersedes the 2026-09-07
fresh-Lyria-only rule for the owner's desktop originals. Retain the requirement
for genre fit, no duplicate recording within a mix, shuffled order, variable
total runtime, and a distinctive thumbnail. New compositions can also be
added after the export, usage rights, channel fit, and file identity are
recorded. Do not infer licensing from an MP3 tag alone.

Read-only inventory at 03:26 KST: 692 root-level audio files (691 MP3, one
WAV), of which 633 carry a Suno creation tag and 59 have no source tag. None
has an ID3 genre tag. Durations range from 23 to 479 seconds. 483 filenames
have a numbered or duplicate-looking suffix; that is not proof of unique
audio. The repository's previously reviewed 20-track romantic set totals
60.4 minutes, but only five desktop files matched any of its SHA-256 values.
Accordingly, the old Drive manifest cannot simply be relabeled as this local
library. A channel-specific catalog needs content/genre review and audio-hash
deduplication before automatic selection or transfer to the VPS.

The production `scripts/youtube_playlist_maker.py` still defaults to an
approved Drive bank and intentionally raises `WAITING_FRESH_COMPOSITIONS` for
`globalmusic` and `kpop`. A new opt-in `PLAYLIST_MUSIC_SOURCE=owner_local`
path now reads a private, reviewed manifest and staged audio. It validates
the channel's genre, owner's paid-plan or independently verified export
rights, exact SHA-256, duration and distinct recordings, then shuffles the
selection and targets 50–70 minutes. Romantic mixes keep equal French and
Japanese track counts. It writes a track manifest in
the video work directory. Missing or changed assets stop before rendering.
This path was activated on 2026-10-01 after the private catalog, selection and
staging checks completed. The desktop folder contains non-audio files,
including credential-like
JSON names; transfer only approved audio by an explicit allowlist. Do not
upload or commit the directory wholesale.

Activation receipt: 692 source audio files were inventoried, 492 distinct
audio hashes and 107 distinct Suno song IDs were observed, and 36 reviewed
tracks were staged. The Globalmusic pool is 20 tracks / 65.68 minutes with
exactly ten French and ten Japanese tracks. The K-pop pool is 16 tracks /
61.47 minutes. Production re-hashes every staged file before selection, uses
no duplicate hash inside a mix, and keeps the private filenames and manifest
outside Git. Four separate 1672x941 channel-specific source images were added
for Globalmusic, K-pop, Starbucks and MBB. Healing remains on its existing
nature-sound/image path and is not part of this recovery batch.

Private manifest format: `{"version":1,"tracks":[{"channel":"globalmusic",
"file":"song.mp3","sha256":"<64 hex>","approved":true,
"genre":"romantic_acoustic","language":"french",
"rights":"owner_paid_suno"}]}`. `kpop` requires genre
`korean_acoustic_pop`; `starbucks` requires `instrumental_cafe`. The
manifest must not be committed with local filenames or rights evidence.
`healing` retains its nature-sound pipeline and `mbb` its approved classical
recordings; neither silently selects Suno tracks by title.

## Suno cafe-instrumental batch created on 2026-10-01

Twelve new V6 instrumentals were created in the owner's paid Suno workspace for
the Starbucks playlist channel. They used an empty lyrics field and explicit
instrumental/no-vocal prompts:

- Midnight Cafe Window: `9f8a7d8a-ac33-4bc3-83a1-c86501e54c65`, `2351e16b-51b2-430a-a4ac-269a402ffc92`
- Morning Bossa Table: `2a48b4f8-03e8-42e9-9e1a-5e3c594dbb40`, `0d761339-55e8-402d-b3a0-738eeab7d4ce`
- Rainy Afternoon Piano: `b2afe38b-8b07-4654-bc14-aecd81b5ff9e`, `42fdf7d9-e2ec-4af5-a926-25486c6a53ca`
- Vibraphone Coffee Break: `8c1b0944-ba22-4bde-a005-e476e9675770`, `e7dc9401-b5fe-45c7-97e6-8e0a47f46b0e`
- Quiet Lobby Keys: `71ec2efb-489a-4ef4-9eed-e272c47afb30`, `3598089c-6c07-403f-94d2-809c7b69a5d9`
- Golden Hour Cafe Guitar: `06b30fed-b12c-4575-ad4e-30ae5bbedd61`, `16398899-456f-4b23-919d-a45ff3c82c9d`

Suno then displayed `Out of Downloads`, zero downloads remaining, and a
2026-10-05 refresh date. None of these twelve tracks has been copied to the VPS
or used in a YouTube upload. The Starbucks worker now fails closed instead of
falling back to the unreviewed mixed-vocal Drive bank.

## Current free composition options

| Service | Current free route | Fit for this long-form pipeline |
|---|---|---|
| Gemini app Lyria 3.5 | Google says available to all users, with short and longer track choices. | Manual app export can be reviewed; the Gemini **API** Lyria 3.5 has no free tier, so it is not an unattended free fallback. |
| Google ProducerAI | Google says free and paid subscriptions are available. | Promising manual composition option; verify the account's export and commercial terms for each new track before staging. |
| ElevenMusic v2.5 | Vendor announced five free lossless downloads daily with commercial use if ElevenMusic is credited. | Test an exported track and retain plan/rights evidence and required credit. Its published pricing/terms pages are not fully synchronized, so verify the actual account entitlement first. |
| Suno Free | Free downloads are personal, non-commercial under current vendor help. | Do not use future free-plan tracks for a monetized channel; the owner's existing paid-plan downloads are a separate, approved source. |
| Udio Free | Free generation credits exist, but Udio says audio/video/stem downloads are disabled. | No file for this long-form production path. |
| YouTube Dream Track | Generates soundtracks inside Shorts; generated soundtrack cannot be downloaded. | Useful for Shorts only, not a playlist MP3 source. |
| Grok Imagine | Official xAI documentation describes image/video creation with generated scene audio. | No verified standalone downloadable song generator for this workflow. |

Sources checked 2026-10-01: Google Lyria 3.5 announcement
https://blog.google/innovation-and-ai/products/gemini-app/better-tracks-lyria-gemini/ ;
Google API pricing https://ai.google.dev/gemini-api/docs/pricing ;
ProducerAI https://blog.google/innovation-and-ai/models-and-research/google-labs/producerai/ ;
ElevenMusic https://elevenlabs.io/blog/music-v2-5-model and
https://elevenlabs.io/eleven-music-model-specific-terms ;
Suno https://help.suno.com/en/articles/13926401 ;
Udio https://help.udio.com/en/articles/12683565-changes-associated-with-the-universal-music-group-umg-partnership ;
YouTube https://support.google.com/youtube/answer/14151606 ;
xAI https://docs.x.ai/grok/overview .

## Next production steps

1. Build a SHA-256 catalog of the desktop audio only, with duration, source,
   owner-paid-rights attestation, listening-reviewed genre/mood/vocal language,
   and whether a file has appeared in a prior public playlist.
2. Create each mix from its reviewed channel pool with a unique daily seed,
   no repeated audio hash, shuffled sequence, and a target runtime varied
   within the channel's approved range. Preserve a track-by-track manifest.
3. Stage only selected audio on the VPS. Keep new AI compositions as a separate
   addition with service, export date, rights and attribution recorded.
4. Prepare a fresh channel-specific 16:9 source image, review the 1280x720
   thumbnail at phone size for one clear focal subject and readable short text,
   then render and verify exact channel/public video receipts. The thumbnail
   must not be a generic copy or obscure its subject.

The later execution batch publishes only after separate channel identity and
public receipt verification; creation or inventory alone is not a publication
receipt.
