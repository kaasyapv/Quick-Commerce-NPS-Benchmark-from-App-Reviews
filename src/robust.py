"""Does the app ranking hold when 3 star reviews count as passive instead of detractor?

Writes outputs/robustness.csv with one row per quarter.
"""
import numpy as np
import pandas as pd

from nps import OUT, nps


def order(df: pd.DataFrame) -> pd.Series:
    """Apps from best to worst NPS, per period, as one string."""
    return df.sort_values("nps", ascending=False).groupby("period")["app"].agg(" > ".join)


def lead(df: pd.DataFrame) -> pd.DataFrame:
    """Lead of the first app over the second, and whether it beats their two margins of error combined."""
    top2 = df.sort_values("nps", ascending=False).groupby("period").head(2).groupby("period")
    out = pd.DataFrame({"lead": top2["nps"].agg(lambda s: s.iloc[0] - s.iloc[1]),
                        "moe": top2["moe"].agg(lambda s: np.sqrt((s ** 2).sum()))})
    out["clear"] = out["lead"] > out["moe"]
    return out


if __name__ == "__main__":
    main, alt = nps("quarter", 3), nps("quarter", 2)
    out = pd.DataFrame({"ranking": order(main), "ranking_3star_passive": order(alt)})
    out["same_ranking"] = out["ranking"] == out["ranking_3star_passive"]
    for name, df in (("main", main), ("3star_passive", alt)):
        out[f"top_minus_bottom_{name}"] = df.groupby("period")["nps"].agg(lambda s: s.max() - s.min())
        out = out.join(lead(df).rename(columns={"lead": f"lead_over_second_{name}", "moe": f"lead_moe_{name}",
                                                "clear": f"lead_is_clear_{name}"}))
    out.round(2).to_csv(OUT / "robustness.csv")
    print(out.round(2).T.to_string())
    print(f"\nranking unchanged in {out['same_ranking'].sum()} of {len(out)} quarters")
