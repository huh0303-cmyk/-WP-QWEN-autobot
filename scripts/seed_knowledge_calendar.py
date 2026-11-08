"""Idempotently seed the five knowledge channels' due calendar rows.

Never alter existing rows, claim states, or backfill missed dates.
"""
from __future__ import annotations
import datetime as dt
from scripts.knowledge_channel_cadence import KST, DAILY, WEEKLY, slots
from automation_hub.youtube_calendar import TAB, READY, read_calendar

TOPICS = {
    'history': 'This Day in World History: surprising true events on {date}',
    'nasa': 'NASA X-Files: a verified space exploration mystery ({date})',
    'invention': 'Invention Story: the unexpected origin of a breakthrough ({date})',
    'silent_era': 'Old Hollywood: forgotten cinema stories and archival discoveries ({date})',
    'retro_reels': 'Retro USA: surprising everyday American life in the archives ({date})',
}

def planned_rows(existing, now, enabled):
    today = now.astimezone(KST).date()
    occupied = {(r['key'], r['when'].date()) for r in existing}
    output = []
    for channel in DAILY + WEEKLY:
        if channel not in enabled:
            continue
        for when in slots(channel, today):
            if when.date() < today or (channel, when.date()) in occupied:
                continue
            # The calendar uses an hourly dispatcher: avoid already-passed slots.
            if when <= now.astimezone(KST):
                continue
            date = when.date().isoformat()
            row = [''] * 15
            row[0] = f'CAL-AUTO-{channel.upper()}-{date}'
            row[1] = when.strftime('%Y-%m-%d %H:%M KST')
            row[2] = 'YouTube Knowledge'
            row[3] = channel
            row[5] = 'en'
            row[7] = TOPICS[channel].format(date=date)
            row[12] = READY
            row[14] = '[knowledge-auto-plan] source-verified production required'
            output.append(row)
            occupied.add((channel, when.date()))
    return output

def seed(service, spreadsheet_id, enabled, now=None):
    now = now or dt.datetime.now(KST)
    existing = read_calendar(service, spreadsheet_id)
    additions = planned_rows(existing, now, enabled)
    if additions:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{TAB}'!A:O", valueInputOption='RAW',
            insertDataOption='INSERT_ROWS', body={'values': additions},
        ).execute()
    print(f'KNOWLEDGE_CALENDAR_SEEDED count={len(additions)}')
    return len(additions)
