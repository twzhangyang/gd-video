# Subtitle Glossary

Used by the subtitle step. `gdvideo.py prep` passes the correct terms to Whisper as a hint, and the cleanup step (the `gd-video` skill) fixes known mishearings and uses the translations.

Format: `- wrong → right` for a known mishearing, or `- term` for a correct spelling. Add a line whenever a subtitle comes out wrong.

> Only bullets under **Levels** and **Game terms** are sent to Whisper. Add new terms there.

## Levels

- Electro-Ban adventures → Electroman Adventures
- ElectraModadventures → Electroman Adventures

## Game terms

- Geometry Dash
- practice mode
- coin
- user coin
- orb
- portal
- ship
- UFO
- wave
- ball
- robot
- spider
- swing
- straight fly
- straightfire → straight fly
- transition
- checkpoint
- icon

## Translation (zh)

| English | 中文 |
|---|---|
| coin | 金币 |
| orb | 跳环 |
| portal | 传送门 |
| ship | 飞船 |
| wave | 波浪 |
| practice mode | 练习模式 |
| straight fly | 直飞 |
| transition | 转场 |

## Cleanup rules

- Remove filler and repeats: "okay okay okay", "um", "like", "whatever", "bro" at the end of a line
- Keep the speaker's personality: reactions like "Oh my god", "I'm too good" stay
- Keep each line short: one idea per cue
