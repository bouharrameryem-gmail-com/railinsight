# Datasheet — Monthly TGV regularity by route (SNCF / AQST)

Two levels are documented: (a) the source dataset published by SNCF,
which we did not create, and (b) the derived dataset produced by
our processes and used by the app.

## 1. Motivation
- Purpose of the source dataset: public reporting of TGV service quality
  per route, in cooperation with the French transport service quality
  authority (AQST). [Check the official description.]
- Purpose of the derived dataset: support the RailInsight public webapp
  answering: [our main question].
- Creators: SNCF Voyageurs (source); [team names] (derived version,
  Télécom Paris MS IA project).
- Funding: [unknown for the source]; none for the derived version.

## 2. Composition
- One instance = one month x one route (departure station -> arrival
  station) x one service (national / international). Not a train, not a
  passenger trip.
- Number of instances: [N rows], [n routes], months [first]..[last].
- Sample or census? A selection of TGV routes defined with the AQST, not
  all TGV services. The same train can be counted in several routes:
  rows must NOT be summed to compute a national or per-axis regularity.
- Fields: [link to the data dictionary table].
- Definition of "on time" (composite regularity): delay at terminus below
  5 min (< 1h30 trips), 10 min (1h30-3h), 15 min (> 3h). Consequence: the
  generic late rate is not comparable across routes of different
  durations; we use fixed thresholds (> 30 min) for cross-route comparisons.
- Measurement: sensors at station entry, occasionally manual; precision
  of one minute, rounded down.
- Missing information: mean delay of late trains and cause shares are
  undefined when no train is late (structural missingness, not imputed);
  comment fields mostly empty (filled when notable events occur).
  [Months missing for some routes: describe.]
- Errors / noise / redundancy: [results of the consistency checks:
  nested thresholds, cause shares summing to 100, duplicated keys].
  [Result of the "is the late-arrival column composite?" check.]
- Cause labels are attributed by the operator itself using an internal
  nomenclature; they are declarative labels, not causal estimates.
- Relationships between instances: A->B and B->A are distinct routes;
  routes sharing trains are not identified.
- Self-contained? Yes for the regularity figures. Station coordinates
  come from the SNCF "stations" dataset [name, URL, snapshot date];
  [x %] of stations matched automatically, the rest via a manual alias file.
- Personal or sensitive data: none. The dataset does not relate to
  individuals (aggregated operational statistics).

## 3. Collection process
- Source: SNCF open data portal, dataset `regularite-mensuelle-tgv-aqst`,
  CSV export downloaded on [date] from [URL].
- Collection mechanism of the source: operational train tracking systems
  (sensors), monthly aggregation by SNCF. [Details unknown to us.]
- Timeframe: [first month]..[last month]; published monthly.
- Ethical review: not applicable (no personal data).

## 4. Preprocessing / cleaning
- Column renaming to snake_case (mapping in `src/railinsight/config.py`).
- Type conversions: month -> period; station names normalised
  (upper case, stripped accents and extra spaces) [list other rules].
- Derived variables: trains run = planned - cancelled; rates computed
  as ratios of sums; duration class; cause counts = share x late trains.
- Rows removed: [none / list with justification].
- Exceptional months (strikes, COVID-19 lockdowns): KEPT in the data,
  flagged by [rule], and excludable in the app. Rationale: extreme but
  real events, not errors.
- Raw data kept: yes, [location / how to re-download].
- Software: `scripts/build_dataset.py`, tested in `tests/`.

## 5. Uses
- Intended: descriptive and exploratory analysis of TGV punctuality per
  route for a general audience.
- Not suitable for: computing national or per-axis regularity (double
  counting); inferring the delay probability of an individual trip
  (ecological fallacy); attributing responsibility for delays (cause
  labels are declarative); causal claims (observational aggregated data).
- Risks: small routes produce unstable rates (mitigated by shrinkage and
  minimum-volume thresholds); ranking routes may harm the perception of
  specific stations or regions, so rankings are shown with uncertainty.

## 6. Distribution
- Source licence: [ODbL — verify on the portal]. Attribution: "Source:
  SNCF Open Data". Derived database shared under the same licence.
- Derived data distributed in this GitHub repository (parquet snapshot).

## 7. Maintenance
- Source maintained by SNCF, updated monthly.
- Derived version maintained by [team] until [date]; refresh by running
  `uv run python scripts/build_dataset.py --source <new export>`.
- Report issues via GitHub issues on [repo URL].
- Changelog: [date] — first version.