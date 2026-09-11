"""Footage-first scene narration. Never loop footage to fill a target runtime."""
import json
import os
from pathlib import Path


ANGLES = {
    'nasa': 'Space science grounded in the actual NASA footage.',
    'history': 'World history on the specified month/day, newest event first.',
    'invention': 'Did you know? Surprising invention origins and incremental discoveries. Electricity and coffee were not invented by one person. Avoid lone-inventor myths.',
    'silent_era': 'Old Hollywood: silent and black-and-white cinema, with documentary narration about the actual film and filmmaking.',
    'retro_reels': 'Retro USA: everyday homes, appliances, children, food, dancing and social life from the 1960s through the 2000s. Evoke nostalgia without inventing memories.',
}


def validate_scene(text, duration):
    if not text.strip() or duration <= 0:
        raise ValueError('Empty narration or source footage')
    if len(text.split()) > max(8, int(duration * 2.2)):
        raise ValueError('Narration exceeds available footage word budget')


def render_scenes(topic, channel, clips, workdir, generate, parse, verify,
                  tts, write_srt, mux, normalize, ffmpeg, duration):
    """Generate and synthesize each scene independently, then concatenate AV pairs."""
    segments, records = [], []
    elapsed = 0.0
    for index, clip in enumerate(clips):
        if elapsed >= 900:
            break
        folder = Path(workdir) / f'scene_{index:03d}'
        folder.mkdir(parents=True, exist_ok=True)
        available = min(float(clip['duration']), 45.0, 900 - elapsed)
        if available < 5:
            continue
        budget = max(8, int(available * 1.6))
        prompt = (
            f'{ANGLES[channel]} Topic: {topic}. Write English documentary narration '
            f'for ONLY this actual clip, maximum {budget} words. Begin naturally; '
            'do not repeat a generic introduction in each scene. Describe only '
            'the inspected footage and supported source facts. Omit uncertain claims. '
            'Do not describe later footage or pad duration. Return JSON with narration. '
            f'Source: {json.dumps(clip, ensure_ascii=False)}'
        )
        data = json.loads(parse(generate(prompt, temperature=0.4)))
        text = data.get('narration', '').strip()
        validate_scene(text, available)
        review = verify(clip.get('event_text', topic), [clip], text, generate)
        def reject_silence(*args, **kwargs):
            raise RuntimeError('ElevenLabs failed: silent narration is not publishable')
        globals_ = tts.__globals__
        previous = globals_.get('make_silence')
        globals_['make_silence'] = reject_silence
        try:
            audio, captions, seconds = tts(text, str(folder))
        finally:
            if previous is None:
                globals_.pop('make_silence', None)
            else:
                globals_['make_silence'] = previous
        # A mismatch must not silently loop or freeze unrelated imagery.
        if seconds > available + 0.05:
            raise RuntimeError(f'Scene {index}: narration {seconds:.1f}s exceeds footage budget {available:.1f}s')
        visual = str(folder / 'visual.mp4')
        normalize(clip['path'], visual, seconds)
        if duration(visual) + 0.15 < seconds:
            raise RuntimeError('Source video shorter than narration')
        if clip.get('event_label'):
            # Date/year remains visible above the timed spoken subtitles.
            label_path = folder / 'event.txt'
            label_path.write_text(clip['event_label'], encoding='utf-8')
            labeled = str(folder / 'labeled.mp4')
            escaped = str(label_path.resolve()).replace('\\', '/').replace(':', '\\:')
            ffmpeg(['ffmpeg', '-y', '-i', visual, '-vf',
                    f"drawtext=textfile='{escaped}':fontsize=48:fontcolor=white:box=1:boxcolor=black@0.65:x=40:y=40",
                    '-c:v', 'libx264', '-an', labeled])
            visual = labeled
        subtitle = str(folder / 'captions.srt')
        write_srt(captions, subtitle)
        final = str(folder / 'final.mp4')
        mux(visual, audio, subtitle, final, str(folder))
        segments.append(Path(final).resolve())
        records.append({'clip': clip, 'narration': text, 'start': elapsed,
                        'duration': seconds, 'alignment': review})
        elapsed += seconds
    if not segments:
        raise RuntimeError('No grounded, narrated scenes available')
    concat = Path(workdir) / 'scene_concat.txt'
    concat.write_text(''.join("file '" + str(p).replace('\\', '/') .replace("'", "'\\''") + "'\n" for p in segments), encoding='utf-8')
    final = str(Path(workdir) / 'final.mp4')
    ffmpeg(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat), '-c', 'copy', final])
    Path(workdir, 'scene_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    return final, '\n\n'.join(r['narration'] for r in records)
