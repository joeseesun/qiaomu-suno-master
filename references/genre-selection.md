# Genre Selection

This skill includes a compact copy of `joeseesun/music-genre-finder` under
`references/genre-finder/`. The database is based on RateYourMusic genre pages
and contains thousands of main genres, subgenres, and deeper branches.

Use genre selection when:

- the user asks for style recommendations before writing a song
- the user asks only for Suno style tags or unusual genre combinations
- the user gives only a mood or scene, such as "深夜空灵" or "有活力"
- the requested style is broad, such as "rock", "world music", or "electronic"
- Suno tags would benefit from more precise subgenre choices

Style discovery workflow:

1. Extract the user's axes: core genre, adjacent genre family, era/scene,
   rhythm, texture, vocal color, and mood.
2. Run the finder on the original phrase first:

```bash
scripts/find_music_genres.py "<user phrase>" --limit 8
```

3. For style-only requests, broad briefs, or "give me combinations" requests,
   run at least two more focused probes. Useful probe shapes:
   - core family plus adjacent family, such as `post-punk new-wave dream-pop`
   - texture or production, such as `minimal synth coldwave drum machine`
   - rhythm or energy, such as `dance-punk motorik driving bass`
   - contrast or surprise, such as `ethereal wave no wave art punk`
4. Deduplicate the results into a palette of 6-12 plausible database-backed
   genre tags. Prefer tags that appeared in the output; use parent/child genre
   relationships only when they are obvious from the result descriptions.
5. Build each Suno style string from 1-3 genre tags plus 2-5 performance,
   production, tempo, vocal, or mood tags.
6. Keep `style_description` concise. Suno works better with focused tags than a
   long genre dump.
7. When presenting style-only recommendations, include a short "palette used"
   line or otherwise make clear which finder-backed genres informed the output.
   If the finder failed, say so and mark the answer as best-effort.

Examples:

```bash
scripts/find_music_genres.py "深夜 空灵 梦幻" --limit 5
scripts/find_music_genres.py "raw energetic punk" --limit 5
scripts/find_music_genres.py "世界音乐 鼓 长笛 电影感" --limit 6
scripts/find_music_genres.py "art punk proto post-punk new wave dream pop" --limit 8
scripts/find_music_genres.py "minimal wave coldwave synth punk drum machine" --limit 8
scripts/find_music_genres.py "dance-punk krautrock motorik hypnotic bass" --limit 8
```

Good Suno tag shape:

```text
punk-rock, garage-punk, raw-male-vocals, distorted-guitars, fast-tempo, anthemic
```

```text
afrobeat, highlife, duet-vocals, hand-drums, flute, mid-tempo, euphoric
```

Avoid overloading:

```text
rock, punk, garage punk, hardcore punk, pop punk, post-punk, new wave, metal,
alternative rock, indie rock, noise rock, grunge, hard rock, classic rock
```

For style-only answers, prefer a response shape like:

```text
Palette used: post-punk, minimal-wave, coldwave, synth-punk, dance-punk,
ethereal-wave, dream-pop, krautrock

Best starters:
1. minimal-wave, coldwave, post-punk, drum-machine, sparse-arrangement, cold-female-vocals, nocturnal
2. krautrock, post-punk, minimal-wave, motorik-drums, hypnotic-bass, synth-textures, night-drive

exclude_styles: trap, metal, country, reggae, smooth-jazz
```

Use the database as a palette, not as the whole arrangement.
