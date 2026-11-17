# MonsoonMind

Explains Tamil Nadu's monsoon and weather history from IMD reports (northeast monsoon statistics, district rainfall, cyclone reports) and sets it next to live forecasts.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

## Who it's for

Agriculture officer in Thanjavur planning samba paddy advisories around the northeast monsoon.

## The problem

Agriculture officers need reliable information about Tamil Nadu's monsoon rainfall to plan Samba paddy advisories. IMD reports provide historical rainfall statistics, but officers also need to understand current weather conditions. Historical rainfall data and live forecasts are different types of information and should not be mixed. MonsoonMind keeps these sources separate so officers can make better-informed decisions.

## Data sources

IMD monsoon end-of-season reports, northeast monsoon reports, RMC Chennai reports, RSMC cyclone reports and district rainfall statistics.

- https://mausam.imd.gov.in/
- https://rsmcnewdelhi.imd.gov.in/
- https://open-meteo.com/
- Terms: Public IMD publications; Open-Meteo is free for non-commercial use (CC BY 4.0 data).

## Hardest problem (my interview story)

Climate history vs real time: reports describe past seasons, users ask about now. The app must keep 'what IMD reported' (retrieval) apart from 'current forecast' (API tool) and never present a forecast as a report fact.

## Signature feature

Season replay: pick a year and see the delta districts' NE monsoon rainfall vs normal, with cyclones marked on the timeline.

## Target metric

Correct season statistics for 90%+ of 40 questions; zero forecast numbers presented as report facts.

The initial performance and availability targets are set realistically for a student-scale deployment and can be improved as the system grows.


## Run it locally

```bash
uv sync
cp .env.example .env   # Windows: copy .env.example .env
uv run uvicorn monsoonmind.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```
