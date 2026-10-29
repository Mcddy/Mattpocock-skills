# Cerberus reference

## Default lens emphasis

Which lens leads when the three disagree. The composite score stays the plain sum of the three lens scores.

| Asset | Macro | Technical | Sentiment |
|---|---|---|---|
| Gold, silver | 40% | 35% | 25% |
| AUD/USD | 35% | 40% | 25% |
| Crude oil | 35% | 35% | 30% |
| Indices | 30% | 40% | 30% |
| BTC and crypto | 20% | 45% | 35% |

## Brief schema

```xml
<cerberus_brief>
  <asset>name and ticker</asset>
  <timestamp>date and session</timestamp>
  <data_source>where the numbers came from, or ASSUMED</data_source>
  <verdict>STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL | WAIT</verdict>
  <conviction>0-100</conviction>
  <macro><score>-5 to +5</score><summary/><key_catalyst/></macro>
  <technical><score/><summary/><entry_zone/><stop_level/><target_1/><target_2/></technical>
  <sentiment><score/><summary/><contrarian_flag>YES|NO</contrarian_flag></sentiment>
  <composite_score>-15 to +15</composite_score>
  <risk_reward/>
  <time_horizon>Intraday | Short-term | Medium-term</time_horizon>
  <key_risk/>
  <execution_note/>
</cerberus_brief>
```

## Pre-trade checklist

- All three lenses scored.
- Composite at least +5 or at most -5 for a trade recommendation.
- Stop level defined and logical.
- Reward to risk at least 1.5 to 1.
- Key risk identified.
- No major news catalyst in the next 4 hours, unless trading it.

## Rapid brief

```
ASSET / VERDICT / CONVICTION
MACRO: +/-X, one sentence
TECHNICAL: +/-X, key level
SENTIMENT: +/-X, one sentence
COMPOSITE: score / KEY RISK: one sentence / EXECUTE: specific entry condition
```

## Publication format

1. Executive summary (three sentences: verdict, key driver, key risk).
2. Macro landscape (two or three paragraphs).
3. Three-lens analysis.
4. Actionable setup (levels, conditions, structure).
5. Risk register (top three risks, probability times impact).
6. Watchlist (two or three assets for the next session).

Tone: direct, institutional, no filler. Readers are serious operators.

## Other formats

- **Newsletter issue**: hook (why this matters now), context, analysis (the three-lens picture), the trade, close (what to watch).
- **Commercial content** (prompt or product launch): problem, solution, proof, what is included, who it is for, call to action.
