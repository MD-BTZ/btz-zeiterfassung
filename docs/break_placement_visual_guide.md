# ArbZG Break Placement - Visual Guide

This visual guide explains how the ArbZG-compliant break placement system works with practical examples and visual representations.

## Break Requirements Visualization

```
|-----------------------------------------------------------------------|
|                       WORK DAY DURATION                               |
|-----------------------------------------------------------------------|
| < 6 hours |          6-9 hours          |         > 9 hours          |
|           |                             |                            |
| No breaks | 30 min break required       | 45 min break required      |
|-----------------------------------------------------------------------|
```

## Break Placement Scenarios

### Scenario 1: Work Day with Perfect Lunch Period

```
|-----------------------------------------------------------------------|
| 08:00            11:30      12:15           14:00                17:00 |
|-----------------------------------------------------------------------|
| WORK             |////LUNCH PERIOD////|     WORK                       |
|                  |                    |                                |
|                  |<-- 45min break -->|                                |
|-----------------------------------------------------------------------|
```

In this case:
- Work day from 8:00 to 17:00 (9 hours)
- Lunch period from 11:30 to 14:00
- 45 min break placed perfectly within lunch period
- Result: 45 min break from 11:45 to 12:30 (centered in lunch period)

### Scenario 2: Work Day with Insufficient Lunch Period

```
|-----------------------------------------------------------------------|
| 08:00     10:00       11:00       12:00                          19:00 |
|-----------------------------------------------------------------------|
| WORK      |/LUNCH/|    WORK                                            |
|           |<30m>|                                  |<15m>|             |
|           |     |                                  |     |             |
|           |Lunch Break|                            |End Break|         |
|-----------------------------------------------------------------------|
```

In this case:
- Work day from 8:00 to 19:00 (11 hours)
- Short lunch period from 10:00 to 11:00 (only 1 hour)
- 45 min break required (> 9 hours work)
- Result: 30 min lunch break + 15 min end-of-day break

### Scenario 3: Work Day After Lunch Period

```
|-----------------------------------------------------------------------|
| 14:30                                                           22:30  |
|-----------------------------------------------------------------------|
| WORK                                                  |<--30min-->|    |
|                                                       |  END BREAK|    |
|-----------------------------------------------------------------------|
```

In this case:
- Work day from 14:30 to 22:30 (8 hours)
- Entire work day is after lunch period
- 30 min break required (6-9 hours work)
- Result: 30 min break placed at the end of the work day

## Break Types - Visual Appearance

The system uses different visual styles to distinguish break types:

```
|-----------------------------------------------------------------------|
| BREAK TYPE         | APPEARANCE       | INDICATOR                     |
|-----------------------------------------------------------------------|
| Lunch Break        | Orange Badge     | Utensils Icon                 |
| End-of-Day Break   | Green Badge      | Clock Icon                    |
| Manual ArbZG Break | Purple Badge     | User-Clock Icon               |
| Auto-detected      | Blue Badge       | Robot Icon                    |
|-----------------------------------------------------------------------|
```

## Break Distribution Logic

For longer work days requiring 45-minute breaks:

```
|-----------------------------------------------------------------------|
| LUNCH PERIOD SIZE   | BREAK DISTRIBUTION                              |
|-----------------------------------------------------------------------|
| ≥ 45 minutes        | Full 45 min break during lunch                  |
| < 45 minutes        | Maximum possible during lunch + remainder at end|
| No overlap          | Full 45 min break at end of day                 |
|-----------------------------------------------------------------------|
```

## Configuring Lunch Period - Admin View

Admin users can configure the system-wide lunch period in the Break Settings page:

```
|-----------------------------------------------------------------------|
| LUNCH PERIOD SETTINGS                                                 |
|-----------------------------------------------------------------------|
| Mittagszeit von: [11] : [30]  bis: [14] : [00]                        |
|-----------------------------------------------------------------------|
```

## User Lunch Period Configuration

Users can have individualized lunch period settings that override system defaults:

```
|-----------------------------------------------------------------------|
| USER SETTINGS                                                         |
|-----------------------------------------------------------------------|
| Bevorzugte Mittagszeit: [12] : [00]  bis: [13] : [30]                 |
|-----------------------------------------------------------------------|
```

This visual guide helps users understand how the break placement algorithm works in different scenarios and how to configure it for their specific needs.
