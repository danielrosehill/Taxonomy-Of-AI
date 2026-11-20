---
title: Taxonomy of AI Annotator
emoji: 🎙️
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

Private review Space for [Taxonomy of AI](https://github.com/danielrosehill/Taxonomy-Of-AI) (`space/`). Go through a
task's models one by one, sorted by trending, downloads (30 days / all time), likes or newest (live Hub stats, fetched
at startup), and either record a spoken note (`r`) or mark the model reviewed with no note (`n`). A note is
transcribed and turned into structured fields in one OpenRouter call (Gemini Flash), and stored with its audio in the
private dataset `danielrosehill/Taxonomy-Of-AI-Voice-Notes` (`reviews/`, `audio/`, `transcripts/`).

Secrets: `HF_TOKEN` (read `Taxonomy-Of-AI-Working`, write `Taxonomy-Of-AI-Voice-Notes`), `OPENROUTER_API_KEY`.
Optional variable `NOTE_MODEL` (default `~google/gemini-flash-latest`).
