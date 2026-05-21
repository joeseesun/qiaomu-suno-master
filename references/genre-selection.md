# Genre Selection

This skill includes a compact copy of `joeseesun/music-genre-finder` under
`references/genre-finder/`. The database is based on RateYourMusic genre pages
and contains thousands of main genres, subgenres, and deeper branches.

Use genre selection when:

- the user asks for style recommendations before writing a song
- the user gives only a mood or scene, such as "深夜空灵" or "有活力"
- the requested style is broad, such as "rock", "world music", or "electronic"
- Suno tags would benefit from more precise subgenre choices

Preferred workflow:

1. Run `scripts/find_music_genres.py "<brief or mood>" --limit 5`.
2. Pick 1-3 genre tags that match the user's intent.
3. Add 2-5 performance tags for vocal, instruments, tempo, and mood.
4. Keep `style_description` concise. Suno works better with focused tags than a
   long genre dump.

Examples:

```bash
scripts/find_music_genres.py "深夜 空灵 梦幻" --limit 5
scripts/find_music_genres.py "raw energetic punk" --limit 5
scripts/find_music_genres.py "世界音乐 鼓 长笛 电影感" --limit 6
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

Use the database as a palette, not as the whole arrangement.
