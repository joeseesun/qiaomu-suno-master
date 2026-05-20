# Lyric Craft Reference

Adapted from the user's `joeseesun/suno-music-creator` workflow and the provided "Suno AI 歌词创作大师 Ultimate Pro" prompt, updated for the Rust `suno` CLI.

## Input Patterns

The user may provide:

- A simple theme: love, friendship, space exploration
- A detailed brief: style, emotion, story, scene, audience
- An article or story: extract the core narrative and emotional arc
- Keywords: transform into a coherent song concept
- Existing lyrics: polish into Suno-ready structure

## Required Creative Output

Always prepare:

- `lyrics`: complete lyrics with Suno section markers and real line breaks
- `style_description`: comma-separated style tags for Suno
- `exclude_styles`: comma-separated styles, instruments, and moods to avoid
- `title_options`: three creative, concise title candidates
- selected `title`: choose the strongest title for CLI generation

Optional when useful:

- `exclude`: styles to avoid
- `vocal`: `male` or `female`
- `model`: usually `v5.5`

## Output Contract For Prompt-Only Creation

When the user asks for lyrics/prompt text rather than immediate generation, output directly as Markdown code blocks with no extra explanation:

```lyrics
[Intro]

[Verse 1]
...

[Outro]
```

```style
alternative-rock, male-vocals, acoustic-guitar, fast-tempo, dreamy
```

```exclude
mainstream-pop, auto-tune, overly-happy
```

```titles
1. Title One
2. Title Two
3. Title Three
```

For generation requests, use the selected title, style description, exclude styles, and lyrics in the CLI.

## Commercial Hook Design

The hook is the most important part.

- Use an extremely memorable core phrase, roughly 8-16 syllables when possible.
- Make it simple, repeatable, emotionally resonant, and distinct.
- Mark it as `[Hook: Catchy]` or `[Hook: Anthemic]`.
- Make the hook appear early enough that the song has a clear identity.
- Avoid generic lines such as "I miss you tonight" unless transformed with specific imagery.
- Give the hook strong rhythm, rhyme, and emotional impact.
- Use contrast, paradox, a question, or a declaration when it makes the hook more magnetic.
- Design for the echo effect: the listener should keep repeating the phrase after hearing it.

## Professional Song Structure

Default pop structure:

```text
[Intro]

[Verse 1]
...

[Pre-Chorus]
...

[Chorus]
[Hook: Anthemic]
...

[Verse 2]
...

[Pre-Chorus]
...

[Chorus]
[Hook: Anthemic]
...

[Bridge]
...

[Chorus]
[Hook: Anthemic]
...

[Outro]
```

Other viable structures:

- Simplified: `Intro -> Verse -> Chorus -> Verse -> Chorus -> Bridge -> Chorus -> Outro`
- Extended: `Intro -> Verse 1 -> Pre-Chorus -> Chorus -> Post-Chorus -> Verse 2 -> Pre-Chorus -> Chorus -> Post-Chorus -> Bridge -> Breakdown -> Chorus -> Outro`
- Modern pop: `Intro -> Chorus -> Verse -> Chorus -> Post-Chorus -> Verse -> Chorus -> Post-Chorus -> Bridge -> Chorus -> Outro`

Rules:

- Keep `[Intro]` and `[Outro]` empty unless the user explicitly wants spoken or sung text there.
- Put every section marker on its own line.
- Keep lyrics concise enough for Suno; prefer focused scenes over sprawling narrative.
- Keep one primary language unless the user asks for bilingual lyrics.
- Use special sections when genre-appropriate: `[Drop]`, `[Interlude]`, `[Breakdown]`, `[Post-Chorus]`, `[Refrain]`, `[Spoken Word]`, or ad-libs in parentheses.

## Suno Markers

Structural:

- `[Intro]`
- `[Verse 1]`, `[Verse 2]`
- `[Pre-Chorus]`
- `[Chorus]`
- `[Post-Chorus]`
- `[Bridge]`
- `[Breakdown]`
- `[Interlude]`
- `[Drop]`
- `[Outro]`

Vocal:

- `[Male Vocals]`
- `[Female Vocals]`
- `[Duet]`
- `[Whispers]`
- `[Shouting]`
- `[Harmonies]`
- `[Falsetto]`
- `[Growl]`
- `[Rap]`

Emotion:

- `[Calm]`
- `[Energetic]`
- `[Emotional]`
- `[Aggressive]`
- `[Intense]`
- `[Melancholic]`
- `[Euphoric]`
- `[Nostalgic]`
- `[Dreamy]`

Sound effects:

- `[Applause]`
- `[Rain]`
- `[City Sounds]`
- `[Heartbeat]`
- `[Static]`
- `[Phone]`
- `[Crowd]`
- `[Nature]`
- `[Traffic]`

Instrument and arrangement:

- `[Heavy drums]`
- `[Piano solo]`
- `[Acoustic]`
- `[Synth Lead]`
- `[Distorted Guitars]`
- `[808]`
- `[Bass Drop]`
- `[Strings]`
- `[Brass]`

Recommended combined markers:

- `[Chorus: Anthemic]`
- `[Verse: Storytelling]`
- `[Bridge: Atmospheric]`
- `[Intro: Mysterious]`
- `[Outro: Fading]`
- `[Verse: Calm to Intense]`
- `[Verse: Whispered]`
- `[Chorus: Shouted]`
- `[Bridge: Piano Focus]`

Marker strategy:

- Use 1-2 main markers plus one modifier per section at most.
- Keep colon modifiers concise, such as `[Verse: Storytelling]`.
- Use emotional gradients and contrast only where they serve the song arc.
- Avoid over-marking; too many instructions can confuse Suno.

## Vocal Texture Techniques

Use sparingly:

- Backing vocals: `(Yeah!)`, `(Echoes)`, `(Whispers)`
- Call and response: `(Call: ...) (Response: ...)`
- Elongation: `lo-o-ong`, `cra-a-azy`, `he-e-ey`
- Emphasis: uppercase single words such as `STOP`, `NEVER`, `NOW`, `FEEL`
- Emotional direction: `(with passion)`, `(whispered)`, `(breaking voice)`
- Effects: `(Vocoder effect)`, `(Auto-tune)`, `(Distortion)`, `(Reverb)`
- Dynamics: `(building)`, `(fading)`, `(suddenly quiet)`
- Space: `(distant)`, `(close up)`, `(surrounding)`
- Use punctuation and line breaks to control pace, pause, and attack.

## Language Strategy

English:

- Balance syllables, stress, and natural rhyme.
- Prefer short, punchy words when rhythm matters.
- Avoid overly complex vocabulary and stiff syntax.
- Use homophones, double meanings, consonant texture, and vowel flow when useful.

Chinese:

- Balance line length, tone flow, and end-rhyme.
- Consider how tones affect melody.
- Avoid rare characters, unclear phrasing, and awkward consonant clusters.
- Use idiom, homophone, and compact imagery only when singable.

Multilingual:

- Use one primary language.
- Use the second language only for a section, hook accent, ad-lib, or contrast.
- Avoid line-by-line language alternation unless the user explicitly asks for it.
- Make bilingual sections conceptually continuous, not direct translations.

## Long Text To Song

For articles, stories, transcripts, or long notes:

- Identify the core theme and emotional premise.
- Track emotional changes from beginning to end.
- Select dramatic, concrete scenes as lyric material.
- Extract the strongest character voice or point of view.
- Simplify the narrative into a song-sized arc.
- Convert descriptive prose into image, metaphor, and action.
- Reorganize the source around song structure rather than source order.

## Emotional Engineering

- Design a clear emotional arc.
- Create tension and release between verse, pre-chorus, chorus, and bridge.
- Add resonance points that feel personally recognizable.
- Anchor key emotions to repeated words or phrases.
- Build expectation before the chorus or drop.
- Use contrast, such as vulnerable to powerful, intimate to expansive, quiet to explosive.
- Balance universal feeling with specific detail.
- Use memory-triggering images when relevant.

## Non-Mainstream Creative Techniques

- Open with an unusual image, action, or voice.
- Make the chorus distinctive, not merely generic repetition.
- Let the bridge become more experimental in lyric or musical gesture.
- Consider an open-ended or philosophical ending.
- Use internal rhyme, slant rhyme, or irregular rhyme for depth.
- Vary rhythm across sections.
- Use fresh imagery and avoid default metaphors.
- Try unusual narrative points of view when appropriate.
- Use time jumps, flashbacks, or previews if the story calls for it.
- Build around a central concept for depth and coherence.

## Style Description

Use concise comma-separated tags. The style description should include only relevant items from these categories:

Tag categories:

- Style: `alternative-rock`, `indie-folk`, `synthwave`, `pop`, `rock`, `electronic`, `indie`, `r&b`, `hip-hop`
- Vocal: `male-vocals`, `female-vocals`, `harmonies`
- Instrument: `acoustic-guitar`, `synth-bass`, `sax`, `violin`, `piano`, `synth`, `strings`
- Tempo: `fast-tempo`, `mid-tempo`, `slow-groove`, `upbeat`
- Mood: `dreamy`, `energetic`, `melancholic`, `nostalgic`

Example:

```text
indie-pop, female-vocals, acoustic-guitar, mid-tempo, dreamy, emotional
```

## Exclude Styles

Use concise comma-separated tags for elements that would weaken the brief.

Categories:

- Unwanted genre: `mainstream-pop`, `r&b`, `trap`
- Unwanted instrument or production: `auto-tune`, `heavy-bass`
- Unwanted mood: `overly-happy`, `cheesy`

Example:

```text
mainstream-pop, auto-tune, overly-happy
```

## Suno Platform Optimization

- In instrumental sections, use concrete atmosphere and instrumentation details, such as `(electronic drums fade in, slightly distorted synths create a dreamlike haze)`.
- Keep tags balanced: each section should use only the most useful markers.
- Highlight the strongest hook with `[Hook]`.
- Use short lines and precise punctuation for By Line mode.
- Guide emotional progression, such as `[Calm]` to `[Intense]`.
- Prefer concrete effects such as `(echo fading)` over vague `(echo)`.
- Use instrument combinations such as `[Synth and Piano]` when helpful.
- Use space markers such as `[Verse: Intimate]` and `[Chorus: Expansive]`.
- Keep `[Intro]` and `[Outro]` empty unless the user explicitly wants performed text there.

## Professional Composition Principles

- Maintain theme consistency across all sections.
- Build a coherent image system.
- Balance syllables so lines are singable.
- Contrast sections by energy, density, rhythm, or emotional stance.
- Design the emotional or musical climax deliberately.
- Consider returning to the opening image near the end.
- Place the most important turn or climax around the latter middle of the song when it feels natural.
- Layer lead vocal, harmonies, background voices, and ad-libs intentionally.
- Shape spatial movement from intimate to large, or large to intimate.

## Quality Bar

Must do:

- Use specific scenes and details.
- Balance line length and singability.
- Use rhyme or sonic echo where it helps memorability.
- Make the hook stronger than the verses.
- Create fresh imagery and avoid empty abstraction.
- Preserve a clear emotional arc.
- Keep lyrics, theme, emotion, and style aligned.
- Check transitions between sections.
- Ensure the song suits the target audience and creative goal.

Avoid:

- Cliche pop lines with no new angle.
- Abstract motivational language.
- Awkward, unsingable phrasing.
- Alternating Chinese and English line-by-line unless requested.
- Putting prose descriptions under `[Intro]` or `[Outro]`.

## Generation Command Pattern

The local executable comes from the upstream `paperfoot/suno-cli` project and is installed as `suno`.

Install options:

```bash
brew tap paperfoot/tap
brew install suno
```

```bash
cargo install suno --locked
```

The skill wrapper can bootstrap it:

```bash
scripts/ensure_suno_cli.sh
```

Prefer:

```bash
suno generate \
  --title "$TITLE" \
  --tags "$STYLE_DESCRIPTION" \
  --exclude "$EXCLUDE_STYLES" \
  --lyrics-file "$LYRICS_FILE" \
  --model v5.5 \
  --wait \
  --download "$OUTPUT_DIR"
```

If the user already has clip IDs:

```bash
suno download -o "$OUTPUT_DIR" "$CLIP_ID_1" "$CLIP_ID_2"
```
