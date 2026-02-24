---
name: wrapped
description: Show a stats summary for a time period — month, year, or all-time.
disable-model-invocation: true
---
Show wrapped stats. If $ARGUMENTS is empty, default to "month".
Run: !`claude-rank wrapped --period ${ARGUMENTS:-month}`
Valid periods: month, year, all-time
