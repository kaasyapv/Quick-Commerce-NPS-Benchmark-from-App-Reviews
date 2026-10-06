-- NPS proxy per app and period, with a 95% margin of error in NPS points.
-- $grain is 'month' or 'quarter'. Promoter = 5 stars, detractor = score <= $detractor_max
-- (3 for the main definition, 2 for the check where 3 stars count as passive).
-- "at" is in IST because the scraper converts timestamps with the local clock.
with reviews as (
    select regexp_extract(filename, '(\w+)\.parquet$', 1) as app,
           date_trunc($grain, "at")::date as period,
           score
    from read_parquet($raw, filename = true)
),
agg as (
    select app, period,
           count(*) as n,
           sum((score = 5)::int) as n_promoters,
           sum((score <= $detractor_max)::int) as n_detractors
    from reviews
    group by app, period
),
shares as (
    select *, n_promoters / n as p, n_detractors / n as d from agg
)
select app, period, n, n_promoters, n_detractors,
       round(p, 4) as p,
       round(d, 4) as d,
       round(100 * (p - d), 2) as nps,
       round(196 * sqrt((p + d - pow(p - d, 2)) / n), 2) as moe
from shares
order by app, period
