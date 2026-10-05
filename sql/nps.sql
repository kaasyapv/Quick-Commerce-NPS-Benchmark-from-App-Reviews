-- Monthly NPS proxy per app, with a 95% margin of error in NPS points.
-- Promoter = 5 stars, detractor = score <= $detractor_max (3 for the main definition,
-- 2 for the robustness check where 3 stars count as passive).
-- "at" is in IST because the scraper converts timestamps with the local clock.
with reviews as (
    select regexp_extract(filename, '(\w+)\.parquet$', 1) as app,
           date_trunc('month', "at")::date as month,
           score
    from read_parquet($raw, filename = true)
),
monthly as (
    select app, month,
           count(*) as n,
           avg((score = 5)::int) as p,
           avg((score <= $detractor_max)::int) as d
    from reviews
    group by app, month
)
select app, month, n,
       round(p, 4) as p,
       round(d, 4) as d,
       round(100 * (p - d), 2) as nps,
       round(196 * sqrt((p + d - pow(p - d, 2)) / n), 2) as moe
from monthly
order by app, month
