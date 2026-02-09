# OpenF1 API Data Shapes

Captured from `scripts/explore_openf1.py` on 2026-02-09.
Session: Abu Dhabi 2025 (session_key: 9839, meeting_key: 1276).

---

## /sessions

**Records per race year:** ~30

```json
{
  "session_key": 9693,
  "session_type": "Race",
  "session_name": "Race",
  "date_start": "2025-03-16T04:00:00+00:00",
  "date_end": "2025-03-16T06:00:00+00:00",
  "meeting_key": 1254,
  "circuit_key": 10,
  "circuit_short_name": "Melbourne",
  "country_key": 5,
  "country_code": "AUS",
  "country_name": "Australia",
  "location": "Melbourne",
  "gmt_offset": "11:00:00",
  "year": 2025
}
```

**Notes:** Cache this — doesn't change mid-session. Contains `meeting_key` and `circuit_key` not in our original data model.

---

## /drivers

**Records per session:** 20 (one per driver)

```json
{
  "meeting_key": 1276,
  "session_key": 9839,
  "driver_number": 1,
  "broadcast_name": "M VERSTAPPEN",
  "full_name": "Max VERSTAPPEN",
  "name_acronym": "VER",
  "team_name": "Red Bull Racing",
  "team_colour": "4781D7",
  "first_name": "Max",
  "last_name": "Verstappen",
  "headshot_url": "https://media.formula1.com/...",
  "country_code": null
}
```

**Notes:** Cache this — doesn't change mid-session. `team_colour` is useful for dashboard styling. `country_code` can be null.

---

## /position

**Records per driver per session:** Very low (~3 for VER in a race). Updates only on position changes, NOT every poll cycle.

```json
{
  "date": "2025-12-07T12:05:19.767000+00:00",
  "session_key": 9839,
  "driver_number": 1,
  "position": 1,
  "meeting_key": 1276
}
```

**Notes:** Low-frequency endpoint. Position tower will need to reconstruct current standings from the latest position record per driver, not from a continuous stream.

---

## /car_data

**Records per driver per session:** ~33,653 (HIGHEST VOLUME — ~100ms resolution)

```json
{
  "date": "2025-12-07T12:06:20.939000+00:00",
  "session_key": 9839,
  "meeting_key": 1276,
  "n_gear": 0,
  "driver_number": 1,
  "rpm": 0,
  "throttle": 0,
  "drs": 0,
  "speed": 0,
  "brake": 0
}
```

**Notes:**
- **This is the bandwidth concern.** 33K records/driver × 20 drivers = ~670K records/session.
- Consider downsampling to 1-second intervals for storage (reduce ~10x).
- Or only poll this endpoint for specific drivers on demand.
- Fields: `n_gear` (gear number), `rpm`, `throttle` (0-100), `drs` (0/1), `speed` (km/h), `brake` (0/1 or 0-100).

---

## /laps

**Records per driver per session:** ~58 (one per lap)

```json
{
  "meeting_key": 1276,
  "session_key": 9839,
  "driver_number": 1,
  "lap_number": 1,
  "date_start": "2025-12-07T13:03:27.584000+00:00",
  "duration_sector_1": 21.142,
  "duration_sector_2": 38.489,
  "duration_sector_3": 32.363,
  "i1_speed": 284,
  "i2_speed": 293,
  "is_pit_out_lap": false,
  "lap_duration": 91.994,
  "segments_sector_1": [2048, 2049, 2051, 2051, 2051],
  "segments_sector_2": [2049, 2051, 2049, 2049, 2049, 2049, 2049, 2049, 2049],
  "segments_sector_3": [2049, 2051, 2049, 2051, 2051, 2051, 2051, 2051, 2051, 2051],
  "st_speed": 307
}
```

**Notes:**
- **Field name mismatches vs. original data model:**
  - API: `duration_sector_1` → Model had: `sector_1`
  - API: `lap_duration` → Model had: `lap_duration` (matches)
  - API: `is_pit_out_lap` → Model had: `is_pit_out_lap` (matches)
- **Fields NOT in original model (add these):**
  - `i1_speed`, `i2_speed` — intermediate speed traps (km/h)
  - `st_speed` — speed trap (km/h)
  - `segments_sector_1/2/3` — mini-sector marshal codes (arrays of ints). DynamoDB stores these as Lists.
  - `date_start` — lap start timestamp
- **`compound` (tire type) is NOT in this endpoint.** Must come from `/pit` or be inferred. Need a join strategy.

---

## /race_control

**Records per session:** ~109

```json
{
  "meeting_key": 1276,
  "session_key": 9839,
  "date": "2025-12-07T12:20:00+00:00",
  "driver_number": null,
  "lap_number": 1,
  "category": "Flag",
  "flag": "GREEN",
  "scope": "Track",
  "sector": null,
  "qualifying_phase": null,
  "message": "GREEN LIGHT - PIT EXIT OPEN"
}
```

**Notes:**
- `driver_number` is nullable (track-wide flags have no driver).
- `scope` can be "Track" or sector-specific.
- `qualifying_phase` only populated during qualifying sessions.
- Extra fields vs. model: `scope`, `sector`, `qualifying_phase`, `lap_number`.

---

## /weather

**Records per session:** ~154

```json
{
  "date": "2025-12-07T12:06:07.170000+00:00",
  "session_key": 9839,
  "pressure": 1016.4,
  "air_temperature": 27.4,
  "rainfall": 0,
  "wind_speed": 3.0,
  "meeting_key": 1276,
  "humidity": 55.0,
  "track_temperature": 34.6,
  "wind_direction": 67
}
```

**Notes:** Low frequency (~1 record/min). Good candidate for the dashboard's weather widget. Not in original DynamoDB model — consider adding a Weather table or embedding in session metadata.

---

## /pit

**Records per session:** ~27

```json
{
  "date": "2025-12-07T13:14:35.391000+00:00",
  "session_key": 9839,
  "driver_number": 27,
  "meeting_key": 1276,
  "stop_duration": null,
  "pit_duration": 21.6,
  "lap_number": 7,
  "lane_duration": 21.6
}
```

**Notes:**
- `stop_duration` is frequently null — only `pit_duration` and `lane_duration` are reliable.
- **This is where tire compound info should come from**, but it's NOT in this endpoint either.
- Tire compound may need to come from FastF1 Python library or be inferred from lap characteristics.

---

## Summary: Data Model Updates Needed

| Issue | Action |
|-------|--------|
| Laps table: `sector_1/2/3` field names | Rename to `duration_sector_1/2/3` to match API |
| Laps table: missing speed trap fields | Add `i1_speed`, `i2_speed`, `st_speed` |
| Laps table: missing segment arrays | Add `segments_sector_1/2/3` (List type) |
| Laps table: `compound` not available | Remove from Laps table or source from FastF1 |
| Weather data: no table defined | Add Weather table or embed in session |
| Position data: very low frequency | Design dashboard to show last-known position, not assume continuous updates |
| car_data: extreme volume | Downsample or limit polling to avoid DynamoDB cost explosion |
| Pit table: `stop_duration` unreliable | Use `pit_duration` as primary metric |
